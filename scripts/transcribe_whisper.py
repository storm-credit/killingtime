"""ASR fallback: transcribe audio to SRT when no subtitle tracks exist.

Uses faster-whisper. Emits an SRT with segment-level timestamps.
Runs only when the orchestra runner finds 0 usable subtitle tracks.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from _common import SUBTITLE_DIR, ensure_dirs, log


def format_ts(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:
        secs += 1
        ms = 0
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{ms:03d}"


def transcribe(video: Path, model_size: str, language: str | None) -> list[tuple[float, float, str]]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SystemExit("faster-whisper not installed. pip install faster-whisper") from exc

    log("asr", f"loading model {model_size}")
    model = WhisperModel(model_size, device="auto", compute_type="auto")
    log("asr", f"transcribing {video.name} lang={language or 'auto'}")
    segments, info = model.transcribe(str(video), language=language, vad_filter=True)
    log("asr", f"detected language={info.language} duration={info.duration:.1f}s")
    cues = []
    for seg in segments:
        cues.append((seg.start, seg.end, (seg.text or "").strip()))
    return cues


def write_srt(path: Path, cues: list[tuple[float, float, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, (start, end, text) in enumerate(cues, start=1):
        if not text:
            continue
        lines.append(str(i))
        lines.append(f"{format_ts(start)} --> {format_ts(end)}")
        lines.append(text)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--model", default="small")
    ap.add_argument("--language", default=None,
                    help="Force source language code (zh, en, ja, ...); default auto-detect")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    if not args.video.exists():
        raise FileNotFoundError(args.video)
    cues = transcribe(args.video, args.model, args.language)
    if not cues:
        raise SystemExit("ASR produced no cues")
    out = SUBTITLE_DIR / f"{args.video_id}.whisper.srt"
    write_srt(out, cues)
    log("asr", f"wrote {out} cues={len(cues)}")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
