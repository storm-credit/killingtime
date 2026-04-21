from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FINAL_DIR = ROOT / "outputs" / "final"


def run(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(command, check=True, cwd=str(cwd) if cwd else None)


def make_softsub(video_path: Path, subtitle_path: Path, output_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(subtitle_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-map",
        "1:0",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-c:s",
        "mov_text",
        "-metadata:s:s:0",
        "language=ko",
        "-metadata:s:s:0",
        "title=Korean",
        str(output_path),
    ]
    run(command)


def make_softsub_mkv(video_path: Path, subtitle_path: Path, output_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(subtitle_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-map",
        "1:0",
        "-c:v",
        "copy",
        "-c:a",
        "copy",
        "-c:s",
        "srt",
        "-metadata:s:s:0",
        "language=kor",
        "-metadata:s:s:0",
        "title=Korean",
        "-disposition:s:0",
        "default",
        str(output_path),
    ]
    run(command)


def make_hardsub(video_path: Path, subtitle_path: Path, output_path: Path) -> None:
    subtitle_filter_path = Path("..") / "subtitles" / subtitle_path.name
    force_style = (
        "FontName=Malgun Gothic,"
        "FontSize=18,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00101010,"
        "BackColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=2,"
        "Shadow=0,"
        "MarginV=48,"
        "Alignment=2"
    )
    vf = f"subtitles={subtitle_filter_path.as_posix()}:force_style='{force_style}'"
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path.name),
        "-vf",
        vf,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-c:a",
        "copy",
        str(output_path.resolve()),
    ]
    run(command, cwd=video_path.parent)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create softsub and hardsub Korean subtitle outputs.")
    parser.add_argument("video", help="Source video path")
    parser.add_argument("subtitle", help="Korean subtitle path")
    parser.add_argument(
        "--stem",
        default="output",
        help="Output stem name inside outputs/final",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    video_path = Path(args.video).resolve()
    subtitle_path = Path(args.subtitle).resolve()
    stem = args.stem

    softsub_path = FINAL_DIR / f"{stem}.softsub.mp4"
    softsub_mkv_path = FINAL_DIR / f"{stem}.softsub.mkv"
    softsub_sidecar_path = FINAL_DIR / f"{stem}.softsub.srt"
    hardsub_path = FINAL_DIR / f"{stem}.hardsub.mp4"

    make_softsub(video_path, subtitle_path, softsub_path)
    make_softsub_mkv(video_path, subtitle_path, softsub_mkv_path)
    shutil.copyfile(subtitle_path, softsub_sidecar_path)
    make_hardsub(video_path, subtitle_path, hardsub_path)

    print(softsub_path)
    print(softsub_mkv_path)
    print(softsub_sidecar_path)
    print(hardsub_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
