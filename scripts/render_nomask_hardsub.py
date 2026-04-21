from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def run(command: list[str], cwd: Path | None = None) -> None:
    subprocess.run(command, check=True, cwd=str(cwd) if cwd else None)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render Korean hardsubs without masking burned-in subtitles.")
    parser.add_argument("video", help="Source video path")
    parser.add_argument("subtitle", help="Korean subtitle path")
    parser.add_argument("output", help="Output video path")
    parser.add_argument("--font-size", type=int, default=50)
    parser.add_argument("--margin-v", type=int, default=120)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    video = Path(args.video).resolve()
    subtitle = Path(args.subtitle).resolve()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    workdir = output.parent
    video_arg = Path(os.path.relpath(video, workdir)).as_posix()
    subtitle_arg = Path(os.path.relpath(subtitle, workdir)).as_posix()

    force_style = (
        "FontName=Malgun Gothic,"
        f"FontSize={args.font_size},"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00202020,"
        "BackColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=3,"
        "Shadow=0,"
        f"MarginV={args.margin_v},"
        "Alignment=2"
    )

    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "warning",
        "-i",
        video_arg,
        "-vf",
        f"subtitles={subtitle_arg}:charenc=UTF-8:force_style='{force_style}'",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p5",
        "-cq",
        "19",
        "-b:v",
        "0",
        "-movflags",
        "+faststart",
        "-c:a",
        "copy",
        output.name,
    ]
    run(command, cwd=workdir)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
