"""Run WP1 on one image and optionally save the results for inspection."""

import argparse
import json
from pathlib import Path

import cv2

from src.pipeline_wp1 import detect_plate


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    result = detect_plate(args.image)
    if result is None:
        print("No plate candidate found")
    else:
        args.output.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(args.output / "plate_crop.png"), result["plate_crop"])
        cv2.imwrite(str(args.output / "plate_normalized.png"), result["plate_normalized"])
        print(json.dumps({key: value for key, value in result.items() if key not in ("plate_crop", "plate_normalized")}, indent=2))
