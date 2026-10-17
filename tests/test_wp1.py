import cv2
import numpy as np
import pytest

from src.color_detection import color_masks
from src.detection import _iou, find_candidates
from src.pipeline_wp1 import detect_plate
from src.preprocessing import enhance, grayscale
from src.warp import order_points, warp_plate


def test_preprocessing_handles_valid_and_empty_images():
    image = np.full((80, 120, 3), 180, dtype=np.uint8)
    assert grayscale(image).shape == (80, 120)
    for filter_type in ("gaussian", "median", "bilateral", "none"):
        assert enhance(image, filter_type).shape == (80, 120)
    with pytest.raises(ValueError):
        grayscale(np.empty((0, 0), dtype=np.uint8))


def test_color_and_warp_geometry():
    image = np.full((80, 160, 3), 255, dtype=np.uint8)
    assert cv2.countNonZero(color_masks(image)["white"]) == 80 * 160
    corners = np.array([[150, 70], [10, 10], [10, 70], [150, 10]], dtype=np.float32)
    ordered = order_points(corners)
    assert np.array_equal(ordered[0], [10, 10])
    assert warp_plate(image, corners).shape[:2] == (60, 140)


def test_detection_synthetic_plate_and_interface(tmp_path):
    image = np.full((400, 600, 3), 65, dtype=np.uint8)
    cv2.rectangle(image, (185, 150), (405, 250), (245, 245, 245), -1)
    cv2.rectangle(image, (185, 150), (405, 250), (20, 20, 20), 3)
    cv2.putText(image, "59X1", (205, 218), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 4)
    candidates = find_candidates(image)
    assert candidates
    assert max(_iou(candidate.bbox, (185, 150, 405, 250)) for candidate in candidates) > 0.5
    path = tmp_path / "input.png"
    cv2.imwrite(str(path), image)
    result = detect_plate(path)
    assert result is not None
    assert result["plate_crop"].size > 0
    assert result["plate_normalized"].size > 0
    assert len(result["bbox"]) == 4
