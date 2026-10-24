"""Normalize a segmented character to a fixed, centered, white-on-black patch."""

import cv2
import numpy as np

from .fix_broken import CharBox


DEFAULT_SIZE = 32


def _tight_bounds(binary: np.ndarray) -> tuple[int, int, int, int] | None:
    columns = np.flatnonzero((binary > 0).any(axis=0))
    rows = np.flatnonzero((binary > 0).any(axis=1))
    if columns.size == 0 or rows.size == 0:
        return None
    return int(columns[0]), int(rows[0]), int(columns[-1]) + 1, int(rows[-1]) + 1


def normalize_histogram(values: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    """Robust min-max normalization using 2nd/98th percentiles."""
    sample = values[mask] if mask is not None else values.ravel()
    if sample.size == 0:
        return values
    low, high = np.percentile(sample, (2, 98))
    if high <= low:
        return values
    scaled = (values.astype(np.float32) - low) * (255.0 / (high - low))
    return np.clip(scaled, 0, 255).astype(np.uint8)


def normalize_character(
    gray: np.ndarray,
    binary: np.ndarray,
    size: int = DEFAULT_SIZE,
    target_height_ratio: float = 0.78,
    margin: int = 2,
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(gray_patch, binary_patch)`` of shape ``(size, size)``.

    The glyph is scaled by height so every character has a consistent height,
    then centered. ``gray_patch`` keeps anti-aliased stroke intensity for HOG
    and is always white-on-black; ``binary_patch`` is the cleaned 0/255 mask.
    """
    if gray is None or binary is None:
        raise ValueError("gray and binary patches are required")
    if gray.shape[:2] != binary.shape[:2]:
        raise ValueError("gray and binary must have the same shape")
    if size < 8 or margin < 0 or 2 * margin >= size:
        raise ValueError("invalid normalization size or margin")

    mask = (binary > 0).astype(np.uint8)
    if cv2.countNonZero(mask) == 0:
        blank = np.zeros((size, size), dtype=np.uint8)
        return blank, blank.copy()

    bounds = _tight_bounds(mask)
    if bounds is None:
        blank = np.zeros((size, size), dtype=np.uint8)
        return blank, blank.copy()
    x1, y1, x2, y2 = bounds
    mask = mask[y1:y2, x1:x2]
    glyph_gray = gray[y1:y2, x1:x2].copy()

    # Make whichever class is the glyph bright, independent of plate colors.
    glyph_pixels = glyph_gray[mask > 0]
    background_pixels = glyph_gray[mask == 0]
    if background_pixels.size and glyph_pixels.size:
        if glyph_pixels.mean() < background_pixels.mean():
            glyph_gray = 255 - glyph_gray
    glyph_gray = normalize_histogram(glyph_gray, mask > 0)

    # Keep a little anti-aliasing around the thresholded stroke.
    grown = cv2.dilate(mask, np.ones((3, 3), np.uint8), iterations=1)
    glyph_gray = np.where(grown > 0, glyph_gray, 0).astype(np.uint8)
    glyph_gray = cv2.addWeighted(glyph_gray, 0.75, mask * 255, 0.25, 0)

    height, width = glyph_gray.shape[:2]
    usable = size - 2 * margin
    target_h = max(1, round(usable * target_height_ratio))
    scale = min(target_h / max(1, height), usable / max(1, width))
    new_w = max(1, min(usable, round(width * scale)))
    new_h = max(1, min(usable, round(height * scale)))

    gray_patch = cv2.resize(glyph_gray, (new_w, new_h), interpolation=cv2.INTER_AREA)
    binary_patch = cv2.resize(mask * 255, (new_w, new_h), interpolation=cv2.INTER_NEAREST)

    gray_canvas = np.zeros((size, size), dtype=np.uint8)
    binary_canvas = np.zeros((size, size), dtype=np.uint8)
    left = (size - new_w) // 2
    top = (size - new_h) // 2
    gray_canvas[top : top + new_h, left : left + new_w] = gray_patch
    binary_canvas[top : top + new_h, left : left + new_w] = binary_patch
    return gray_canvas, binary_canvas


def normalize_characters(
    enhanced_gray: np.ndarray,
    binary: np.ndarray,
    boxes: list[CharBox],
    size: int = DEFAULT_SIZE,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Normalize every box from a full plate image."""
    gray_patches, binary_patches = [], []
    for box in boxes:
        gray_crop = enhanced_gray[box.y : box.y2, box.x : box.x2]
        binary_crop = binary[box.y : box.y2, box.x : box.x2]
        gray_patch, binary_patch = normalize_character(gray_crop, binary_crop, size=size)
        gray_patches.append(gray_patch)
        binary_patches.append(binary_patch)
    return gray_patches, binary_patches
