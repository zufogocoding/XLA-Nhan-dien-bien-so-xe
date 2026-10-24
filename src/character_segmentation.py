"""Segment characters inside one plate line."""

import cv2
import numpy as np

from .character_filter import filter_character_boxes
from .fix_broken import CharBox, merge_broken_components
from .fix_touching import split_touching_components


def connected_character_boxes(binary: np.ndarray) -> list[CharBox]:
    """Return bounding boxes of all 8-connected components."""
    if binary is None or binary.size == 0:
        raise ValueError("binary image is empty")
    if binary.ndim != 2:
        raise ValueError("binary image must be single-channel")
    count, _, stats, _ = cv2.connectedComponentsWithStats(
        (binary > 0).astype(np.uint8), connectivity=8
    )
    boxes = []
    for label in range(1, count):
        x, y, width, height, area = stats[label]
        if area < 4 or width < 1 or height < 2:
            continue
        boxes.append(CharBox(int(x), int(y), int(width), int(height)))
    return boxes


def _estimate_character_height(boxes: list[CharBox], line_height: int) -> float:
    if not boxes:
        return max(1.0, line_height * 0.72)
    heights = np.asarray([box.h for box in boxes], dtype=np.float32)
    tall = heights[heights >= 0.30 * max(1, line_height)]
    sample = tall if tall.size else heights
    return float(np.median(sample))


def _is_frame_like(box: CharBox, binary_line: np.ndarray) -> bool:
    """Reject border pieces that survived the plate-level frame cleanup."""
    line_height, line_width = binary_line.shape[:2]
    if box.w > 0.92 * line_width:
        return True
    if box.w > 0.55 * line_width and box.h < 0.35 * line_height:
        return True
    # Dots, hyphens and thin horizontal frame remnants.
    if box.h < 0.12 * line_height:
        return True
    # Thin vertical frame remnants, including slivers at a clipped edge.
    if box.w < 0.03 * line_width and box.h > 0.30 * line_height:
        return True
    if box.w / max(1, box.h) < 0.06 and box.h > 0.40 * line_height:
        return True

    touches_side = box.x <= 1 or box.x2 >= line_width - 2
    if touches_side and box.h >= 0.50 * line_height:
        return True

    # Frame pieces can sit just inside a skewed crop rather than on the exact
    # boundary. They are short and close to the top/bottom edge.
    cy = box.cy / max(1, line_height)
    if (cy < 0.18 or cy > 0.82) and box.h < 0.35 * line_height:
        return True

    if box.h >= 0.35 * line_height and box.w >= 0.18 * line_width:
        ink = cv2.countNonZero(binary_line[box.y : box.y2, box.x : box.x2])
        if ink / max(1, box.area) < 0.18:
            return True
    return False


def segment_text_line(
    binary_line: np.ndarray, line_index: int = 0, y_offset: int = 0
) -> list[CharBox]:
    """Segment one text line and return boxes in ``[x, y, w, h]`` form.

    Coordinates are relative to the input plate image (``y_offset`` is added),
    and boxes are ordered left to right.
    """
    if binary_line is None or binary_line.size == 0:
        return []
    line_height, line_width = binary_line.shape[:2]

    boxes = []
    for box in connected_character_boxes(binary_line):
        if _is_frame_like(box, binary_line):
            continue
        boxes.append(box)
    if not boxes:
        return []

    median_h = _estimate_character_height(boxes, line_height)
    boxes = merge_broken_components([box.to_tuple() for box in boxes], median_h)

    expected_h = _estimate_character_height(boxes, line_height)
    boxes = split_touching_components(binary_line, boxes, expected_h)
    boxes = filter_character_boxes(boxes, binary_line)

    shifted = [
        CharBox(box.x, box.y + y_offset, box.w, box.h)
        for box in sorted(boxes, key=lambda item: item.x)
    ]
    return shifted


__all__ = ["CharBox", "connected_character_boxes", "segment_text_line"]
