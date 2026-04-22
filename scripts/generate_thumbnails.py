"""Generate 3 webtoon/manhwa-style longform (16:9) thumbnails per job.

Strategy (v2 — copyright-safe generation):
  1. Pull one or two reference frames from the middle of the video (scene
     detect, then take a couple temporally spread picks).
  2. Feed them to Vertex `gemini-2.5-flash-image` with a stylization prompt
     to produce a NEW 16:9 illustration inspired by (not copied from) the
     footage.
  3. Save three thumbnails with three prompt variants (romantic close-up,
     emotional duo, dramatic wide). Emit a manifest the UI can pick from.

Fallback: if the image model is unavailable, fall back to the legacy ffmpeg
stylization pipeline.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path

import yaml

from _common import OUTPUTS, ROOT, ensure_dirs, log, run


# ---- Reference frame extraction ----

def probe_duration(video: Path) -> float:
    r = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video),
    ])
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def extract_reference_frame(video: Path, ts: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{ts:.3f}",
        "-i", str(video),
        "-frames:v", "1",
        "-q:v", "3",
        "-vf", "scale=-2:720",  # downscale to keep the upload small
        str(out),
    ], capture=False)


# ---- Vertex Gemini image generation ----

def load_vertex_config() -> dict:
    harness = yaml.safe_load((ROOT / "configs" / "pipeline" / "killingtime_harness.yml").read_text(encoding="utf-8"))
    engines = (harness.get("translation_engine") or {}).get("providers") or {}
    v = engines.get("vertex") or {}
    return {
        "project": v.get("project"),
        "location": v.get("location", "us-central1"),
        "env_key": v.get("env_key", "GOOGLE_APPLICATION_CREDENTIALS"),
    }


_ASPECT_HEADER = (
    "IMPORTANT: Output image MUST be landscape 16:9 aspect ratio (wider than "
    "tall), suitable for a YouTube longform thumbnail at 1920x1080 pixels. "
    "Ignore the aspect ratio of the reference image — ONLY use it for the "
    "character design and mood reference. The generated illustration MUST "
    "be horizontal. "
)

PROMPTS = [
    (
        "romantic-closeup",
        _ASPECT_HEADER +
        "Korean manhwa / webtoon-style illustration of the protagonist, "
        "medium close-up shot framed horizontally. Dramatic romantic lighting, "
        "soft warm colour grading, emotional expression, rose-tinted background "
        "gradient. Painterly anime art style, clean bold lines, detailed eyes, "
        "cinematic horizontal composition. No text, logos, or watermarks.",
    ),
    (
        "duo-emotional",
        _ASPECT_HEADER +
        "Korean webtoon illustration with two characters in an emotionally "
        "charged moment (embrace, tension, longing). Wide horizontal framing, "
        "both characters placed off-centre to fit 16:9, dramatic rim lighting, "
        "desaturated warm palette, soft gradient background. Manhwa art style, "
        "detailed shading. No text, watermarks, or logos.",
    ),
    (
        "wide-dramatic",
        _ASPECT_HEADER +
        "Wide cinematic Korean drama webtoon illustration: the protagonist "
        "placed on the right third, against an atmospheric backdrop (night "
        "city skyline, rain, luxurious interior) filling the left two-thirds. "
        "Rich dramatic lighting, bold colour accent, anime-stylized. Designed "
        "as a 16:9 YouTube longform thumbnail with empty negative space at "
        "top-left for an overlaid title. No text in the image.",
    ),
]


def gemini_generate(project: str, location: str, reference_bytes: bytes, mime: str, prompt: str) -> bytes | None:
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel, Part
    except ImportError:
        raise SystemExit("google-cloud-aiplatform not installed")

    vertexai.init(project=project, location=location)
    model = GenerativeModel("gemini-2.5-flash-image")
    parts = [
        Part.from_data(mime_type=mime, data=reference_bytes),
        Part.from_text(prompt),
    ]
    resp = model.generate_content(parts)

    # Find the first inline image in the response
    for cand in resp.candidates or []:
        for part in (cand.content.parts or []):
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "mime_type", "").startswith("image/"):
                data = inline.data
                if isinstance(data, str):
                    data = base64.b64decode(data)
                return data
    return None


# ---- Legacy ffmpeg fallback (kept for the offline case) ----

FALLBACK_CHAIN = (
    "split=2[bg][fg];"
    "[bg]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
    "boxblur=20:2,eq=saturation=1.4:brightness=-0.05[bgb];"
    "[fg]scale=-2:1080,edgedetect=low=0.1:high=0.3:mode=colormix,"
    "eq=saturation=1.6:contrast=1.15,unsharp=5:5:1.2:5:5:0.0,gblur=sigma=0.4[fgs];"
    "[bgb][fgs]overlay=(W-w)/2:0"
)


def fallback_ffmpeg_render(video: Path, ts: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{ts:.3f}",
        "-i", str(video),
        "-frames:v", "1",
        "-vf", FALLBACK_CHAIN,
        "-q:v", "2",
        str(out),
    ], capture=False)


# ---- Driver ----

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--force-fallback", action="store_true")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    if not args.video.exists():
        raise FileNotFoundError(args.video)

    thumbs_dir = OUTPUTS / "jobs" / args.video_id / "thumbnails"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    duration = probe_duration(args.video)
    # Three picks at 25 / 50 / 75% across the video as reference stills.
    ts_picks = [duration * p for p in (0.25, 0.5, 0.75)] if duration > 0 else [5, 10, 15]

    cfg = load_vertex_config()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        references: list[Path] = []
        for i, ts in enumerate(ts_picks):
            ref = tmp_dir / f"ref_{i}.jpg"
            try:
                extract_reference_frame(args.video, ts, ref)
                references.append(ref)
            except subprocess.CalledProcessError as exc:
                log("thumbs", f"frame extract failed at {ts:.1f}s: {exc}")

        if not references:
            raise SystemExit("no reference frames could be extracted")

        candidates: list[dict] = []
        use_fallback = args.force_fallback or not cfg.get("project") or not os.getenv(cfg["env_key"])

        for i, (label, prompt) in enumerate(PROMPTS[: args.count]):
            out = thumbs_dir / f"thumb_{i + 1}.jpg"
            ref = references[i % len(references)]
            gen_ok = False

            if not use_fallback:
                try:
                    log("thumbs", f"gemini-image generating {label}")
                    data = gemini_generate(
                        cfg["project"],
                        cfg["location"],
                        ref.read_bytes(),
                        "image/jpeg",
                        prompt,
                    )
                    if data:
                        out.write_bytes(data)
                        gen_ok = True
                except Exception as exc:
                    log("thumbs", f"gemini-image failed for {label}: {exc}; switching to fallback")
                    use_fallback = True

            if not gen_ok:
                log("thumbs", f"fallback ffmpeg render for {label}")
                fallback_ffmpeg_render(args.video, ts_picks[i % len(ts_picks)], out)

            candidates.append({
                "index": i,
                "style": label,
                "timestamp": round(ts_picks[i % len(ts_picks)], 3),
                "path": str(out.relative_to(ROOT)) if ROOT in out.parents else str(out),
                "filename": out.name,
                "source": "gemini-image" if gen_ok else "ffmpeg-fallback",
            })
            log("thumbs", f"rendered {out.name} ({label})")

    manifest = {"version": 2, "selected": None, "candidates": candidates}
    (thumbs_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    log("thumbs", f"manifest at {thumbs_dir / 'manifest.json'}")
    print(thumbs_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
