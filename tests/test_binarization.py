import cv2
import numpy as np
import pytest

from src.binarization import binarize


@pytest.mark.parametrize("method", ["otsu", "adaptive"])
def test_dark_text_has_white_foreground(method):
    image = np.full((60, 120, 3), 240, np.uint8)
    cv2.rectangle(image, (40, 10), (55, 49), (10, 10, 10), -1)
    binary = binarize(image, method)
    assert binary[0, 0] == 0
    assert binary[10, 40] == 255
    assert set(np.unique(binary)) == {0, 255}


def test_polarity_for_light_text_on_dark_plate():
    image = np.zeros((60, 120), np.uint8)
    image[10:50, 40:55] = 230
    assert np.array_equal(binarize(image) > 0, image > 0)


def test_invalid_input_and_threshold_arguments():
    with pytest.raises(ValueError):
        binarize(np.empty((0, 0), np.uint8))
    with pytest.raises(ValueError):
        binarize(np.zeros((5, 5), np.float32))
    with pytest.raises(ValueError):
        binarize(np.zeros((10, 10), np.uint8), "adaptive", block_size=4)
