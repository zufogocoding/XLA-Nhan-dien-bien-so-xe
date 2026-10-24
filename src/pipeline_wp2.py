"""WP2 interface: plate image -> segmented, normalized characters."""

from pathlib import Path

import cv2
import numpy as np

from .binarization import binarize, remove_border_frame, to_gray
from .character_segmentation import segment_text_line
from .fix_broken import CharBox
from .line_separation import LineRegion, detect_lines
from .normalize_character import DEFAULT_SIZE, normalize_characters


MIN_WORK_WIDTH = 224
def _prepare(plate_image: np.ndarray) -> tuple[np.ndarray, float]:
    gray = to_gray(plate_image)
    if min(gray.shape[:2]) < 12:
        raise ValueError("plate image is too small for segmentation")
    scale = max(1.0, MIN_WORK_WIDTH / max(1, gray.shape[1]))
    if scale > 1.0:
        gray = cv2.resize(
            gray,
            (round(gray.shape[1] * scale), round(gray.shape[0] * scale)),
            interpolation=cv2.INTER_CUBIC,
        )
    return gray, scale


def _segment_once(
    gray: np.ndarray, method: str
) -> tuple[list[list[CharBox]], list[LineRegion], str, np.ndarray, np.ndarray, str]:
    binary, enhanced = binarize(gray, method=method)
    clean = remove_border_frame(binary)
    regions, line_type = detect_lines(clean)
    boxes_by_line = [
        segment_text_line(
            clean[region.y1 : region.y2],
            line_index=region.index,
            y_offset=region.y1,
        )
        for region in regions
    ]
    if not any(boxes_by_line):
        return [], [], "1_line", clean, enhanced, method
    return boxes_by_line, regions, line_type, clean, enhanced, method


def _median_height(boxes: list[CharBox]) -> float:
    if not boxes:
        return 0.0
    return float(np.median([box.h for box in boxes]))


def _finalize_lines(
    regions: list[LineRegion], boxes_by_line: list[list[CharBox]]
) -> tuple[list[LineRegion], list[list[CharBox]], str]:
    """Drop empty lines and lines whose glyph height is clearly inconsistent."""
    kept = [
        (region, boxes)
        for region, boxes in zip(regions, boxes_by_line)
        if boxes
    ]
    if not kept:
        return [], [], "1_line"

    if len(kept) == 2:
        heights = [_median_height(boxes) for _, boxes in kept]
        taller, shorter = max(heights), min(heights)
        if shorter > 0 and taller / shorter > 1.45:
            kept = [kept[int(np.argmax(heights))]]

    regions = [
        LineRegion(region.y1, region.y2, index)
        for index, (region, _) in enumerate(kept)
    ]
    boxes_by_line = [boxes for _, boxes in kept]
    line_type = "2_line" if len(kept) == 2 else "1_line"
    return regions, boxes_by_line, line_type


def _result_score(
    boxes_by_line: list[list[CharBox]], line_type: str, shape: tuple[int, int]
) -> float:
    """Heuristic quality score used to choose between threshold methods."""
    boxes = [box for line in boxes_by_line for box in line]
    total = len(boxes)
    if total == 0:
        return -100.0
    height, width = shape
    heights = np.asarray([box.h for box in boxes], dtype=np.float32)
    mean_h = max(1.0, float(heights.mean()))
    height_cv = float(heights.std() / mean_h)
    aspect = width / max(1, height)

    # Vietnamese plates normally have 7-9 characters.
    score = 3.0 * float(np.exp(-((total - 8) / 2.5) ** 2))
    score -= min(1.5, 2.0 * height_cv)
    if line_type == "2_line":
        if aspect >= 2.20:
            score -= 2.0
        elif aspect <= 1.70:
            score += 0.3
        if len(boxes_by_line) == 2:
            counts = [len(line) for line in boxes_by_line]
            if not (2 <= counts[0] <= 5 and 3 <= counts[1] <= 6):
                score -= 0.5
    elif aspect <= 1.30 and total >= 7:
        score -= 0.3

    touching_border = sum(
        1 for box in boxes if box.x <= 1 or box.x + box.w >= width - 1
    )
    score -= 0.15 * touching_border
    return float(score)


def segment_plate(plate_image: np.ndarray, size: int = DEFAULT_SIZE) -> dict:
    """Segment characters from a cropped plate image.

    Returns the WP2 interface plus debug metadata::

        {
          "characters": [np.ndarray, ...],   # size x size, white on black
          "positions": [(x, y, w, h), ...],  # coordinates in the input image
          "line_type": "1_line" | "2_line",
          "num_chars": int,
          # extras
          "char_binary": [...],
          "line_boxes": [(x, y, w, h), ...],
          "line_indices": [0, 0, 1, ...],
          "binary": np.ndarray,
          "normalized_size": int,
        }
    """
    if plate_image is None or np.asarray(plate_image).size == 0:
        raise ValueError("plate image is empty")
    gray, scale = _prepare(plate_image)
    original_h, original_w = to_gray(plate_image).shape[:2]
    shape = gray.shape[:2]

    candidates = []
    for method in ("otsu", "adaptive", "central"):
        result = _segment_once(gray, method)
        regions, boxes_by_line, line_type = _finalize_lines(result[1], result[0])
        score = _result_score(boxes_by_line, line_type, shape)
        candidates.append(
            (score, (regions, boxes_by_line, line_type, result[3], result[4], method))
        )
        if method == "otsu" and score >= 2.2:
            break

    _, chosen = max(candidates, key=lambda item: item[0])
    regions, boxes_by_line, line_type, clean, enhanced, method = chosen

    if not boxes_by_line:
        return {
            "characters": [],
            "positions": [],
            "line_type": "1_line",
            "num_chars": 0,
            "char_binary": [],
            "line_boxes": [],
            "line_indices": [],
            "binary": cv2.resize(
                clean, (original_w, original_h), interpolation=cv2.INTER_NEAREST
            ),
            "normalized_size": size,
            "binarization": method,
        }

    boxes = [box for line in boxes_by_line for box in line]
    line_indices = [
        index for index, line in enumerate(boxes_by_line) for _ in line
    ]

    gray_patches, binary_patches = normalize_characters(
        enhanced, clean, boxes, size=size
    )

    inverse = 1.0 / scale
    positions = [
        (
            int(round(box.x * inverse)),
            int(round(box.y * inverse)),
            max(1, int(round(box.w * inverse))),
            max(1, int(round(box.h * inverse))),
        )
        for box in boxes
    ]
    line_boxes = [
        (
            0,
            int(round(region.y1 * inverse)),
            original_w,
            max(1, int(round(region.height * inverse))),
        )
        for region in regions
    ]
    binary_vis = cv2.resize(
        clean, (original_w, original_h), interpolation=cv2.INTER_NEAREST
    )

    return {
        "characters": gray_patches,
        "positions": positions,
        "line_type": line_type,
        "num_chars": len(gray_patches),
        "char_binary": binary_patches,
        "line_boxes": line_boxes,
        "line_indices": line_indices,
        "binary": binary_vis,
        "normalized_size": size,
        "binarization": method,
    }


def segment_plate_file(path: str | Path, size: int = DEFAULT_SIZE) -> dict:
    """Read a plate crop from disk and segment it."""
    path = Path(path)
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot read image: {path}")
    return segment_plate(image, size=size)


__all__ = ["DEFAULT_SIZE", "segment_plate", "segment_plate_file"]
