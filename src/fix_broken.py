"""Optional morphology for fragmented white character strokes."""

import cv2
import numpy as np

from .binarization import validate_binary


def fix_broken(binary: np.ndarray, *, kernel_size: tuple[int, int], method: str = "closing") -> np.ndarray:
    """Repair strokes with an explicitly supplied kernel to avoid blind merging."""
    validate_binary(binary)
    if len(kernel_size) != 2 or min(kernel_size) < 1:
        raise ValueError("kernel_size must contain two positive integers")
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_size)
    if method == "closing":
        return cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    if method == "dilation":
        return cv2.dilate(binary, kernel, iterations=1)
    raise ValueError("method must be 'closing' or 'dilation'")
