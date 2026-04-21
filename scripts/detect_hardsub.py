"""Probe a video for burned-in subtitles using sampled frames.

Strategy:
  - sample N frames across the duration via ffmpeg
  - run PaddleOCR on the bottom strip (default bottom 30%)
  - classify language family per detection; if most detections are zh or en,
    flag as burned-in and emit the bounding region

Outputs a probe report with region (xywh ratios), confidence, detected languages.
If paddleocr is unavailable the script returns a low-confidence "unknown" probe
so the pipeline can skip inpainting.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from _common import PROBE_DIR, ensure_dirs, log, run, write_json


def sample_frames(video: Path, count: int, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    result = run([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video),
    ])
    try:
        duration = float(result.stdout.strip())
    except ValueError:
        duration = 0.0
    frames: list[Path] = []
    if duration <= 0:
        run(["ffmpeg", "-y", "-i", str(video), "-frames:v", "1", str(out_dir / "frame_0.jpg")])
        frames.append(out_dir / "frame_0.jpg")
        return frames
    step = duration / (count + 1)
    for i in range(count):
        t = step * (i + 1)
        out = out_dir / f"frame_{i:02d}.jpg"
        run([
            "ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", str(video),
            "-frames:v", "1", "-q:v", "3", str(out),
        ])
        if out.exists():
            frames.append(out)
    return frames


def classify_language(text: str) -> str:
    has_cjk = any("\u4e00" <= c <= "\u9fff" for c in text)
    if has_cjk:
        return "zh"
    stripped = "".join(ch for ch in text if ch.isalpha())
    if stripped and all(ord(ch) < 128 for ch in stripped):
        return "en"
    return "other"


def ocr_frames(frames: list[Path], bottom_ratio: float) -> dict[str, Any]:
    try:
        from paddleocr import PaddleOCR
    except Exception as exc:  # pragma: no cover
        log("hardsub", f"paddleocr unavailable ({exc}); returning unknown probe")
        return {"available": False, "detections": [], "languages": {}, "regions": []}

    ocr = PaddleOCR(use_angle_cls=False, lang="ch", show_log=False)
    detections = []
    languages: dict[str, int] = {}
    regions = []
    from PIL import Image  # Pillow is a paddleocr dep

    for frame in frames:
        with Image.open(frame) as im:
            w, h = im.size
            crop_top = int(h * (1 - bottom_ratio))
            strip = im.crop((0, crop_top, w, h))
            strip_path = frame.with_name(frame.stem + "_strip.jpg")
            strip.save(strip_path)
        try:
            result = ocr.ocr(str(strip_path), cls=False)
        except Exception as exc:
            log("hardsub", f"ocr failed on {frame.name}: {exc}")
            continue
        if not result:
            continue
        for line in result[0] or []:
            box, (text, conf) = line
            if conf < 0.6 or not text.strip():
                continue
            lang = classify_language(text)
            languages[lang] = languages.get(lang, 0) + 1
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x = min(xs) / w
            y = (crop_top + min(ys)) / h
            bw = (max(xs) - min(xs)) / w
            bh = (max(ys) - min(ys)) / h
            detections.append({"text": text, "conf": float(conf), "lang": lang})
            regions.append([x, y, bw, bh])
    return {"available": True, "detections": detections, "languages": languages, "regions": regions}


def aggregate_region(regions: list[list[float]]) -> list[float] | None:
    if not regions:
        return None
    xs = [r[0] for r in regions]
    ys = [r[1] for r in regions]
    rs = [r[0] + r[2] for r in regions]
    bs = [r[1] + r[3] for r in regions]
    x = max(0.0, min(xs) - 0.02)
    y = max(0.0, min(ys) - 0.02)
    w = min(1.0 - x, max(rs) - x + 0.02)
    h = min(1.0 - y, max(bs) - y + 0.02)
    return [x, y, w, h]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--samples", type=int, default=8)
    ap.add_argument("--bottom", type=float, default=0.3)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    if not args.video.exists():
        raise FileNotFoundError(args.video)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        frames = sample_frames(args.video, args.samples, tmp_path)
        log("hardsub", f"sampled {len(frames)} frames for ocr")
        ocr = ocr_frames(frames, args.bottom)

    langs = ocr.get("languages") or {}
    total = sum(langs.values()) or 1
    burned_langs = [lang for lang, count in langs.items() if lang in {"zh", "en"} and count / total >= 0.25]
    confidence = 0.0
    if ocr.get("detections"):
        confidence = sum(d["conf"] for d in ocr["detections"]) / len(ocr["detections"])
    region = aggregate_region(ocr.get("regions") or [])

    probe = {
        "video_id": args.video_id,
        "ocr_available": ocr.get("available"),
        "burned_in_detected": bool(burned_langs) and confidence >= 0.7,
        "burned_in_languages": burned_langs,
        "confidence": round(confidence, 3),
        "region": region,
        "samples": len(ocr.get("detections") or []),
    }
    out_path = PROBE_DIR / f"{args.video_id}.hardsub.json"
    write_json(out_path, probe)
    log("hardsub", f"probe: burned={probe['burned_in_detected']} langs={burned_langs} region={region}")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
