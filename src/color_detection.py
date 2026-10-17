"""HSV masks for common Vietnamese plate backgrounds."""

import cv2
import numpy as np


RANGES = {
    "white": [((0, 0, 155), (179, 85, 255))],
    "yellow": [((15, 70, 100), (40, 255, 255))],
    "blue": [((90, 45, 45), (135, 255, 255))],
    "red": [((0, 80, 70), (10, 255, 255)), ((165, 80, 70), (179, 255, 255))],
}


def color_masks(image: np.ndarray) -> dict[str, np.ndarray]:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    result = {}
    for name, ranges in RANGES.items():
        mask = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for low, high in ranges:
            mask |= cv2.inRange(hsv, np.array(low), np.array(high))
        result[name] = mask
    return result
