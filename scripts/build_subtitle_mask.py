from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def build_mask(width: int, height: int, profile: str) -> np.ndarray:
    mask = np.zeros((height, width), dtype=np.uint8)

    if profile == "full":
        top_band = (
            int(width * 0.18),
            int(height * 0.57),
            int(width * 0.82),
            int(height * 0.68),
        )
        bottom_band = (
            int(width * 0.12),
            int(height * 0.66),
            int(width * 0.88),
            int(height * 0.77),
        )
    else:
        top_band = (
            int(width * 0.18),
            int(height * 0.10),
            int(width * 0.82),
            int(height * 0.40),
        )
        bottom_band = (
            int(width * 0.12),
            int(height * 0.33),
            int(width * 0.88),
            int(height * 0.62),
        )

    for x1, y1, x2, y2 in (top_band, bottom_band):
        cv2.rectangle(mask, (x1, y1), (x2, y2), 255, thickness=-1)

    # Soften edges to reduce obvious seams during removelogo reconstruction.
    mask = cv2.GaussianBlur(mask, (31, 31), 0)
    _, mask = cv2.threshold(mask, 8, 255, cv2.THRESH_BINARY)
    return mask


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a static mask for burned subtitle removal.")
    parser.add_argument("--width", type=int, required=True)
    parser.add_argument("--height", type=int, required=True)
    parser.add_argument(
        "--profile",
        choices=["full", "band"],
        default="full",
        help="Mask geometry for the full frame or a cropped subtitle band",
    )
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    mask = build_mask(args.width, args.height, args.profile)
    cv2.imwrite(str(output), mask)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
