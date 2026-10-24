"""Filter character-sized components and remove noise, dots and frame pieces."""

import cv2
import numpy as np

from .fix_broken import CharBox


def _ink_area(binary: np.ndarray, box: CharBox) -> int:
    return cv2.countNonZero(binary[box.y : box.y2, box.x : box.x2])


def _iou(a: CharBox, b: CharBox) -> float:
    left, top = max(a.x, b.x), max(a.y, b.y)
    right, bottom = min(a.x2, b.x2), min(a.y2, b.y2)
    intersection = max(0, right - left) * max(0, bottom - top)
    return intersection / max(1, a.area + b.area - intersection)


def filter_character_boxes(
    boxes: list[CharBox],
    binary: np.ndarray,
    min_height_ratio: float = 0.42,
    max_height_ratio: float = 1.45,
    min_aspect: float = 0.05,
    max_aspect: float = 1.35,
    min_ink_density: float = 0.07,
) -> list[CharBox]:
    """Keep boxes with a plausible character height, aspect ratio and ink."""
    if not boxes:
        return []
    height, width = binary.shape[:2]
    if height <= 0 or width <= 0:
        return []

    rough = []
    for box in boxes:
        if box.w < 2 or box.h < 3:
            continue
        # The line region may include a few rows of plate frame, so this gate
        # only removes tiny specks; the median-height gate below does the real
        # character size filtering.
        if box.h < max(3, 0.08 * height):
            continue
        if box.w > 0.90 * width:
            continue
        ink = _ink_area(binary, box)
        if ink < max(6, 0.004 * binary.size):
            continue
        rough.append(box)

    if not rough:
        return []

    heights = np.asarray([box.h for box in rough], dtype=np.float32)
    median_h = float(np.median(heights))
    if median_h <= 0:
        return []

    kept = []
    for box in rough:
        if box.h < min_height_ratio * median_h or box.h > max_height_ratio * median_h:
            continue
        aspect = box.w / max(1, box.h)
        if aspect < min_aspect or aspect > max_aspect:
            continue
        ink = _ink_area(binary, box)
        if ink / max(1, box.area) < min_ink_density:
            continue
        # Long thin remnants of the plate frame.
        if box.w > 0.40 * width and box.h > 0.80 * median_h:
            continue

        duplicate = False
        for index, other in enumerate(kept):
            if _iou(box, other) > 0.65:
                if box.area > other.area:
                    kept[index] = box
                duplicate = True
                break
        if not duplicate:
            kept.append(box)

    if not kept and rough:
        # Never throw away every glyph because of an over-aggressive filter.
        kept = sorted(rough, key=lambda box: box.area, reverse=True)[:1]
    return sorted(kept, key=lambda box: box.x)
