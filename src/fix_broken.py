"""Repair characters that were split into several connected components."""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class CharBox:
    x: int
    y: int
    w: int
    h: int

    def __post_init__(self) -> None:
        self.x = int(self.x)
        self.y = int(self.y)
        self.w = int(self.w)
        self.h = int(self.h)

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    @property
    def area(self) -> int:
        return self.w * self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def to_tuple(self) -> tuple[int, int, int, int]:
        return self.x, self.y, self.w, self.h


def boxes_to_char_boxes(boxes: list[tuple[int, int, int, int]]) -> list[CharBox]:
    return [CharBox(*box) for box in boxes]


def _x_overlap_ratio(a: CharBox, b: CharBox) -> float:
    overlap = max(0, min(a.x2, b.x2) - max(a.x, b.x))
    return overlap / max(1, min(a.w, b.w))


def _y_overlap_ratio(a: CharBox, b: CharBox) -> float:
    overlap = max(0, min(a.y2, b.y2) - max(a.y, b.y))
    return overlap / max(1, min(a.h, b.h))


def _vertical_gap(a: CharBox, b: CharBox) -> int:
    return max(0, max(a.y, b.y) - min(a.y2, b.y2))


def _horizontal_gap(a: CharBox, b: CharBox) -> int:
    return max(0, max(a.x, b.x) - min(a.x2, b.x2))


def _union(a: CharBox, b: CharBox) -> CharBox:
    x1, y1 = min(a.x, b.x), min(a.y, b.y)
    x2, y2 = max(a.x2, b.x2), max(a.y2, b.y2)
    return CharBox(x1, y1, x2 - x1, y2 - y1)


def _should_merge(a: CharBox, b: CharBox, median_h: float) -> bool:
    x_overlap = _x_overlap_ratio(a, b)
    y_overlap = _y_overlap_ratio(a, b)
    vgap = _vertical_gap(a, b)
    hgap = _horizontal_gap(a, b)
    union = _union(a, b)

    # Stacked fragments (broken horizontal strokes, detached accents).
    if (
        x_overlap >= 0.55
        and vgap <= max(2, 0.18 * median_h)
        and union.h <= 1.35 * median_h
        and union.w <= 1.15 * max(a.w, b.w)
    ):
        return True

    # A one-pixel cut splitting a vertical stroke in two. Keep this strict:
    # adjacent characters often have a 2-3 px gap and must not be merged.
    if (
        hgap <= 1
        and y_overlap >= 0.60
        and union.w <= 0.90 * median_h
    ):
        return True

    # Small fragments sitting inside or right next to a large glyph.
    small, large = (a, b) if a.area <= b.area else (b, a)
    if small.area <= 0.18 * max(1, large.area):
        inside_x = large.x - 0.12 * median_h <= small.cx <= large.x2 + 0.12 * median_h
        near_y = (
            large.y - 0.22 * median_h <= small.cy <= large.y2 + 0.22 * median_h
        )
        if inside_x and near_y and union.w <= 1.25 * max(1, max(a.w, b.w)):
            return True

    return False


def merge_broken_components(
    boxes: list[tuple[int, int, int, int]], median_h: float | None = None
) -> list[CharBox]:
    """Greedily merge components that belong to the same character."""
    merged = boxes_to_char_boxes(boxes)
    if not merged:
        return []
    if median_h is None or median_h <= 0:
        median_h = float(np.median([box.h for box in merged]))
    median_h = max(1.0, float(median_h))

    changed = True
    while changed and len(merged) > 1:
        changed = False
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                if _should_merge(merged[i], merged[j], median_h):
                    merged[i] = _union(merged[i], merged[j])
                    del merged[j]
                    changed = True
                    break
            if changed:
                break
    return merged


def close_gaps(binary: np.ndarray, iterations: int = 1) -> np.ndarray:
    """Morphological closing used when strokes are broken by noise."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=iterations)
