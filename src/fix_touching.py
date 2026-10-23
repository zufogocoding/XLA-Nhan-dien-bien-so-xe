"""Split characters that touch each other.

The main strategy is a vertical projection profile: a valley between two
touching glyphs is a column with very little ink. Erosion is used as a
fallback for heavily fused glyphs where no projection valley exists.
"""

import cv2
import numpy as np

from .fix_broken import CharBox


def _crop(binary: np.ndarray, box: CharBox) -> np.ndarray:
    return binary[box.y : box.y2, box.x : box.x2]


def _smooth_profile(profile: np.ndarray) -> np.ndarray:
    if profile.size < 3:
        return profile.astype(np.float32)
    return np.convolve(profile.astype(np.float32), np.ones(3) / 3.0, mode="same")


def _valley_groups(profile: np.ndarray, threshold: float) -> list[tuple[int, int, float]]:
    columns = np.flatnonzero(profile <= threshold)
    if columns.size == 0:
        return []
    groups = []
    start = previous = int(columns[0])
    for column in columns[1:]:
        column = int(column)
        if column == previous + 1:
            previous = column
            continue
        groups.append((start, previous + 1, float(profile[start : previous + 1].mean())))
        start = previous = column
    groups.append((start, previous + 1, float(profile[start : previous + 1].mean())))
    return groups


def _split_by_erosion(
    binary: np.ndarray, box: CharBox, expected_h: float, expected_w: float
) -> list[CharBox]:
    """Separate fused glyphs by eroding them apart, then restore box padding."""
    crop = _crop(binary, box)
    if crop.size == 0:
        return []
    eroded = cv2.erode(crop, np.ones((2, 2), np.uint8), iterations=1)
    count, _, stats, _ = cv2.connectedComponentsWithStats(eroded, connectivity=8)
    parts = []
    for label in range(1, count):
        x, y, bw, bh, area = stats[label]
        if area < max(6, 0.02 * crop.size):
            continue
        if bh < 0.45 * box.h or bw < 0.55 * expected_w:
            continue
        parts.append(
            CharBox(
                box.x + max(0, x - 1),
                box.y + max(0, y - 1),
                min(box.w, bw + 2),
                min(box.h, bh + 2),
            )
        )
    if len(parts) < 2:
        return []
    parts.sort(key=lambda part: part.x)
    return parts


def split_touching_box(
    binary: np.ndarray,
    box: CharBox,
    expected_h: float,
    expected_w: float | None = None,
    depth: int = 0,
) -> list[CharBox]:
    """Recursively split one connected component into character boxes."""
    if expected_w is None:
        expected_w = 0.45 * expected_h
    expected_w = max(1.0, float(expected_w))
    if expected_h <= 0 or depth >= 3:
        return [box]
    wide = box.w > 1.55 * expected_w and box.w > 0.65 * expected_h
    if not wide:
        return [box]

    crop = _crop(binary, box)
    if crop.size == 0:
        return [box]
    profile = _smooth_profile((crop > 0).sum(axis=0))
    margin = max(2, int(round(0.24 * expected_h)))
    if box.w - 2 * margin < max(4, int(round(0.60 * expected_w))):
        return [box]

    inner = profile[margin : box.w - margin]
    max_value = float(inner.max()) if inner.size else 0.0
    if max_value <= 0:
        return [box]
    groups = _valley_groups(inner, max(1.0, 0.12 * max_value))

    candidates = []
    for start, end, mean_value in groups:
        cut = margin + (start + end) // 2
        left_width = cut
        right_width = box.w - cut
        if left_width < 0.55 * expected_w or right_width < 0.55 * expected_w:
            continue
        left_ink = float(profile[:cut].sum())
        right_ink = float(profile[cut:].sum())
        if left_ink < 0.05 * max(1.0, profile.sum()) or right_ink < 0.05 * max(1.0, profile.sum()):
            continue
        candidates.append((mean_value, abs(cut - box.w / 2), cut))

    if not candidates:
        if box.w > 1.80 * expected_w:
            return _split_by_erosion(binary, box, expected_h, expected_w) or [box]
        return [box]

    # Prefer the deepest valley; break ties by closeness to the box center.
    _, _, cut = min(candidates)
    left = CharBox(box.x, box.y, cut, box.h)
    right = CharBox(box.x + cut, box.y, box.w - cut, box.h)
    parts = split_touching_box(binary, left, expected_h, expected_w, depth + 1)
    parts += split_touching_box(binary, right, expected_h, expected_w, depth + 1)
    return parts


def split_touching_components(
    binary: np.ndarray,
    boxes: list[CharBox],
    expected_h: float,
    expected_w: float | None = None,
) -> list[CharBox]:
    """Apply :func:`split_touching_box` to every component."""
    if expected_w is None:
        if boxes:
            median_w = float(np.median([box.w for box in boxes]))
            expected_w = min(median_w, 0.50 * expected_h)
        else:
            expected_w = 0.45 * expected_h
    result = []
    for box in boxes:
        result.extend(split_touching_box(binary, box, expected_h, expected_w))
    return result


def erode_for_split(binary: np.ndarray, iterations: int = 1) -> np.ndarray:
    """Public helper used for debugging heavily fused characters."""
    return cv2.erode(binary, np.ones((3, 3), np.uint8), iterations=iterations)
