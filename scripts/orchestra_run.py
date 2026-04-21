"""Orchestra runner for Killing Time.

Chains stages per configs/pipeline/killingtime_harness.yml:

  intake -> source_probe -> subtitle_discovery -> source_extraction
         -> translation -> qa -> export

Policies enforced here:
  - Track subtitles are the preferred translation source (timing preserved).
  - delivery_exclude (zh, en) applies only to the final package, never to
    the translation source.
  - Hardsub mode defaults to `keep`: the original video is not touched,
    ko/es cues overlay on playback. `--clean-hardsub` opts into delogo.
  - ASR (faster-whisper) runs only when 0 subtitle tracks exist.
  - `--existing` + `--sub` reuse already-downloaded assets.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import yaml

from _common import (
    DOWNLOAD_DIR,
    MANIFEST_DIR,
    REPORT_DIR,
    ROOT,
    SUBTITLE_DIR,
    ensure_dirs,
    log,
    read_json,
    run,
    sanitize_stem,
    write_json,
)


SCRIPTS = Path(__file__).resolve().parent


def py(*args: str) -> list[str]:
    return [sys.executable, *args]


def load_harness() -> dict:
    return yaml.safe_load((ROOT / "configs" / "pipeline" / "killingtime_harness.yml").read_text(encoding="utf-8"))


def write_manifest(video_id: str, project: dict) -> Path:
    path = MANIFEST_DIR / f"{video_id}.yml"
    path.write_text(yaml.safe_dump({"project": project}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def update_manifest(path: Path, patch: dict) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    project = data.get("project") or {}
    project.update(patch)
    path.write_text(yaml.safe_dump({"project": project}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return project


def synth_download_report(video: Path, video_id: str) -> Path:
    report = {
        "video_id": video_id,
        "title": video_id,
        "channel": None,
        "duration": None,
        "webpage_url": None,
        "available_subtitles": [],
        "available_auto_captions": [],
        "file": str(video.relative_to(ROOT)) if video.is_absolute() and ROOT in video.parents else str(video),
        "reused": True,
    }
    path = REPORT_DIR / f"{video_id}.download.json"
    write_json(path, report)
    return path


def fetch_remote_metadata(url: str) -> dict:
    result = run(py("-m", "yt_dlp", "--dump-single-json", "--no-warnings", url))
    return json.loads(result.stdout)


def pull_subtitle(url: str, video_id: str, track: str) -> Path | None:
    output_template = str(SUBTITLE_DIR / f"{video_id}.%(ext)s")
    cmd = py(
        "-m", "yt_dlp",
        "--skip-download",
        "--write-subs", "--write-auto-subs",
        "--sub-format", "srt",
        "--convert-subs", "srt",
        "--sub-langs", track,
        "-o", output_template,
        "--no-warnings",
        url,
    )
    try:
        run(cmd, capture=False)
    except subprocess.CalledProcessError as exc:
        log("source_extraction", f"yt-dlp subtitle pull failed for {track}: {exc}")
        return None
    base = track.split("-")[0]
    for cand in sorted(SUBTITLE_DIR.glob(f"{video_id}*.srt")):
        if track in cand.name or base in cand.name:
            return cand
    matches = sorted(SUBTITLE_DIR.glob(f"{video_id}*.srt"))
    return matches[0] if matches else None


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("url", nargs="?", help="YouTube URL (omit when using --existing with --video-id)")
    ap.add_argument("--targets", nargs="+", default=["ko", "es"])
    ap.add_argument("--existing", type=Path, default=None,
                    help="Reuse an already-downloaded video file")
    ap.add_argument("--sub", type=Path, default=None,
                    help="Use an existing source SRT, skipping subtitle_discovery + extraction")
    ap.add_argument("--source-lang", default=None,
                    help="Source language code for the SRT (used with --sub)")
    ap.add_argument("--video-id", default=None,
                    help="Override video id (required when using --existing without a URL)")
    ap.add_argument("--clean-hardsub", action="store_true",
                    help="Apply ffmpeg delogo to remove burned-in subtitles (may blur the region)")
    ap.add_argument("--skip-hardsub-probe", action="store_true")
    ap.add_argument("--asr-model", default="small", help="faster-whisper model size")
    ap.add_argument("--engine", default=None,
                    help="translation engine: local | claude | gemini | gpt (default from harness)")
    ap.add_argument("--dry-run", action="store_true")
    return ap.parse_args()


def count_cues(p: Path) -> int:
    return len(re.findall(r"\d{2}:\d{2}:\d{2}[,\.]\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}[,\.]\d{3}",
                          p.read_text(encoding="utf-8")))


def main() -> int:
    args = parse_args()
    ensure_dirs()
    harness = load_harness()

    engine_id = args.engine or (harness.get("translation_engine") or {}).get("default", "local")
    providers = (harness.get("translation_engine") or {}).get("providers") or {}
    if engine_id not in providers and not args.dry_run:
        raise SystemExit(f"engine '{engine_id}' not in harness.translation_engine.providers: {list(providers)}")

    if args.dry_run:
        plan = {
            "url": args.url,
            "existing": str(args.existing) if args.existing else None,
            "sub": str(args.sub) if args.sub else None,
            "targets": args.targets,
            "stage_order": harness["stage_order"],
            "delivery_exclude": harness.get("delivery_exclude", []),
            "source_preference": harness.get("source_preference", []),
            "hardsub_mode": "clean" if args.clean_hardsub else harness.get("hardsub", {}).get("default_mode", "keep"),
            "engine_selected": engine_id,
            "provider": providers.get(engine_id),
        }
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0

    # ---- intake: download or reuse ----
    if args.existing:
        video_path = args.existing.resolve()
        if not video_path.exists():
            raise SystemExit(f"--existing not found: {video_path}")
        video_id = args.video_id or sanitize_stem(video_path.stem)
        log("orchestra", f"intake: reusing existing video {video_path}")
        report_path = synth_download_report(video_path, video_id)
        report = read_json(report_path)
    else:
        if not args.url:
            raise SystemExit("either url or --existing is required")
        log("orchestra", f"intake: {args.url}")
        download_cmd = py(str(SCRIPTS / "download_best.py"), args.url,
                          "--format", harness["download"]["format_expression"],
                          "--container", harness["download"]["merge_output_format"])
        result = run(download_cmd)
        report_path = Path(result.stdout.strip().splitlines()[-1])
        report = read_json(report_path)
        video_id = report["video_id"]
        if not report.get("file"):
            raise SystemExit("download did not produce a video path")
        video_path = ROOT / report["file"]

    project = {
        "id": video_id,
        "title": report.get("title") or video_id,
        "source_url": report.get("webpage_url") or (args.url if args.url else "(local)"),
        "source_language": args.source_lang or "auto",
        "targets": args.targets,
        "current_stage": "intake",
        "preferred_path": "track_subtitles",
        "fallback_path": ["asr_whisper"],
        "status": "in_progress",
        "notes": [f"started {time.strftime('%Y-%m-%d %H:%M:%S')}",
                  f"hardsub_mode={'clean' if args.clean_hardsub else 'keep'}"],
        "artifacts": {
            "download_report": str(report_path.relative_to(ROOT)) if ROOT in report_path.parents else str(report_path),
            "video": str(video_path.relative_to(ROOT)) if ROOT in video_path.parents else str(video_path),
        },
    }
    manifest_path = write_manifest(video_id, project)
    log("orchestra", f"manifest: {manifest_path}")

    # ---- source_probe: detect hardsub ----
    probe_path: Path | None = None
    if not args.skip_hardsub_probe:
        log("orchestra", "source_probe: hardsub detection")
        try:
            r = run(py(str(SCRIPTS / "detect_hardsub.py"), str(video_path), "--video-id", video_id))
            probe_path = Path(r.stdout.strip().splitlines()[-1])
        except subprocess.CalledProcessError as exc:
            log("orchestra", f"hardsub probe failed, continuing: {exc}")
    update_manifest(manifest_path, {
        "current_stage": "source_probe",
        "artifacts": {**project["artifacts"],
                      "hardsub_probe": str(probe_path.relative_to(ROOT)) if probe_path else None},
    })

    # ---- source_extraction: use provided --sub, else discover+pull, else ASR ----
    src_srt: Path | None = None
    chosen_track = args.source_lang or "auto"

    if args.sub:
        src_srt = args.sub.resolve()
        if not src_srt.exists():
            raise SystemExit(f"--sub not found: {src_srt}")
        log("orchestra", f"source_extraction: reusing {src_srt}")
    else:
        # If we have a URL we can query yt-dlp for track availability via the
        # existing download report; when reusing existing file, tracks are empty.
        if not report.get("available_subtitles") and not report.get("available_auto_captions") and args.url:
            # Re-fetch metadata only if reuse mode skipped initial listing
            log("orchestra", "subtitle_discovery: refreshing metadata")
            meta = fetch_remote_metadata(args.url)
            report["available_subtitles"] = sorted((meta.get("subtitles") or {}).keys())
            report["available_auto_captions"] = sorted((meta.get("automatic_captions") or {}).keys())
            write_json(report_path, report)

        log("orchestra", "subtitle_discovery + lang rank")
        r = run(py(str(SCRIPTS / "filter_langs.py"), str(report_path)))
        lang_report_path = Path(r.stdout.strip().splitlines()[-1])
        lang_report = read_json(lang_report_path)
        chosen_track = lang_report.get("recommended_source_track")

        if chosen_track and args.url:
            log("orchestra", f"source_extraction: pulling {chosen_track}")
            src_srt = pull_subtitle(args.url, video_id, chosen_track)
            if not src_srt or not src_srt.exists():
                log("orchestra", f"track pull failed; falling back to ASR")
                src_srt = None
        elif chosen_track and not args.url:
            log("orchestra", "tracks listed but no URL to pull from; falling back to ASR")

        if src_srt is None:
            log("orchestra", "source_extraction: ASR fallback (faster-whisper)")
            r = run(py(str(SCRIPTS / "transcribe_whisper.py"), str(video_path),
                       "--video-id", video_id, "--model", args.asr_model))
            src_srt = Path(r.stdout.strip().splitlines()[-1])
            chosen_track = "asr"

    # ---- hardsub cleanup (opt-in) ----
    clean_video = video_path
    if args.clean_hardsub and probe_path and read_json(probe_path).get("burned_in_detected"):
        log("orchestra", "hardsub: cleaning via delogo")
        r = run(py(str(SCRIPTS / "inpaint_hardsub.py"), str(video_path),
                   "--probe", str(probe_path),
                   "--out", str(video_path.with_name(video_path.stem + ".clean.mp4"))))
        clean_video = Path(r.stdout.strip().splitlines()[-1])
    else:
        if probe_path and read_json(probe_path).get("burned_in_detected"):
            log("orchestra", "hardsub detected but mode=keep; leaving video untouched")
    update_manifest(manifest_path, {"current_stage": "source_extraction",
                                    "source_language": chosen_track})

    # ---- translation ----
    log("orchestra", f"translation: engine={engine_id} targets={args.targets}")
    # Update the manifest to 'translation' BEFORE the subprocess so the UI
    # reflects the current stage during the long-running translate call.
    update_manifest(manifest_path, {"current_stage": "translation"})
    # Don't capture stderr so translate.py's per-batch progress streams to the
    # same log the web UI tails. Keep stdout captured to recover file paths.
    translate_cmd = py(str(SCRIPTS / "translate.py"), str(src_srt),
                       "--video-id", video_id, "--targets", *args.targets,
                       "--engine", engine_id)
    proc = subprocess.run(translate_cmd, check=True, text=True,
                           encoding="utf-8", errors="replace",
                           stdout=subprocess.PIPE)

    class _R:
        def __init__(self, stdout): self.stdout = stdout
    r = _R(proc.stdout)
    translated_paths = [Path(p) for p in r.stdout.strip().splitlines() if p.strip()]
    ko = next((p for p in translated_paths if p.name.endswith(".ko.srt")), None)
    es = next((p for p in translated_paths if p.name.endswith(".es.srt")), None)
    missing = []
    if "ko" in args.targets and not ko:
        missing.append("ko.srt")
    if "es" in args.targets and not es:
        missing.append("es.srt")
    if missing:
        raise SystemExit(f"translation missing outputs ({missing}): {translated_paths}")

    # ---- qa: cue count parity ----
    src_n = count_cues(src_srt)
    ko_n, es_n = count_cues(ko), count_cues(es)
    qa_ok = src_n == ko_n == es_n
    notes = list(project["notes"]) + [f"qa cue counts src={src_n} ko={ko_n} es={es_n} ok={qa_ok}"]
    update_manifest(manifest_path, {"current_stage": "qa", "notes": notes})

    # ---- export ----
    log("orchestra", "export: packaging")
    provider = providers.get(engine_id) or {}
    cmd = py(str(SCRIPTS / "package_export.py"),
             "--video-id", video_id,
             "--video", str(clean_video),
             "--ko-srt", str(ko),
             "--es-srt", str(es),
             "--download-report", str(report_path),
             "--source-lang", chosen_track,
             "--engine", engine_id,
             "--model", provider.get("model", ""))
    if probe_path:
        cmd += ["--probe", str(probe_path)]
    r = run(cmd)
    package_path = Path(r.stdout.strip().splitlines()[-1])
    update_manifest(manifest_path, {
        "current_stage": "export",
        "status": "completed" if qa_ok else "needs_review",
        "artifacts": {
            "package": str(package_path.relative_to(ROOT)) if ROOT in package_path.parents else str(package_path),
        },
    })
    log("orchestra", f"done. package={package_path}")
    print(package_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
