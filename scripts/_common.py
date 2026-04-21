from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"
DOWNLOAD_DIR = OUTPUTS / "downloads"
SUBTITLE_DIR = OUTPUTS / "subtitles"
REPORT_DIR = OUTPUTS / "reports"
PROBE_DIR = OUTPUTS / "probes"
TRANSLATED_DIR = OUTPUTS / "translated"
PACKAGE_DIR = OUTPUTS / "packages"
MANIFEST_DIR = OUTPUTS / "manifests"


def ensure_dirs() -> None:
    for d in (DOWNLOAD_DIR, SUBTITLE_DIR, REPORT_DIR, PROBE_DIR, TRANSLATED_DIR, PACKAGE_DIR, MANIFEST_DIR):
        d.mkdir(parents=True, exist_ok=True)


def run(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_stem(text: str) -> str:
    out = []
    for char in text:
        if char.isalnum() or char in ("-", "_"):
            out.append(char)
        else:
            out.append("_")
    return "".join(out).strip("_") or "video"


def log(stage: str, message: str) -> None:
    sys.stderr.write(f"[{stage}] {message}\n")
    sys.stderr.flush()
