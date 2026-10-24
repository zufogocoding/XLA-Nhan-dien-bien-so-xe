"""Split wide glyph components conservatively using erosion or projection."""

import cv2
import numpy as np

from .binarization import validate_binary
from .character_segmentation import segment_characters


def split_touching(binary: np.ndarray, *, max_iterations: int = 2) -> list[tuple[int, int, int, int]]:
    """Return boxes within a component, without altering the source character pixels.

    If neither erosion nor a projection valley produces plausible tall pieces,
    keep the original component for downstream diagnostics/filtering.
    """
    validate_binary(binary)
    if max_iterations < 1:
        raise ValueError("max_iterations must be positive")
    height, width = binary.shape
    if width <= height:
        return [(0, 0, width, height)]
    for iteration in range(1, max_iterations + 1):
        eroded = cv2.erode(binary, np.ones((1, 3), np.uint8), iterations=iteration)
        pieces = [b for b in segment_characters(eroded) if b[3] >= 0.6 * height and b[2] >= 2]
        if len(pieces) >= 2:
            # Restore box margins lost to erosion, bounded by adjacent pieces.
            centers = [x + w / 2 for x, _, w, _ in pieces]
            bounds = [0] + [round((a + b) / 2) for a, b in zip(centers, centers[1:])] + [width]
            return [(a, 0, b - a, height) for a, b in zip(bounds, bounds[1:])]
    projection = np.count_nonzero(binary, axis=0)
    left, right = max(1, round(width * 0.25)), min(width - 1, round(width * 0.75))
    if right > left:
        cut = left + int(np.argmin(projection[left:right]))
        if projection[cut] <= 0.2 * projection.max() and min(cut, width - cut) >= 0.2 * height:
            return [(0, 0, cut, height), (cut, 0, width - cut, height)]
    return [(0, 0, width, height)]
