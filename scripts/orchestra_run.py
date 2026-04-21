"""Orchestra runner for Killing Time.

Chains stages per configs/pipeline/killingtime_harness.yml:

  intake -> source_probe -> subtitle_discovery -> source_extraction
         -> translation -> qa -> export

Each step writes a JSON/SRT sidecar in outputs/. A project manifest is written
to outputs/manifests/<video_id>.yml for the web console to display progress.

The runner is conservative: if a stage's preferred tool is unavailable, the
fallback defined in the harness is attempted. ASR / OCR fallback is marked as
TODO for a future skill — this MVP prefers downloading subtitle tracks.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import yaml

from _common import (
    DOWNLOAD_DIR,
    MANIFEST_DIR,
    PROBE_DIR,
    REPORT_DIR,
    ROOT,
    SUBTITLE_DIR,
    TRANSLATED_DIR,
    ensure_dirs,
    log,
    read_json,
    run,
    write_json,
)


SCRIPTS = Path(__file__).resolve().parent


def py(*args: str) -> list[str]:
    return [sys.executable, *args]


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
    for cand in sorted(SUBTITLE_DIR.glob(f"{video_id}*.srt")):
        if track.split("-")[0] in cand.name or track in cand.name:
            return cand
    matches = sorted(SUBTITLE_DIR.glob(f"{video_id}*.srt"))
    return matches[0] if matches else None


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--targets", nargs="+", default=["ko", "es"])
    ap.add_argument("--skip-hardsub-probe", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="plan only, no network")
    return ap.parse_args()


def load_harness() -> dict:
    return yaml.safe_load((ROOT / "configs" / "pipeline" / "killingtime_harness.yml").read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    ensure_dirs()
    harness = load_harness()

    if args.dry_run:
        plan = {
            "url": args.url,
            "targets": args.targets,
            "stage_order": harness["stage_order"],
            "source_exclude": harness.get("source_exclude", []),
            "engine": harness.get("translation_engine", {}),
        }
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0

    # ---- intake ----
    log("orchestra", f"intake: {args.url}")
    download_cmd = py(str(SCRIPTS / "download_best.py"), args.url,
                      "--format", harness["download"]["format_expression"],
                      "--container", harness["download"]["merge_output_format"])
    result = run(download_cmd)
    report_path = Path(result.stdout.strip().splitlines()[-1])
    report = read_json(report_path)
    video_id = report["video_id"]

    project = {
        "id": video_id,
        "title": report.get("title") or video_id,
        "source_url": report.get("webpage_url") or args.url,
        "source_language": "auto",
        "targets": args.targets,
        "current_stage": "intake",
        "preferred_path": "yt_dlp_subtitles",
        "fallback_path": ["asr"],
        "status": "in_progress",
        "notes": [f"started {time.strftime('%Y-%m-%d %H:%M:%S')}"],
        "artifacts": {
            "download_report": str(report_path.relative_to(ROOT)),
            "video": report.get("file"),
        },
    }
    manifest_path = write_manifest(video_id, project)
    log("orchestra", f"manifest: {manifest_path}")

    video_rel = report.get("file")
    if not video_rel:
        raise SystemExit("download did not produce a video path")
    video_path = ROOT / video_rel

    # ---- source_probe (hardsub) ----
    probe_path: Path | None = None
    if not args.skip_hardsub_probe:
        log("orchestra", "source_probe: hardsub detection")
        try:
            r = run(py(str(SCRIPTS / "detect_hardsub.py"), str(video_path), "--video-id", video_id))
            probe_path = Path(r.stdout.strip().splitlines()[-1])
        except subprocess.CalledProcessError as exc:
            log("orchestra", f"hardsub probe failed, continuing: {exc}")
    update_manifest(manifest_path, {"current_stage": "source_probe",
                                    "artifacts": {**project["artifacts"],
                                                  "hardsub_probe": str(probe_path.relative_to(ROOT)) if probe_path else None}})

    # ---- subtitle_discovery + language gate ----
    log("orchestra", "subtitle_discovery + lang-filter-gate")
    r = run(py(str(SCRIPTS / "filter_langs.py"), str(report_path)))
    lang_report_path = Path(r.stdout.strip().splitlines()[-1])
    lang_report = read_json(lang_report_path)
    chosen_track = lang_report.get("recommended_source_track")
    if not chosen_track:
        raise SystemExit("no allowed subtitle track remains after language filter; ASR fallback not yet implemented in MVP")
    update_manifest(manifest_path, {"current_stage": "subtitle_discovery",
                                    "source_language": chosen_track})

    # ---- source_extraction: pull the track ----
    log("orchestra", f"source_extraction: pulling {chosen_track}")
    src_srt = pull_subtitle(args.url, video_id, chosen_track)
    if not src_srt or not src_srt.exists():
        raise SystemExit(f"failed to pull subtitle track {chosen_track}")

    # ---- inpaint if hardsub detected ----
    clean_video = video_path
    if probe_path and read_json(probe_path).get("burned_in_detected"):
        log("orchestra", "inpainting hardsub region")
        r = run(py(str(SCRIPTS / "inpaint_hardsub.py"), str(video_path),
                   "--probe", str(probe_path),
                   "--out", str(video_path.with_name(video_path.stem + ".clean.mp4"))))
        clean_video = Path(r.stdout.strip().splitlines()[-1])
    update_manifest(manifest_path, {"current_stage": "source_extraction"})

    # ---- translation (Claude) ----
    log("orchestra", f"translation: Claude targets={args.targets}")
    r = run(py(str(SCRIPTS / "translate_claude.py"), str(src_srt),
               "--video-id", video_id, "--targets", *args.targets))
    translated_paths = [Path(p) for p in r.stdout.strip().splitlines() if p.strip()]
    ko = next((p for p in translated_paths if p.name.endswith(".ko.srt")), None)
    es = next((p for p in translated_paths if p.name.endswith(".es.srt")), None)
    if not ko or not es:
        raise SystemExit(f"translation missing outputs: {translated_paths}")
    update_manifest(manifest_path, {"current_stage": "translation"})

    # ---- qa (automated minimal): cue count parity ----
    import re
    def count_cues(p: Path) -> int:
        return len(re.findall(r"\d{2}:\d{2}:\d{2}[,\.]\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}[,\.]\d{3}", p.read_text(encoding="utf-8")))
    src_n = count_cues(src_srt)
    ko_n, es_n = count_cues(ko), count_cues(es)
    qa_ok = src_n == ko_n == es_n
    update_manifest(manifest_path, {"current_stage": "qa",
                                    "notes": [*project["notes"], f"qa cue counts src={src_n} ko={ko_n} es={es_n} ok={qa_ok}"]})

    # ---- export ----
    log("orchestra", "export: packaging")
    engine = harness.get("translation_engine") or {}
    cmd = py(str(SCRIPTS / "package_export.py"),
             "--video-id", video_id,
             "--video", str(clean_video),
             "--ko-srt", str(ko),
             "--es-srt", str(es),
             "--download-report", str(report_path),
             "--source-lang", chosen_track,
             "--engine", engine.get("id", "claude-api"),
             "--model", engine.get("model", "claude-sonnet-4-6"))
    if probe_path:
        cmd += ["--probe", str(probe_path)]
    r = run(cmd)
    package_path = Path(r.stdout.strip().splitlines()[-1])
    update_manifest(manifest_path, {"current_stage": "export",
                                    "status": "completed" if qa_ok else "needs_review",
                                    "artifacts": {"package": str(package_path.relative_to(ROOT))}})
    log("orchestra", f"done. package={package_path}")
    print(package_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
