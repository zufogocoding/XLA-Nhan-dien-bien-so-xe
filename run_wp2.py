"""Run WP2 on one image (via WP1) or on an already cropped plate."""

import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from src.pipeline_wp1 import detect_plate
from src.pipeline_wp2 import segment_plate


def character_grid(characters: list[np.ndarray], columns: int = 5) -> np.ndarray:
    size = characters[0].shape[0] if characters else 32
    scale = 3
    tile = size * scale
    gap = 10
    rows = max(1, (len(characters) + columns - 1) // columns)
    canvas = np.full(
        (rows * tile + (rows + 1) * gap, columns * tile + (columns + 1) * gap),
        245,
        dtype=np.uint8,
    )
    for index, character in enumerate(characters):
        row, column = divmod(index, columns)
        x = gap + column * (tile + gap)
        y = gap + row * (tile + gap)
        canvas[y : y + tile, x : x + tile] = cv2.resize(
            character, (tile, tile), interpolation=cv2.INTER_NEAREST
        )
        cv2.putText(
            canvas,
            str(index + 1),
            (x + 3, y + 13),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            140,
            1,
            cv2.LINE_AA,
        )
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path, help="car image, or plate crop with --plate")
    parser.add_argument("--plate", action="store_true", help="input is already a plate crop")
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--size", type=int, default=32)
    args = parser.parse_args()

    if args.plate:
        plate = cv2.imdecode(np.fromfile(args.image, dtype=np.uint8), cv2.IMREAD_COLOR)
        if plate is None:
            raise ValueError(f"cannot read image: {args.image}")
        detection = None
    else:
        detection = detect_plate(args.image)
        if detection is None:
            print(json.dumps({"error": "no plate detected"}, ensure_ascii=False))
            return 1
        plate = detection["plate_normalized"]

    result = segment_plate(plate, size=args.size)
    args.output.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output / "wp2_plate.png"), plate)
    cv2.imwrite(str(args.output / "wp2_binary.png"), result["binary"])
    cv2.imwrite(
        str(args.output / "wp2_characters.png"), character_grid(result["characters"])
    )
    metadata = {
        "line_type": result["line_type"],
        "num_chars": result["num_chars"],
        "positions": [list(position) for position in result["positions"]],
        "line_indices": result["line_indices"],
        "line_boxes": [list(line) for line in result["line_boxes"]],
        "binarization": result["binarization"],
        "normalized_size": result["normalized_size"],
    }
    if detection is not None:
        metadata["wp1_bbox"] = detection["bbox"]
        metadata["wp1_angle"] = detection["angle"]
    (args.output / "wp2_result.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
