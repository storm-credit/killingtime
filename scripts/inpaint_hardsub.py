"""Mask and clean a burned-in subtitle region using ffmpeg.

Reads a probe report, picks the aggregated region (xywh in ratios),
and produces a cleaned mp4 using ffmpeg delogo filter as a conservative default.
For higher quality work, a future skill can swap in opencv inpainting per-frame.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from _common import DOWNLOAD_DIR, ensure_dirs, log, read_json, run


def build_delogo(region: list[float], width: int, height: int) -> str:
    x = max(0, int(region[0] * width))
    y = max(0, int(region[1] * height))
    w = min(width - x, int(region[2] * width))
    h = min(height - y, int(region[3] * height))
    w = max(w, 8)
    h = max(h, 8)
    return f"delogo=x={x}:y={y}:w={w}:h={h}:show=0"


def probe_dimensions(video: Path) -> tuple[int, int]:
    result = run([
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        str(video),
    ])
    w, h = result.stdout.strip().split(",")
    return int(w), int(h)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--probe", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=None)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    probe = read_json(args.probe)
    if not probe.get("burned_in_detected") or not probe.get("region"):
        log("inpaint", "probe indicates no burn-in; copying input")
        out = args.out or args.video.with_name(args.video.stem + ".clean.mp4")
        run(["ffmpeg", "-y", "-i", str(args.video), "-c", "copy", str(out)], capture=False)
        print(out)
        return 0

    width, height = probe_dimensions(args.video)
    delogo = build_delogo(probe["region"], width, height)
    out = args.out or args.video.with_name(args.video.stem + ".clean.mp4")
    cmd = [
        "ffmpeg", "-y", "-i", str(args.video),
        "-vf", delogo,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-c:a", "copy",
        str(out),
    ]
    log("inpaint", f"running delogo: {delogo}")
    run(cmd, capture=False)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
