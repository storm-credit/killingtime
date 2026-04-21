"""Download YouTube video at best available quality merged into MP4.

Policy comes from configs/pipeline/killingtime_harness.yml `download` block:
  format_expression: bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b
  merge_output_format: mp4
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _common import DOWNLOAD_DIR, REPORT_DIR, ensure_dirs, log, run, sanitize_stem, write_json


def fetch_metadata(url: str) -> dict:
    result = run([sys.executable, "-m", "yt_dlp", "--dump-single-json", "--no-warnings", url])
    return json.loads(result.stdout)


def download(url: str, video_id: str, format_expression: str, merge_format: str) -> Path:
    output_template = str(DOWNLOAD_DIR / f"{video_id}.%(ext)s")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", format_expression,
        "--merge-output-format", merge_format,
        "-o", output_template,
        "--no-warnings",
        url,
    ]
    run(cmd, capture=False)
    target = DOWNLOAD_DIR / f"{video_id}.{merge_format}"
    if not target.exists():
        candidates = list(DOWNLOAD_DIR.glob(f"{video_id}.*"))
        if candidates:
            target = candidates[0]
    return target


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Download best-quality YouTube video into MP4.")
    ap.add_argument("url")
    ap.add_argument("--format", default="bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b")
    ap.add_argument("--container", default="mp4")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()

    log("download", f"fetching metadata for {args.url}")
    meta = fetch_metadata(args.url)
    video_id = sanitize_stem(meta["id"])

    log("download", f"downloading {video_id} as {args.container}")
    path = download(args.url, video_id, args.format, args.container)

    report = {
        "video_id": video_id,
        "title": meta.get("title"),
        "channel": meta.get("channel"),
        "duration": meta.get("duration"),
        "webpage_url": meta.get("webpage_url"),
        "available_subtitles": sorted((meta.get("subtitles") or {}).keys()),
        "available_auto_captions": sorted((meta.get("automatic_captions") or {}).keys()),
        "file": str(path.relative_to(path.parents[2])) if path.exists() else None,
    }
    report_path = REPORT_DIR / f"{video_id}.download.json"
    write_json(report_path, report)
    log("download", f"report written: {report_path}")
    sys.stdout.write(str(report_path) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
