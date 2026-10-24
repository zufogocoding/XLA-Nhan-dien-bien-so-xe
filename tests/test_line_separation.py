import numpy as np

from src.line_separation import separate_lines


def test_two_rows_are_returned_in_reading_order():
    binary = np.zeros((100, 200), np.uint8)
    for x in (20, 50, 80, 110):
        binary[10:40, x:x + 15] = 255
        binary[60:90, x:x + 15] = 255
    assert separate_lines(binary) == [(10, 40), (60, 90)]


def test_single_row_and_empty_plate():
    binary = np.zeros((50, 200), np.uint8)
    assert separate_lines(binary) == []
    binary[10:40, 20:35] = 255
    binary[10:40, 60:75] = 255
    assert separate_lines(binary) == [(10, 40)]
