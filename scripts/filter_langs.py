"""Apply language-gate: drop excluded source languages from metadata tracks.

Reads harness source_exclude and the download report; emits a candidate
source-language list ranked for extraction.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from _common import REPORT_DIR, ROOT, ensure_dirs, log, read_json, write_json


def load_exclude() -> set[str]:
    harness = ROOT / "configs" / "pipeline" / "killingtime_harness.yml"
    data = yaml.safe_load(harness.read_text(encoding="utf-8"))
    return {x.lower() for x in (data.get("source_exclude") or [])}


def normalize(code: str) -> str:
    base = code.split("-")[0].lower()
    return base


def filter_tracks(tracks: list[str], exclude_norm: set[str]) -> list[str]:
    return [t for t in tracks if normalize(t) not in exclude_norm]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("download_report", type=Path)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    rep = read_json(args.download_report)
    exclude = load_exclude()
    exclude_norm = {normalize(x) for x in exclude}

    subs = rep.get("available_subtitles") or []
    autos = rep.get("available_auto_captions") or []
    kept_subs = filter_tracks(subs, exclude_norm)
    kept_autos = filter_tracks(autos, exclude_norm)

    dropped = {
        "subs": [t for t in subs if t not in kept_subs],
        "autos": [t for t in autos if t not in kept_autos],
    }
    log("lang-filter", f"excluded codes={sorted(exclude)} dropped={dropped}")

    out = {
        "video_id": rep.get("video_id"),
        "exclude": sorted(exclude),
        "kept_subtitles": kept_subs,
        "kept_auto_captions": kept_autos,
        "dropped": dropped,
        "recommended_source_track": (kept_subs or kept_autos or [None])[0],
    }
    out_path = REPORT_DIR / f"{rep['video_id']}.langfilter.json"
    write_json(out_path, out)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
