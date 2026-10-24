"""Tests for WP2 binarization and frame cleanup."""

import cv2
import numpy as np
import pytest

from src.binarization import (
    adaptive_binary,
    binarize,
    central_otsu_binary,
    enhance_gray,
    otsu_binary,
    remove_border_frame,
    to_gray,
)


def _plate(text="30A12345", background=(238, 238, 238), foreground=(20, 20, 20)):
    image = np.full((120, 520, 3), background, dtype=np.uint8)
    cv2.rectangle(image, (2, 2), (517, 117), foreground, 4)
    cv2.putText(
        image,
        text,
        (35, 88),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.0,
        foreground,
        5,
        cv2.LINE_AA,
    )
    return image


def test_to_gray_accepts_supported_layouts_and_rejects_bad_input():
    bgr = _plate()
    assert to_gray(bgr).shape == bgr.shape[:2]
    assert to_gray(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)).shape == bgr.shape[:2]
    rgba = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
    assert to_gray(rgba).shape == bgr.shape[:2]
    with pytest.raises(ValueError):
        to_gray(np.empty((0, 0), dtype=np.uint8))


def test_thresholds_put_glyphs_on_black_for_light_and_dark_plates():
    white_plate = _plate()
    blue_plate = _plate(background=(120, 48, 22), foreground=(245, 245, 245))
    for image in (white_plate, blue_plate):
        gray = to_gray(image)
        for method in (otsu_binary, adaptive_binary, central_otsu_binary):
            binary = method(gray)
            assert binary.shape == gray.shape
            assert binary.dtype == np.uint8
            assert set(np.unique(binary)).issubset({0, 255})
            assert 0 < cv2.countNonZero(binary) < binary.size


def test_enhance_and_binarize_return_enhanced_gray():
    image = _plate()
    gray = enhance_gray(to_gray(image))
    binary, enhanced = binarize(image, method="otsu")
    assert binary.shape == gray.shape
    assert enhanced.shape == gray.shape
    assert enhanced.dtype == np.uint8
    with pytest.raises(ValueError):
        binarize(image, method="unknown")


def test_remove_border_frame_deletes_outer_frame():
    binary = np.zeros((100, 300), dtype=np.uint8)
    cv2.rectangle(binary, (1, 1), (298, 98), 255, 4)
    cv2.putText(
        binary, "30A12345", (30, 70), cv2.FONT_HERSHEY_SIMPLEX, 1.5, 255, 4
    )
    cleaned = remove_border_frame(binary)
    assert cleaned.shape == binary.shape
    assert cv2.countNonZero(cleaned) < cv2.countNonZero(binary)
    assert cv2.countNonZero(cleaned[[0, -1], :]) == 0
    assert cv2.countNonZero(cleaned[:, [0, -1]]) == 0
    # Character strokes away from the frame must survive.
    assert cv2.countNonZero(cleaned[30:80, 40:260]) > 0


def test_remove_border_frame_rejects_empty_input():
    with pytest.raises(ValueError):
        remove_border_frame(np.empty((0, 0), dtype=np.uint8))
