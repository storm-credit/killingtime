from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = ROOT / "outputs" / "downloads"
SUBTITLE_DIR = ROOT / "outputs" / "subtitles"
REPORT_DIR = ROOT / "outputs" / "reports"


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def yt_dlp_command(*args: str) -> list[str]:
    return [sys.executable, "-m", "yt_dlp", *args]


def fetch_metadata(url: str) -> dict[str, Any]:
    result = run_command(
        yt_dlp_command(
            "--dump-single-json",
            "--no-warnings",
            url,
        )
    )
    return json.loads(result.stdout)


def choose_source_language(metadata: dict[str, Any]) -> str | None:
    subtitles = metadata.get("subtitles", {}) or {}
    for candidate in ("zh-Hant", "zh-Hans", "zh", "en"):
        if candidate in subtitles:
            return candidate
    automatic = metadata.get("automatic_captions", {}) or {}
    for candidate in ("zh-Hant", "zh-Hans", "zh", "en"):
        if candidate in automatic:
            return candidate
    return None


def language_is_available(metadata: dict[str, Any], language: str) -> tuple[bool, str]:
    subtitles = metadata.get("subtitles", {}) or {}
    automatic = metadata.get("automatic_captions", {}) or {}
    if language in subtitles:
        return True, "subtitles"
    if language in automatic:
        return True, "automatic_captions"
    return False, ""


def sanitize_stem(text: str) -> str:
    safe = []
    for char in text:
        if char.isalnum() or char in ("-", "_"):
            safe.append(char)
        else:
            safe.append("_")
    return "".join(safe).strip("_")


def download_video(url: str, video_id: str) -> Path:
    output_template = str(DOWNLOAD_DIR / f"{video_id}.%(ext)s")
    command = yt_dlp_command(
        "-f",
        "bv*[ext=mp4][height<=720]+ba[ext=m4a]/b[ext=mp4][height<=720]/18",
        "--merge-output-format",
        "mp4",
        "-o",
        output_template,
        url,
    )
    run_command(command)
    return DOWNLOAD_DIR / f"{video_id}.mp4"


def download_subtitles(url: str, video_id: str, languages: list[str]) -> None:
    if not languages:
        return
    output_template = str(SUBTITLE_DIR / f"{video_id}.%(ext)s")
    command = yt_dlp_command(
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-format",
        "srt",
        "--convert-subs",
        "srt",
        "--sub-langs",
        ",".join(languages),
        "-o",
        output_template,
        url,
    )
    run_command(command)


def find_downloaded_subtitles(video_id: str) -> list[str]:
    matches = []
    for path in sorted(SUBTITLE_DIR.glob(f"{video_id}*.srt")):
        matches.append(str(path.relative_to(ROOT)))
    return matches


def build_report(
    metadata: dict[str, Any],
    requested_languages: list[str],
    download_video_enabled: bool,
    video_path: Path | None,
) -> dict[str, Any]:
    video_id = metadata["id"]
    available: dict[str, dict[str, str]] = {}
    for language in requested_languages:
        ok, kind = language_is_available(metadata, language)
        available[language] = {
            "available": ok,
            "source": kind if ok else "missing",
        }

    source_language = choose_source_language(metadata)

    report = {
        "video_id": video_id,
        "title": metadata.get("title"),
        "channel": metadata.get("channel"),
        "source_url": metadata.get("webpage_url"),
        "chosen_source_language": source_language,
        "requested_languages": requested_languages,
        "availability": available,
        "video_downloaded": download_video_enabled,
        "video_path": str(video_path.relative_to(ROOT)) if video_path and video_path.exists() else None,
        "subtitle_files": find_downloaded_subtitles(video_id),
    }
    return report


def write_report(video_id: str, report: dict[str, Any]) -> Path:
    report_path = REPORT_DIR / f"{video_id}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download a YouTube video and available subtitle files.")
    parser.add_argument("url", help="YouTube URL")
    parser.add_argument(
        "--langs",
        nargs="+",
        default=["zh-Hant", "ko", "es", "en"],
        help="Subtitle languages to fetch in order",
    )
    parser.add_argument(
        "--skip-video",
        action="store_true",
        help="Download only subtitles and metadata",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    SUBTITLE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    metadata = fetch_metadata(args.url)
    video_id = sanitize_stem(metadata["id"])

    selected_languages = []
    for language in args.langs:
        if language_is_available(metadata, language)[0]:
            selected_languages.append(language)

    if not selected_languages:
        raise RuntimeError("No requested subtitle languages are available for this video.")

    video_path: Path | None = None
    if not args.skip_video:
        video_path = download_video(args.url, video_id)

    download_subtitles(args.url, video_id, selected_languages)

    report = build_report(
        metadata=metadata,
        requested_languages=selected_languages,
        download_video_enabled=not args.skip_video,
        video_path=video_path,
    )
    report_path = write_report(video_id, report)

    payload = json.dumps(report, indent=2, ensure_ascii=False)
    sys.stdout.buffer.write(payload.encode("utf-8", errors="replace"))
    sys.stdout.buffer.write(f"\n\nReport written to: {report_path}\n".encode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
