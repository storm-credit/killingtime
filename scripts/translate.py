"""Translate a source SRT into Korean and Spanish.

Engine selection is driven by configs/pipeline/killingtime_harness.yml
`translation_engine.providers`. Supported runtimes:

  - ollama     (local, default)   no api key, needs ollama daemon
  - anthropic  (claude)           ANTHROPIC_API_KEY
  - google     (gemini)           GEMINI_API_KEY
  - openai     (gpt)              OPENAI_API_KEY

Cue indices and timestamps are preserved verbatim; only the text content
of each cue is rewritten. The prompt asks the model to keep cue count
stable and return valid SRT only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
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


def parse_srt_text(text: str) -> list[Cue]:
    tmp = Path("_tmp.srt")
    try:
        tmp.write_text(text, encoding="utf-8")
        return parse_srt(tmp)
    finally:
        if tmp.exists():
            tmp.unlink()


def write_srt(path: Path, cues: list[Cue]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for c in cues:
        out.append(str(c.index))
        out.append(f"{c.start} --> {c.end}")
        out.append(c.text)
        out.append("")
    path.write_text("\n".join(out), encoding="utf-8")


def load_engine_config(engine_id: str | None) -> tuple[str, dict, dict]:
    harness = yaml.safe_load((ROOT / "configs" / "pipeline" / "killingtime_harness.yml").read_text(encoding="utf-8"))
    eng = harness.get("translation_engine") or {}
    chosen = engine_id or eng.get("default") or "local"
    providers = eng.get("providers") or {}
    if chosen not in providers:
        raise SystemExit(f"engine '{chosen}' not found in harness.translation_engine.providers (have: {list(providers)})")
    return chosen, providers[chosen], eng


SYSTEM_PROMPT = (
    "You are Killing Time's Translation Lead.\n\n"
    "You receive subtitle cues and return translations that match the target\n"
    "language's spoken register. You must:\n\n"
    "1. Translate cue by cue. Return EXACTLY the same number of cues, in the same order.\n"
    "2. Preserve cue index numbers and timestamps. Only the text content changes.\n"
    "3. Keep each cue to at most 2 lines. Break for breath / readability, not word count.\n"
    "4. Prefer natural spoken phrasing over literal word-for-word rendering.\n"
    "5. Preserve proper nouns. Do not over-localize names.\n"
    "6. Never add commentary, notes, or content outside the SRT structure.\n\n"
    "Output format: valid SRT, nothing else. Do not wrap in code fences."
)


LANGUAGE_STYLE = {
    "ko": (
        "Target: Korean (ko-KR). Use natural everyday speech with appropriate 존댓말/반말\n"
        "for each speaker, matching emotional register. Avoid stiff literal translation."
    ),
    "es": (
        "Target: Spanish (neutral Latin American when ambiguous). Use natural\n"
        "spoken Spanish, contractions where a speaker would, keep emotional\n"
        "register matched to the source."
    ),
}


def build_user_text(target: str, cues: list[Cue]) -> str:
    srt = []
    for c in cues:
        srt.append(str(c.index))
        srt.append(f"{c.start} --> {c.end}")
        srt.append(c.text)
        srt.append("")
    return (
        f"{LANGUAGE_STYLE[target]}\n\n"
        "Translate the following SRT cues. Return only the translated SRT.\n\n"
        + "\n".join(srt).strip()
    )


# -- engine adapters --

def call_ollama(provider: dict, target: str, cues: list[Cue]) -> str:
    base_url = provider.get("base_url", "http://localhost:11434").rstrip("/")
    model = provider.get("model", "qwen2.5:7b")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_text(target, cues)},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"ollama unreachable at {base_url}: {exc}. "
            "Start the daemon (`ollama serve`) or pull the model (`ollama pull qwen2.5:7b`)."
        ) from exc
    return (data.get("message") or {}).get("content", "").strip()


def call_anthropic(provider: dict, target: str, cues: list[Cue]) -> str:
    if not os.getenv(provider.get("env_key", "ANTHROPIC_API_KEY")):
        raise SystemExit(f"{provider.get('env_key')} not set")
    try:
        from anthropic import Anthropic
    except ImportError as exc:
        raise SystemExit("anthropic sdk not installed. pip install anthropic") from exc
    client = Anthropic()
    resp = client.messages.create(
        model=provider["model"],
        max_tokens=8192,
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": [{"type": "text", "text": build_user_text(target, cues)}]}],
    )
    parts = []
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def call_google(provider: dict, target: str, cues: list[Cue]) -> str:
    if not os.getenv(provider.get("env_key", "GEMINI_API_KEY")):
        raise SystemExit(f"{provider.get('env_key')} not set")
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise SystemExit("google-generativeai not installed. pip install google-generativeai") from exc
    genai.configure(api_key=os.environ[provider.get("env_key", "GEMINI_API_KEY")])
    model = genai.GenerativeModel(
        provider["model"],
        system_instruction=SYSTEM_PROMPT,
    )
    resp = model.generate_content(
        build_user_text(target, cues),
        generation_config={"temperature": 0.2, "max_output_tokens": 8192},
    )
    return (resp.text or "").strip()


_VERTEX_DEGRADED = False


def _vertex_try(provider: dict, model_name: str, prompt: str) -> str:
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig
    vertexai.init(project=provider["project"], location=provider.get("location", "us-central1"))
    model = GenerativeModel(model_name, system_instruction=SYSTEM_PROMPT)
    config = GenerationConfig(temperature=0.2, max_output_tokens=8192)
    resp = model.generate_content(prompt, generation_config=config)
    return (resp.text or "").strip()


def call_vertex(provider: dict, target: str, cues: list[Cue]) -> str:
    import time
    global _VERTEX_DEGRADED
    key_path = os.getenv(provider.get("env_key", "GOOGLE_APPLICATION_CREDENTIALS"))
    if not key_path:
        raise SystemExit(f"{provider.get('env_key')} not set")
    if not os.path.exists(key_path):
        raise SystemExit(f"service account file not found: {key_path}")
    try:
        import vertexai  # noqa: F401
        from vertexai.generative_models import GenerativeModel  # noqa: F401
    except ImportError as exc:
        raise SystemExit("google-cloud-aiplatform not installed. pip install google-cloud-aiplatform") from exc

    primary = provider["model"]
    fallback = provider.get("fallback_model")
    prompt = build_user_text(target, cues)

    # If we've already fallen back on a previous batch, skip straight to it.
    if _VERTEX_DEGRADED and fallback:
        return _vertex_try(provider, fallback, prompt)

    # Try primary with backoff. 2 quota retries only so we fail over quickly.
    max_attempts = 2 if fallback else 6
    delay = 10.0
    for attempt in range(1, max_attempts + 1):
        try:
            return _vertex_try(provider, primary, prompt)
        except Exception as exc:
            msg = str(exc)
            is_quota = "RESOURCE_EXHAUSTED" in msg or "429" in msg or "quota" in msg.lower()
            is_retry = is_quota or "503" in msg or "UNAVAILABLE" in msg or "DEADLINE_EXCEEDED" in msg
            if is_quota and fallback:
                log("translate", f"vertex {primary} hit quota; degrading to fallback {fallback}")
                _VERTEX_DEGRADED = True
                return _vertex_try(provider, fallback, prompt)
            if attempt >= max_attempts or not is_retry:
                raise
            log("translate", f"vertex attempt {attempt} transient error; sleeping {delay:.0f}s")
            time.sleep(delay)
            delay = min(delay * 2, 60)
    raise RuntimeError("unreachable")


def call_openai(provider: dict, target: str, cues: list[Cue]) -> str:
    if not os.getenv(provider.get("env_key", "OPENAI_API_KEY")):
        raise SystemExit(f"{provider.get('env_key')} not set")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise SystemExit("openai not installed. pip install openai") from exc
    client = OpenAI()
    resp = client.chat.completions.create(
        model=provider["model"],
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_text(target, cues)},
        ],
        temperature=0.2,
        max_tokens=8192,
    )
    return (resp.choices[0].message.content or "").strip()


RUNTIMES = {
    "ollama": call_ollama,
    "anthropic": call_anthropic,
    "google": call_google,
    "vertex": call_vertex,
    "openai": call_openai,
}


def call_engine(engine_id: str, provider: dict, target: str, cues: list[Cue]) -> str:
    runtime = provider.get("runtime")
    fn = RUNTIMES.get(runtime)
    if not fn:
        raise SystemExit(f"unsupported runtime '{runtime}' for engine '{engine_id}'")
    return fn(provider, target, cues)


def chunk(cues: list[Cue], size: int) -> list[list[Cue]]:
    return [cues[i : i + size] for i in range(0, len(cues), size)]


def reconcile(source: list[Cue], translated_srt: str) -> list[Cue]:
    translated = parse_srt_text(translated_srt)
    if len(translated) != len(source):
        log("translate", f"cue count mismatch: source={len(source)} translated={len(translated)}; positional merge")
    out: list[Cue] = []
    for i, src in enumerate(source):
        if i < len(translated):
            out.append(Cue(index=src.index, start=src.start, end=src.end, text=translated[i].text))
        else:
            out.append(src)
    return out


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("source_srt", type=Path)
    ap.add_argument("--video-id", required=True)
    ap.add_argument("--targets", nargs="+", default=["ko", "es"])
    ap.add_argument("--engine", default=None, help="local | claude | gemini | vertex | gpt (default from harness)")
    ap.add_argument("--batch", type=int, default=40)
    ap.add_argument("--skip-until", type=int, default=0,
                    help="translate only cues with index >= this value (1-based); useful for resuming")
    ap.add_argument("--output-suffix", default="",
                    help="append this to output filename, e.g. '.part2' -> <video_id>.ko.part2.srt")
    return ap.parse_args()


def main() -> int:
    args = parse_args()
    ensure_dirs()
    engine_id, provider, _ = load_engine_config(args.engine)
    source = parse_srt(args.source_srt)
    if not source:
        raise SystemExit(f"no cues parsed from {args.source_srt}")
    if args.skip_until > 0:
        before = len(source)
        source = [c for c in source if c.index >= args.skip_until]
        log("translate", f"skip-until={args.skip_until}: kept {len(source)}/{before} cues")
    log("translate", f"engine={engine_id} runtime={provider.get('runtime')} model={provider.get('model')} cues={len(source)} targets={args.targets}")

    outputs: list[Path] = []
    for target in args.targets:
        if target not in LANGUAGE_STYLE:
            log("translate", f"skipping unsupported target {target}")
            continue
        merged: list[Cue] = []
        groups = chunk(source, args.batch)
        total = len(groups)
        import time as _time
        t0 = _time.time()
        for i, group in enumerate(groups, 1):
            b0 = _time.time()
            text = call_engine(engine_id, provider, target, group)
            merged.extend(reconcile(group, text))
            elapsed = _time.time() - t0
            batch_sec = _time.time() - b0
            eta_sec = (elapsed / i) * (total - i)
            log("translate", f"  [{target}] batch {i}/{total} ({batch_sec:.1f}s) · elapsed {elapsed/60:.1f}m · eta {eta_sec/60:.1f}m")
        suffix = args.output_suffix
        out_path = TRANSLATED_DIR / f"{args.video_id}.{target}{suffix}.srt"
        write_srt(out_path, merged)
        outputs.append(out_path)
        log("translate", f"wrote {out_path}")

    for p in outputs:
        sys.stdout.write(str(p) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
