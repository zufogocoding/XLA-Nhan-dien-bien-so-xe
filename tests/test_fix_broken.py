import numpy as np
import pytest

from src.fix_broken import fix_broken


def test_vertical_closing_repairs_a_one_pixel_stroke_gap():
    binary = np.zeros((24, 24), np.uint8)
    binary[4:11, 10:13] = 255
    binary[12:20, 10:13] = 255
    repaired = fix_broken(binary, kernel_size=(1, 3))
    assert np.all(repaired[4:20, 10:13] == 255)
    assert not repaired[:, :8].any()
    assert binary[11, 11] == 0


def test_repair_rejects_unknown_method_and_invalid_kernel():
    binary = np.zeros((24, 24), np.uint8)
    with pytest.raises(ValueError):
        fix_broken(binary, kernel_size=(0, 3))
    with pytest.raises(ValueError):
        fix_broken(binary, kernel_size=(1, 3), method="unknown")
