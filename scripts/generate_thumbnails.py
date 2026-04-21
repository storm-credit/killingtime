"""Generate 3 longform (16:9) thumbnail candidates per job.

Approach:
  1. Scene-detect candidate frames, pick 3 temporally spread.
  2. For each frame, build a 1920x1080 composite:
     - background: same frame scaled to cover, heavily blurred + desaturated.
     - foreground: same frame pillarboxed at 1080 height, anime-style
       edge + vibrance + unsharp filter chain.
  3. Write jpgs to outputs/jobs/{videoId}/thumbnails/thumb_{1,2,3}.jpg
  4. Emit manifest.json with candidate metadata (selected=null).

Optional: Claude/Vertex-backed short captions (skipped if unavailable).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from _common import OUTPUTS, ROOT, ensure_dirs, log, run


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


def scene_timestamps(video: Path, threshold: float = 0.4) -> list[float]:
    """Run ffmpeg scene filter and parse pts_time values."""
    cmd = [
        "ffmpeg", "-hide_banner", "-i", str(video),
        "-vf", f"select='gt(scene,{threshold})',showinfo",
        "-vsync", "vfr",
        "-f", "null", "-",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    except subprocess.TimeoutExpired:
        return []
    ts: list[float] = []
    for m in re.finditer(r"pts_time:(\d+\.?\d*)", r.stderr):
        try:
            ts.append(float(m.group(1)))
        except ValueError:
            continue
    return ts


def pick_spread(timestamps: list[float], count: int, duration: float) -> list[float]:
    if not timestamps:
        if duration <= 0:
            return [0.0, 0.0, 0.0][:count]
        return [duration * p for p in (0.2, 0.5, 0.8)][:count]
    timestamps = sorted(timestamps)
    if len(timestamps) <= count:
        return timestamps
    chosen: list[float] = [timestamps[len(timestamps) // 5]]
    while len(chosen) < count:
        best = max(timestamps, key=lambda t: min(abs(t - c) for c in chosen))
        chosen.append(best)
        chosen = sorted(chosen)
    return sorted(chosen)


FILTER_CHAIN = (
    "split=2[bg][fg];"
    "[bg]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,"
    "boxblur=20:2,eq=saturation=1.4:brightness=-0.05[bgb];"
    "[fg]scale=-2:1080,edgedetect=low=0.1:high=0.3:mode=colormix,"
    "eq=saturation=1.6:contrast=1.15,unsharp=5:5:1.2:5:5:0.0,gblur=sigma=0.4[fgs];"
    "[bgb][fgs]overlay=(W-w)/2:0"
)


def render_one(video: Path, ts: float, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{ts:.3f}",
        "-i", str(video),
        "-frames:v", "1",
        "-vf", FILTER_CHAIN,
        "-q:v", "2",
        str(out),
    ]
    run(cmd, capture=False)


def write_manifest(thumbs_dir: Path, candidates: list[dict]) -> Path:
    manifest = {
        "version": 1,
        "selected": None,
        "candidates": candidates,
    }
    path = thumbs_dir / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--threshold", type=float, default=0.4)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    if not args.video.exists():
        raise FileNotFoundError(args.video)

    thumbs_dir = OUTPUTS / "jobs" / args.video_id / "thumbnails"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    duration = probe_duration(args.video)
    log("thumbs", f"duration={duration:.1f}s, scene-detecting")
    scenes = scene_timestamps(args.video, args.threshold)
    log("thumbs", f"{len(scenes)} scenes detected")
    picks = pick_spread(scenes, args.count, duration)
    log("thumbs", f"picked timestamps: {picks}")

    candidates: list[dict] = []
    for i, ts in enumerate(picks):
        out = thumbs_dir / f"thumb_{i + 1}.jpg"
        try:
            render_one(args.video, ts, out)
            candidates.append({
                "index": i,
                "timestamp": round(ts, 3),
                "path": str(out.relative_to(ROOT)) if ROOT in out.parents else str(out),
                "filename": out.name,
            })
            log("thumbs", f"rendered {out.name} @ {ts:.1f}s")
        except subprocess.CalledProcessError as exc:
            log("thumbs", f"failed frame {i}: {exc}")

    manifest = write_manifest(thumbs_dir, candidates)
    log("thumbs", f"manifest at {manifest}")
    print(thumbs_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
