"""Reproducible training-only character perturbations from the WP2 brief."""

import cv2
import numpy as np


def augment_character(
    image: np.ndarray, rng: np.random.Generator, *, rotation: float = 15,
    perspective: float = 0.1, blur: str = "gaussian", brightness: float = 0.3,
    contrast: float = 0.3,
) -> np.ndarray:
    if image.dtype != np.uint8 or image.ndim != 2 or image.size == 0:
        raise ValueError("expected nonempty uint8 grayscale character")
    if not (0 <= rotation <= 15 and 0 <= perspective <= 0.3 and 0 <= brightness <= 0.3 and 0 <= contrast <= 0.3):
        raise ValueError("augmentation range exceeds the WP2 brief")
    height, width = image.shape
    matrix = cv2.getRotationMatrix2D(((width - 1) / 2, (height - 1) / 2), float(rng.uniform(-rotation, rotation)), 1)
    result = cv2.warpAffine(image, matrix, (width, height), borderMode=cv2.BORDER_CONSTANT)
    points = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
    offsets = rng.uniform(-perspective, perspective, (4, 2)) * np.array([width, height])
    transform = cv2.getPerspectiveTransform(points, (points + offsets).astype(np.float32))
    result = cv2.warpPerspective(result, transform, (width, height))
    if blur == "gaussian":
        result = cv2.GaussianBlur(result, (3, 3), 0)
    elif blur == "motion":
        kernel = np.zeros((3, 3), np.float32)
        kernel[1, :] = 1 / 3
        result = cv2.filter2D(result, -1, kernel)
    elif blur != "none":
        raise ValueError("blur must be 'gaussian', 'motion' or 'none'")
    alpha = rng.uniform(1 - contrast, 1 + contrast)
    beta = rng.uniform(-brightness, brightness) * 255
    return np.clip(result.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)
