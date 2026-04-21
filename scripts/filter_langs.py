"""Language gate: rank available subtitle tracks for source selection.

New semantics (v2):
  - All subtitle tracks are candidates for the source (no exclusion).
  - They are ranked by harness.source_preference (best match first).
  - delivery_exclude is reported so the packaging stage can drop zh/en
    tracks from the final bundle, not from translation input.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from _common import REPORT_DIR, ROOT, ensure_dirs, log, read_json, write_json


def load_harness() -> dict:
    path = ROOT / "configs" / "pipeline" / "killingtime_harness.yml"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def normalize(code: str) -> str:
    return code.lower().strip()


def rank_tracks(available: list[str], preference: list[str]) -> list[str]:
    pref_norm = [normalize(p) for p in preference]
    def score(track: str) -> tuple[int, int, str]:
        norm = normalize(track)
        base = norm.split("-")[0]
        # exact match in preference beats base match
        for i, p in enumerate(pref_norm):
            if norm == p:
                return (0, i, track)
        for i, p in enumerate(pref_norm):
            if base == p.split("-")[0]:
                return (1, i, track)
        return (2, 999, track)
    return sorted(available, key=score)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("download_report", type=Path)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    rep = read_json(args.download_report)
    harness = load_harness()
    preference = harness.get("source_preference") or []
    delivery_exclude = {normalize(x) for x in (harness.get("delivery_exclude") or [])}

    subs = rep.get("available_subtitles") or []
    autos = rep.get("available_auto_captions") or []

    ranked_subs = rank_tracks(subs, preference)
    ranked_autos = rank_tracks(autos, preference)
    recommended = (ranked_subs + ranked_autos)[0] if (ranked_subs or ranked_autos) else None

    out = {
        "video_id": rep.get("video_id"),
        "source_preference": preference,
        "delivery_exclude": sorted(delivery_exclude),
        "ranked_subtitles": ranked_subs,
        "ranked_auto_captions": ranked_autos,
        "recommended_source_track": recommended,
        "tracks_available_total": len(subs) + len(autos),
    }
    log("lang-rank", f"recommended={recommended} subs={ranked_subs} autos={ranked_autos}")

    out_path = REPORT_DIR / f"{rep['video_id']}.langrank.json"
    write_json(out_path, out)
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
