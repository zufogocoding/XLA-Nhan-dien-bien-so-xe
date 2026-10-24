"""Binarization helpers for WP2.

The rest of the WP2 pipeline expects a binary image where glyph pixels are
white (255) and the plate background is black (0), regardless of whether the
input plate has dark characters on a light background (white/yellow plates)
or light characters on a dark background (blue plates).
"""

import cv2
import numpy as np


def to_gray(image: np.ndarray) -> np.ndarray:
    """Return a grayscale copy of a grayscale, BGR or BGRA image."""
    if image is None or image.size == 0:
        raise ValueError("image is empty")
    if image.ndim == 2:
        return image.copy()
    if image.ndim == 3 and image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    if image.ndim == 3 and image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    raise ValueError("expected a grayscale, BGR or BGRA image")


def enhance_gray(gray: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    """Apply CLAHE to make faded plates easier to threshold."""
    return cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8)).apply(gray)


def _adaptive_block_size(height: int, width: int) -> int:
    """Pick an odd adaptive-threshold window that always fits the image."""
    shortest = min(height, width)
    block = max(3, (shortest // 6) | 1)
    return min(31, block)


def otsu_binary(gray: np.ndarray) -> np.ndarray:
    """Otsu threshold with the majority class treated as background."""
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if cv2.countNonZero(binary) > binary.size * 0.5:
        binary = cv2.bitwise_not(binary)
    return binary


def adaptive_binary(gray: np.ndarray, c: float = 2.0) -> np.ndarray:
    """Adaptive Gaussian threshold for uneven illumination."""
    block = _adaptive_block_size(*gray.shape[:2])
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, block, c
    )
    if cv2.countNonZero(binary) > binary.size * 0.5:
        binary = cv2.bitwise_not(binary)
    return binary


def central_otsu_binary(gray: np.ndarray, margin: float = 0.12) -> np.ndarray:
    """Otsu threshold fitted on the plate center.

    A loosely cropped plate can contain a bright car body around it. Global
    Otsu then splits "car body vs plate" instead of "plate vs glyph". Fitting
    the threshold on the central region avoids that failure mode.
    """
    height, width = gray.shape[:2]
    y1, y2 = int(height * margin), max(int(height * margin) + 1, int(height * (1 - margin)))
    x1, x2 = int(width * margin), max(int(width * margin) + 1, int(width * (1 - margin)))
    region = gray[y1:y2, x1:x2]
    threshold, _ = cv2.threshold(
        region, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    if region.mean() > 127:
        binary = (gray < threshold).astype(np.uint8) * 255
    else:
        binary = (gray > threshold).astype(np.uint8) * 255
    return binary


def binarize(
    image: np.ndarray, method: str = "otsu", apply_clahe: bool = True
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(binary, enhanced_gray)`` for a plate image.

    ``binary`` has white glyphs. ``enhanced_gray`` is the grayscale image that
    was thresholded and is reused when normalizing characters.
    """
    gray = to_gray(image)
    work = enhance_gray(gray) if apply_clahe else gray
    if method == "otsu":
        binary = otsu_binary(work)
    elif method == "adaptive":
        binary = adaptive_binary(work)
    elif method == "central":
        binary = central_otsu_binary(work)
    elif method == "none":
        binary = otsu_binary(work)
    else:
        raise ValueError(f"unknown binarization method: {method}")
    return binary, work


def _clear_edge_rows_and_columns(
    binary: np.ndarray, foreground_ratio: float = 0.55, band_ratio: float = 0.035
) -> np.ndarray:
    """Erase frame lines that run along the crop boundary."""
    out = binary.copy()
    height, width = out.shape[:2]
    band_y = max(1, round(height * band_ratio))
    band_x = max(1, round(width * band_ratio))
    for y in range(band_y):
        if cv2.countNonZero(out[y, :]) / max(1, width) > foreground_ratio:
            out[y, :] = 0
        if cv2.countNonZero(out[height - 1 - y, :]) / max(1, width) > foreground_ratio:
            out[height - 1 - y, :] = 0
    for x in range(band_x):
        if cv2.countNonZero(out[:, x]) / max(1, height) > foreground_ratio:
            out[:, x] = 0
        if cv2.countNonZero(out[:, width - 1 - x]) / max(1, height) > foreground_ratio:
            out[:, width - 1 - x] = 0
    return out


def _remove_frame_components(
    binary: np.ndarray, span_ratio: float = 0.72
) -> np.ndarray:
    """Remove connected components that look like the plate frame."""
    out = binary.copy()
    height, width = out.shape[:2]
    count, labels, stats, _ = cv2.connectedComponentsWithStats(
        (out > 0).astype(np.uint8), connectivity=8
    )
    for label in range(1, count):
        x, y, bw, bh, area = stats[label]
        touches_border = x == 0 or y == 0 or x + bw >= width or y + bh >= height
        spans_image = bw >= span_ratio * width or bh >= span_ratio * height
        # A hollow frame can sit fully inside the crop when the plate was
        # annotated loosely. Any component this large cannot be a character.
        huge = (
            bw >= 0.60 * width and bh >= 0.60 * height
        ) or (bw >= 0.85 * width and bh >= 0.45 * height)
        # Remaining inner frame line after the crop: very wide and thin.
        long_thin = bw >= 0.65 * width and bh <= 0.25 * height
        # A skewed frame can break into L-shaped pieces that no longer span
        # the image. They are large boxes with very little ink inside.
        density = area / max(1, bw * bh)
        sparse_border = (
            touches_border
            and (bw >= 0.20 * width or bh >= 0.20 * height)
            and density < 0.18
        )
        sparse_large = (
            bw * bh >= 0.02 * width * height
            and (bw >= 0.25 * width or bh >= 0.25 * height)
            and density < 0.15
        )
        if (
            (touches_border and spans_image)
            or huge
            or long_thin
            or sparse_border
            or sparse_large
        ):
            out[labels == label] = 0
    return out


def remove_border_frame(binary: np.ndarray) -> np.ndarray:
    """Remove plate borders/frames before line and character segmentation."""
    if binary is None or binary.size == 0:
        raise ValueError("binary image is empty")
    cleaned = _clear_edge_rows_and_columns(binary)
    return _remove_frame_components(cleaned)
