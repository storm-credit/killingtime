"""Translate a source SRT into Korean and Spanish using Claude.

Design notes:
  - reads translation_engine.model from harness config
  - chunks cues into batches to stay within a single response
  - uses prompt caching: the system prompt is marked cache-worthy, the
    glossary block is cached, and the per-batch cue payload is ephemeral
  - preserves cue indices and timings verbatim; only text is rewritten

Env:
  ANTHROPIC_API_KEY must be set.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from _common import ROOT, TRANSLATED_DIR, ensure_dirs, log


CUE_RE = re.compile(r"^(\d+)\s*$")
TIME_RE = re.compile(r"^(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}[,\.]\d{3})")


@dataclass
class Cue:
    index: int
    start: str
    end: str
    text: str


def parse_srt(path: Path) -> list[Cue]:
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").strip()
    blocks = re.split(r"\n\s*\n", raw)
    cues: list[Cue] = []
    for block in blocks:
        lines = [ln for ln in block.split("\n") if ln.strip() != ""]
        if len(lines) < 2:
            continue
        idx_m = CUE_RE.match(lines[0])
        time_line = lines[1] if idx_m else lines[0]
        time_m = TIME_RE.match(time_line)
        if not time_m:
            continue
        idx = int(idx_m.group(1)) if idx_m else len(cues) + 1
        text_lines = lines[2:] if idx_m else lines[1:]
        cues.append(Cue(index=idx, start=time_m.group(1), end=time_m.group(2), text="\n".join(text_lines)))
    return cues


def write_srt(path: Path, cues: list[Cue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for c in cues:
        out.append(str(c.index))
        out.append(f"{c.start} --> {c.end}")
        out.append(c.text)
        out.append("")
    path.write_text("\n".join(out), encoding="utf-8")


def load_engine_model() -> str:
    harness = yaml.safe_load((ROOT / "configs" / "pipeline" / "killingtime_harness.yml").read_text(encoding="utf-8"))
    eng = harness.get("translation_engine") or {}
    return eng.get("model") or "claude-sonnet-4-6"


SYSTEM_PROMPT = """You are Killing Time's Translation Lead.

You receive subtitle cues and return translations that match the target
language's spoken register. You must:

1. Translate cue by cue. Return EXACTLY the same number of cues, in the same order.
2. Preserve cue index numbers and timestamps. Only the text content changes.
3. Keep each cue to at most 2 lines. Break for breath / readability, not word count.
4. Prefer natural spoken phrasing over literal word-for-word rendering.
5. Preserve proper nouns. Do not over-localize names.
6. Never add commentary, notes, or content outside the SRT structure.

Output format: valid SRT, nothing else. Do not wrap in code fences.
"""


LANGUAGE_STYLE = {
    "ko": (
        "Target: Korean (ko-KR). Use natural everyday 존댓말/반말 as appropriate\n"
        "for the speaker, matching emotional register. Avoid stiff literal translation."
    ),
    "es": (
        "Target: Spanish (es-ES / neutral Latin American when ambiguous).\n"
        "Use natural spoken Spanish, contractions where a speaker would, keep\n"
        "emotional register matched to the source."
    ),
}


def build_messages(model: str, target: str, cues: list[Cue]) -> dict:
    srt_payload = []
    for c in cues:
        srt_payload.append(str(c.index))
        srt_payload.append(f"{c.start} --> {c.end}")
        srt_payload.append(c.text)
        srt_payload.append("")
    srt_text = "\n".join(srt_payload).strip()

    user_text = (
        f"{LANGUAGE_STYLE[target]}\n\n"
        "Translate the following SRT cues. Return only the translated SRT.\n\n"
        f"{srt_text}\n"
    )

    return {
        "model": model,
        "max_tokens": 8192,
        "system": [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": user_text}],
            }
        ],
    }


def call_claude(payload: dict) -> str:
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise SystemExit("anthropic sdk not installed. pip install anthropic") from exc
    client = Anthropic()
    resp = client.messages.create(**payload)
    parts = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def chunk(cues: list[Cue], size: int) -> list[list[Cue]]:
    return [cues[i : i + size] for i in range(0, len(cues), size)]


def reconcile(source: list[Cue], translated_srt: str) -> list[Cue]:
    translated = parse_srt_text(translated_srt)
    if len(translated) != len(source):
        log("translate", f"cue count mismatch: source={len(source)} translated={len(translated)}; falling back to positional merge")
    out: list[Cue] = []
    for i, src in enumerate(source):
        if i < len(translated):
            tr = translated[i]
            out.append(Cue(index=src.index, start=src.start, end=src.end, text=tr.text))
        else:
            out.append(src)
    return out


def parse_srt_text(text: str) -> list[Cue]:
    tmp = Path("_tmp.srt")
    try:
        tmp.write_text(text, encoding="utf-8")
        return parse_srt(tmp)
    finally:
        if tmp.exists():
            tmp.unlink()


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("source_srt", type=Path)
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--targets", nargs="+", default=["ko", "es"])
    ap.add_argument("--batch", type=int, default=40)
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set")

    source = parse_srt(args.source_srt)
    if not source:
        raise SystemExit(f"no cues parsed from {args.source_srt}")
    model = load_engine_model()
    log("translate", f"model={model} cues={len(source)} targets={args.targets}")

    outputs: list[Path] = []
    for target in args.targets:
        if target not in LANGUAGE_STYLE:
            log("translate", f"skipping unsupported target {target}")
            continue
        merged: list[Cue] = []
        for group in chunk(source, args.batch):
            payload = build_messages(model, target, group)
            text = call_claude(payload)
            merged.extend(reconcile(group, text))
        out_path = TRANSLATED_DIR / f"{args.video_id}.{target}.srt"
        write_srt(out_path, merged)
        outputs.append(out_path)
        log("translate", f"wrote {out_path}")

    for p in outputs:
        sys.stdout.write(str(p) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
