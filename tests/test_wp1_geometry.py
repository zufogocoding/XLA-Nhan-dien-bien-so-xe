import cv2
import numpy as np
import pytest

from src.deskew import deskew_plate
from src.edge_detection import canny, laplacian, sobel


def test_edge_operators_find_a_vertical_intensity_step():
    gray = np.zeros((48, 64), np.uint8)
    gray[:, 32:] = 255
    for operator in (canny, sobel, laplacian):
        edges = operator(gray)
        assert edges.shape == gray.shape
        assert edges.dtype == np.uint8
        assert cv2.countNonZero(edges[:, 28:36]) > 0
        assert cv2.countNonZero(edges[:, :20]) == 0


@pytest.mark.parametrize("rotation", [-25, 13, 35])
def test_deskew_makes_a_rotated_plate_horizontal(rotation):
    image = np.zeros((140, 220, 3), np.uint8)
    corners = cv2.boxPoints(((110, 70), (140, 50), rotation))
    cv2.fillConvexPoly(image, corners.astype(np.int32), (255, 255, 255))
    corrected, angle = deskew_plate(image, corners.reshape(-1, 1, 2))
    assert abs(angle - rotation) < 0.1
    _, binary = cv2.threshold(cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY), 127, 255, cv2.THRESH_BINARY)
    ys, xs = np.nonzero(binary)
    _, vectors = np.linalg.eigh(np.cov(np.column_stack([xs, ys]), rowvar=False))
    principal = vectors[:, -1]
    assert abs(principal[1] / principal[0]) < np.tan(np.deg2rad(1))
    assert corrected.shape == image.shape
