"""Rotation correction with a robust minAreaRect angle convention."""

import cv2
import numpy as np


def deskew_plate(image: np.ndarray, contour: np.ndarray) -> tuple[np.ndarray, float]:
    (_, _), (width, height), raw_angle = cv2.minAreaRect(contour)
    angle = raw_angle if width >= height else raw_angle - 90
    if angle > 45:
        angle -= 90
    if angle < -45:
        angle += 90
    h, w = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE), float(angle)
