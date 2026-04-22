"""Extract burned-in Chinese subtitles from a video as an SRT with accurate timing.

Strategy:
  - Sample frames at a steady rate (default 2 FPS).
  - Crop each frame to the subtitle region (user-specified or default mid-bottom).
  - Run PaddleOCR on the crop, collect Chinese text.
  - Merge consecutive frames with the same/very similar text into a single cue;
    the first frame is the cue start, the last is the cue end.
  - Write an SRT sidecar: outputs/subtitles/<video_id>.hardsub.srt
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from _common import SUBTITLE_DIR, ensure_dirs, log, run


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


def probe_dimensions(video: Path) -> tuple[int, int]:
    r = run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        str(video),
    ])
    w, h = r.stdout.strip().split(",")
    return int(w), int(h)


def extract_frames(video: Path, fps: float, crop: str, out_dir: Path) -> None:
    """Use ffmpeg to decimate + crop + scale the video into a sequence of JPGs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    vf = f"fps={fps},{crop}"
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video),
        "-vf", vf,
        "-q:v", "3",
        str(out_dir / "f%07d.jpg"),
    ]
    run(cmd, capture=False)


def normalize_text(text: str) -> str:
    """Collapse whitespace and strip punctuation-only artefacts."""
    text = re.sub(r"\s+", "", text or "")
    return text.strip()


def similar(a: str, b: str) -> bool:
    if a == b:
        return True
    if not a or not b:
        return False
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return short in long or _levenshtein_ratio(a, b) >= 0.85


def _levenshtein_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    la, lb = len(a), len(b)
    if la > 64 or lb > 64:
        return 0.0
    prev = list(range(lb + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * lb
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
        prev = cur
    distance = prev[-1]
    return 1.0 - distance / max(la, lb)


def fmt_ts(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms >= 1000:
        s += 1
        ms -= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def ocr_frames(frames: list[Path], lang: str) -> list[str]:
    from paddleocr import PaddleOCR
    try:
        ocr = PaddleOCR(lang=lang)
    except Exception as exc:
        raise SystemExit(f"failed to init PaddleOCR: {exc}")
    texts: list[str] = []
    for i, path in enumerate(frames):
        try:
            res = ocr.ocr(str(path))
        except Exception as exc:
            log("hardsub-ocr", f"skip frame {i}: {exc}")
            texts.append("")
            continue
        lines = []
        # PaddleOCR 3.x returns a list containing one dict per image with
        # rec_texts / rec_scores / dt_polys keys. 2.x returned nested list.
        if res and isinstance(res, list):
            first = res[0]
            if isinstance(first, dict):
                scores = first.get("rec_scores") or []
                texts_ = first.get("rec_texts") or []
                for text, conf in zip(texts_, scores):
                    if conf >= 0.6 and text and text.strip():
                        lines.append(text.strip())
            else:
                for line in first or []:
                    try:
                        _box, (text, conf) = line
                    except Exception:
                        continue
                    if conf >= 0.6 and text and text.strip():
                        lines.append(text.strip())
        texts.append(normalize_text(" ".join(lines)))
        if (i + 1) % 500 == 0:
            log("hardsub-ocr", f"ocr'd {i + 1}/{len(frames)} frames")
    return texts


def merge_cues(texts: list[str], fps: float, min_duration: float = 0.2) -> list[tuple[float, float, str]]:
    cues: list[tuple[float, float, str]] = []
    i = 0
    n = len(texts)
    while i < n:
        if not texts[i]:
            i += 1
            continue
        j = i + 1
        while j < n and similar(texts[i], texts[j]):
            j += 1
        start = i / fps
        end = j / fps
        if end - start >= min_duration:
            cues.append((start, end, texts[i]))
        i = j
    return cues


def write_srt(path: Path, cues: list[tuple[float, float, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for n, (start, end, text) in enumerate(cues, 1):
        lines.append(str(n))
        lines.append(f"{fmt_ts(start)} --> {fmt_ts(end)}")
        lines.append(text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--fps", type=float, default=2.0, help="frames per second to OCR")
    ap.add_argument("--top", type=float, default=0.55, help="top of subtitle region (0..1)")
    ap.add_argument("--bottom", type=float, default=0.82, help="bottom of subtitle region (0..1)")
    ap.add_argument("--lang", default="ch", help="paddleocr language: ch for Simplified Chinese, chinese_cht for Traditional")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    if not args.video.exists():
        raise FileNotFoundError(args.video)

    w, h = probe_dimensions(args.video)
    duration = probe_duration(args.video)
    y = int(h * args.top)
    crop_h = int(h * (args.bottom - args.top))
    crop = f"crop=iw:{crop_h}:0:{y}"
    log("hardsub", f"video {w}x{h}, {duration:.1f}s, crop {crop}, fps {args.fps}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        log("hardsub", f"decimating frames into {tmp_dir}")
        extract_frames(args.video, args.fps, crop, tmp_dir)
        frames = sorted(tmp_dir.glob("*.jpg"))
        log("hardsub", f"{len(frames)} frames, running paddleocr ({args.lang})")
        texts = ocr_frames(frames, args.lang)

    cues = merge_cues(texts, args.fps)
    out = SUBTITLE_DIR / f"{args.video_id}.hardsub.srt"
    write_srt(out, cues)
    log("hardsub", f"wrote {len(cues)} cues to {out}")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
