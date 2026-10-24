import numpy as np

from src.normalize_character import normalize_character
from src.augmentation import augment_character


def test_normalization_preserves_aspect_centers_and_padding():
    source = np.zeros((60, 30), np.uint8)
    source[5:55, 10:20] = 255
    result = normalize_character(source)
    ys, xs = np.nonzero(result)
    assert result.shape == (32, 32)
    assert ys.max() - ys.min() + 1 == 28
    assert xs.max() - xs.min() + 1 == 6
    assert abs(xs.mean() - 15.5) <= 0.5
    assert abs(ys.mean() - 15.5) <= 0.5


def test_augmentation_is_seeded_and_keeps_shape_range():
    source = np.zeros((32, 32), np.uint8)
    source[5:27, 12:20] = 255
    first = augment_character(source, np.random.default_rng(12), blur="motion")
    second = augment_character(source, np.random.default_rng(12), blur="motion")
    assert np.array_equal(first, second)
    assert first.shape == source.shape and first.dtype == np.uint8
    assert not np.array_equal(first, source)
