"""Edge operators for inspection and detection."""

import cv2
import numpy as np


def canny(gray: np.ndarray, low: int = 80, high: int = 180) -> np.ndarray:
    return cv2.Canny(gray, low, high)


def sobel(gray: np.ndarray) -> np.ndarray:
    gradient = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    return cv2.convertScaleAbs(gradient)


def laplacian(gray: np.ndarray) -> np.ndarray:
    gradient = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
    return cv2.convertScaleAbs(gradient)
