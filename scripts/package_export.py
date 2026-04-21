"""Assemble final export package: cleaned mp4 + ko/es SRT + upload guide."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from _common import PACKAGE_DIR, ensure_dirs, log, read_json, write_json


UPLOAD_GUIDE = """# Upload Guide — {title}

Source: {source_url}
Video ID: {video_id}

## Files in this package
{files_list}

## Recommended YouTube upload steps
1. Upload the cleaned video: `{video_name}` (H.264 / AAC, MP4).
2. In "Subtitles", add:
   - Korean (ko) — upload `{ko_name}` as a new subtitle track.
   - Spanish (es) — upload `{es_name}` as a new subtitle track.
3. In the description, credit the original source URL if re-uploading:
   `Original: {source_url}`
4. Mark the video unlisted first, review both subtitle tracks once more in the
   YouTube editor, then publish.

## Notes
- Hardsub handling: {hardsub_note}
- Source language used for translation: {source_lang}
- Translation engine: {engine} ({model})
"""


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--video", type=Path, required=True)
    ap.add_argument("--ko-srt", type=Path, required=True)
    ap.add_argument("--es-srt", type=Path, required=True)
    ap.add_argument("--download-report", type=Path, required=True)
    ap.add_argument("--probe", type=Path, default=None)
    ap.add_argument("--source-lang", default="auto")
    ap.add_argument("--engine", default="claude-api")
    ap.add_argument("--model", default="claude-sonnet-4-6")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    pkg = PACKAGE_DIR / args.video_id
    pkg.mkdir(parents=True, exist_ok=True)

    video_dst = pkg / f"{args.video_id}.mp4"
    ko_dst = pkg / f"{args.video_id}.ko.srt"
    es_dst = pkg / f"{args.video_id}.es.srt"
    shutil.copy2(args.video, video_dst)
    shutil.copy2(args.ko_srt, ko_dst)
    shutil.copy2(args.es_srt, es_dst)

    report = read_json(args.download_report)
    probe = read_json(args.probe) if args.probe and args.probe.exists() else {}
    hardsub_note = (
        "detected and cleaned via delogo filter" if probe.get("burned_in_detected") else "no burn-in detected"
    )
    guide_path = pkg / "UPLOAD_GUIDE.md"
    guide_path.write_text(
        UPLOAD_GUIDE.format(
            title=report.get("title") or args.video_id,
            source_url=report.get("webpage_url") or "(unknown)",
            video_id=args.video_id,
            files_list="\n".join(f"- {p.name}" for p in (video_dst, ko_dst, es_dst)),
            video_name=video_dst.name,
            ko_name=ko_dst.name,
            es_name=es_dst.name,
            hardsub_note=hardsub_note,
            source_lang=args.source_lang,
            engine=args.engine,
            model=args.model,
        ),
        encoding="utf-8",
    )

    manifest = {
        "video_id": args.video_id,
        "title": report.get("title"),
        "source_url": report.get("webpage_url"),
        "files": {
            "video": str(video_dst.name),
            "ko_srt": ko_dst.name,
            "es_srt": es_dst.name,
            "guide": guide_path.name,
        },
        "hardsub": probe.get("burned_in_detected", False),
        "source_lang": args.source_lang,
        "engine": args.engine,
        "model": args.model,
    }
    write_json(pkg / "manifest.json", manifest)
    log("export", f"package at {pkg}")
    print(pkg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
