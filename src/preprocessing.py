"""Image enhancement used by WP1."""

import cv2
import numpy as np


def grayscale(image: np.ndarray) -> np.ndarray:
    if image is None or image.size == 0:
        raise ValueError("image is empty")
    if image.ndim == 2:
        return image.copy()
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def enhance(image: np.ndarray, filter_type: str = "bilateral") -> np.ndarray:
    gray = grayscale(image)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    if filter_type == "gaussian":
        return cv2.GaussianBlur(gray, (5, 5), 0)
    if filter_type == "median":
        return cv2.medianBlur(gray, 5)
    if filter_type == "bilateral":
        return cv2.bilateralFilter(gray, 5, 35, 35)
    if filter_type == "none":
        return gray
    raise ValueError(f"unknown filter: {filter_type}")
