"""WP2 thresholding with white character foreground on a black background."""

import cv2
import numpy as np

from .preprocessing import grayscale


def binarize(
    image: np.ndarray,
    method: str = "otsu",
    *,
    invert: bool | None = None,
    block_size: int = 11,
    c: float = 2,
) -> np.ndarray:
    """Threshold a uint8 BGR/gray plate; infer foreground polarity if omitted.

    ``invert`` refers to the normal THRESH_BINARY result. Auto polarity treats
    the majority pixel class as background, supporting light and dark plates.
    """
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8:
        raise ValueError("image must be a uint8 numpy array")
    gray = grayscale(image)
    if method == "otsu":
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif method == "adaptive":
        if block_size < 3 or block_size % 2 == 0:
            raise ValueError("block_size must be an odd integer >= 3")
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block_size, c,
        )
    else:
        raise ValueError("method must be 'otsu' or 'adaptive'")
    if invert is None:
        invert = cv2.countNonZero(binary) > binary.size / 2
    return cv2.bitwise_not(binary) if invert else binary


def validate_binary(binary: np.ndarray) -> None:
    """Reject invalid masks instead of silently changing their polarity."""
    if (
        not isinstance(binary, np.ndarray) or binary.dtype != np.uint8
        or binary.ndim != 2 or binary.size == 0
    ):
        raise ValueError("binary must be a nonempty uint8 2-D array")
    if not np.isin(binary, (0, 255)).all():
        raise ValueError("binary mask must contain only 0 and 255")
