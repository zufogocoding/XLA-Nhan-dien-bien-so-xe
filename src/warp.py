"""Perspective correction for a detected quadrilateral."""

import cv2
import numpy as np


def order_points(points: np.ndarray) -> np.ndarray:
    points = np.asarray(points, dtype=np.float32).reshape(4, 2)
    ordered = np.empty((4, 2), dtype=np.float32)
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1).ravel()
    ordered[0] = points[np.argmin(sums)]
    ordered[2] = points[np.argmax(sums)]
    ordered[1] = points[np.argmin(diffs)]
    ordered[3] = points[np.argmax(diffs)]
    if len({tuple(p) for p in ordered}) != 4:
        raise ValueError("quadrilateral has ambiguous corners")
    return ordered


def warp_plate(image: np.ndarray, corners: np.ndarray) -> np.ndarray:
    tl, tr, br, bl = order_points(corners)
    width = max(1, round(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl))))
    height = max(1, round(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl))))
    target = np.array([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(np.array([tl, tr, br, bl]), target)
    return cv2.warpPerspective(image, matrix, (width, height))
