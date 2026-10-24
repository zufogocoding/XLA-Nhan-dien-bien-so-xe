"""Tests for WP2 character normalization and augmentation."""

import cv2
import numpy as np
import pytest

from src.augmentation import (
    add_noise,
    augment_character,
    augment_plate,
    brightness_contrast,
    gaussian_blur,
    motion_blur,
)
from src.fix_broken import CharBox
from src.normalize_character import (
    DEFAULT_SIZE,
    normalize_character,
    normalize_characters,
    normalize_histogram,
)


def _glyph_canvas(gray_value=180, height=40, width=20):
    gray = np.zeros((64, 64), dtype=np.uint8)
    binary = np.zeros((64, 64), dtype=np.uint8)
    top, left = 12, 22
    binary[top : top + height, left : left + width] = 255
    gray[top : top + height, left : left + width] = gray_value
    return gray, binary


def test_normalize_character_returns_centered_white_patch():
    gray, binary = _glyph_canvas()
    gray_patch, binary_patch = normalize_character(gray, binary)
    assert gray_patch.shape == (DEFAULT_SIZE, DEFAULT_SIZE)
    assert binary_patch.shape == (DEFAULT_SIZE, DEFAULT_SIZE)
    assert gray_patch.dtype == np.uint8
    assert set(np.unique(binary_patch)).issubset({0, 255})

    rows, columns = np.nonzero(binary_patch)
    assert rows.size > 0
    assert abs(rows.mean() - (DEFAULT_SIZE - 1) / 2) < 3
    assert abs(columns.mean() - (DEFAULT_SIZE - 1) / 2) < 3
    assert rows.max() - rows.min() + 1 == 22

    background = gray_patch[binary_patch == 0]
    assert background.max() == 0
    assert gray_patch[binary_patch > 0].mean() > 80


def test_normalize_handles_dark_glyphs_and_empty_masks():
    gray, binary = _glyph_canvas(gray_value=40)
    gray_patch, binary_patch = normalize_character(gray, binary)
    assert gray_patch[binary_patch > 0].mean() > 80

    empty = np.zeros((64, 64), dtype=np.uint8)
    gray_patch, binary_patch = normalize_character(empty, empty)
    assert gray_patch.shape == (DEFAULT_SIZE, DEFAULT_SIZE)
    assert cv2.countNonZero(binary_patch) == 0


def test_normalize_rejects_bad_shapes_and_sizes():
    gray, binary = _glyph_canvas()
    with pytest.raises(ValueError):
        normalize_character(gray, binary[:-1])
    with pytest.raises(ValueError):
        normalize_character(gray, binary, size=4)
    with pytest.raises(ValueError):
        normalize_character(gray, binary, margin=20)


def test_normalize_characters_maps_every_box():
    gray, binary = _glyph_canvas()
    boxes = [
        CharBox(22, 12, 20, 40),
        CharBox(22, 12, 20, 40),
    ]
    gray_patches, binary_patches = normalize_characters(gray, binary, boxes)
    assert len(gray_patches) == len(binary_patches) == 2
    assert all(patch.shape == (DEFAULT_SIZE, DEFAULT_SIZE) for patch in gray_patches)


def test_normalized_heights_are_consistent_across_digits():
    image = np.full((120, 520, 3), 238, dtype=np.uint8)
    cv2.putText(
        image,
        "0123456789",
        (20, 88),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.0,
        (20, 20, 20),
        5,
        cv2.LINE_AA,
    )
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    count, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    boxes = [
        CharBox(x, y, w, h)
        for x, y, w, h, area in stats[1:count]
        if area > 50 and h > 20
    ]
    assert len(boxes) == 10
    _, binary_patches = normalize_characters(gray, binary, boxes)
    heights = []
    for patch in binary_patches:
        rows = np.flatnonzero((patch > 0).any(axis=1))
        heights.append(int(rows[-1] - rows[0] + 1))
    median = float(np.median(heights))
    assert all(abs(height - median) <= 0.05 * median for height in heights)


def test_histogram_normalization_uses_glyph_contrast():
    values = np.full((20, 20), 100, dtype=np.uint8)
    values[5:15, 5:15] = np.tile(np.linspace(80, 160, 10), (10, 1)).astype(np.uint8)
    mask = np.zeros_like(values)
    mask[5:15, 5:15] = 255
    result = normalize_histogram(values, mask > 0)
    assert result[5:15, 5:15].max() == 255
    assert result[5:15, 5:15].min() == 0


def test_augmentation_keeps_shapes_and_dtype():
    image = np.full((120, 520, 3), 200, dtype=np.uint8)
    rng = np.random.default_rng(7)
    augmented = augment_plate(image, rng=rng)
    assert augmented.shape == image.shape
    assert augmented.dtype == np.uint8

    patch = np.zeros((32, 32), dtype=np.uint8)
    patch[8:24, 12:20] = 255
    assert augment_character(patch, rng=rng).shape == patch.shape
    for result in (
        gaussian_blur(image, 1.0),
        motion_blur(image, 5, 30),
        brightness_contrast(image, 10, 1.1),
        add_noise(image, 3, rng),
    ):
        assert result.shape == image.shape
        assert result.dtype == np.uint8
