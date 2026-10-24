"""Aspect-preserving 32x32 character normalization, selected by the user."""

import cv2
import numpy as np

from .binarization import validate_binary


def normalize_character(character: np.ndarray, size: int = 32, *, padding: int = 2) -> np.ndarray:
    validate_binary(character)
    if size not in (28, 32) or padding < 0 or 2 * padding >= size:
        raise ValueError("size must be 28 or 32 with usable padding")
    result = np.zeros((size, size), np.uint8)
    pixels = cv2.findNonZero(character)
    if pixels is None:
        return result
    x, y, width, height = cv2.boundingRect(pixels)
    glyph = character[y:y + height, x:x + width]
    scale = (size - 2 * padding) / max(width, height)
    new_width, new_height = max(1, round(width * scale)), max(1, round(height * scale))
    glyph = cv2.resize(glyph, (new_width, new_height), interpolation=cv2.INTER_NEAREST)
    top, left = (size - new_height) // 2, (size - new_width) // 2
    result[top:top + new_height, left:left + new_width] = cv2.equalizeHist(glyph)
    return result
