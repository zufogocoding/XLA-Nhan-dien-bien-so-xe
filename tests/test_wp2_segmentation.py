"""Tests for WP2 line separation and character segmentation."""

import cv2
import numpy as np
import pytest

from src.binarization import binarize
from src.character_segmentation import connected_character_boxes, segment_text_line
from src.fix_broken import CharBox
from src.fix_touching import split_touching_box
from src.line_separation import detect_lines
from src.pipeline_wp2 import segment_plate, segment_plate_file


def _one_line(text="30A12345"):
    image = np.full((120, 520, 3), 238, dtype=np.uint8)
    cv2.rectangle(image, (2, 2), (517, 117), (20, 20, 20), 4)
    cv2.putText(
        image,
        text,
        (35, 88),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.0,
        (20, 20, 20),
        5,
        cv2.LINE_AA,
    )
    return image


def _two_line(top="30M", bottom="4253"):
    image = np.full((220, 360, 3), 238, dtype=np.uint8)
    cv2.rectangle(image, (2, 2), (357, 217), (20, 20, 20), 4)
    cv2.putText(
        image,
        top,
        (60, 85),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.0,
        (20, 20, 20),
        5,
        cv2.LINE_AA,
    )
    cv2.putText(
        image,
        bottom,
        (35, 185),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.0,
        (20, 20, 20),
        5,
        cv2.LINE_AA,
    )
    return image


def test_detect_lines_finds_one_and_two_line_layouts():
    one = binarize(_one_line())[0]
    two = binarize(_two_line())[0]
    assert detect_lines(one)[1] == "1_line"
    assert len(detect_lines(one)[0]) == 1
    regions, line_type = detect_lines(two)
    assert line_type == "2_line"
    assert len(regions) == 2
    assert regions[0].y2 <= regions[1].y1


def test_connected_components_and_segment_text_line():
    line = np.zeros((100, 320), dtype=np.uint8)
    for index, (x, width) in enumerate(((20, 25), (70, 25), (120, 25))):
        cv2.rectangle(line, (x, 20), (x + width, 80), 255, -1)
    boxes = connected_character_boxes(line)
    assert len(boxes) == 3
    segmented = segment_text_line(line)
    assert len(segmented) == 3
    assert all(box.w > 0 and box.h > 0 for box in segmented)
    with pytest.raises(ValueError):
        connected_character_boxes(np.empty((0, 0), dtype=np.uint8))


def test_frame_noise_is_removed_before_segmentation():
    line = np.zeros((110, 340), dtype=np.uint8)
    cv2.rectangle(line, (1, 1), (338, 108), 255, 3)
    for x in (40, 100, 160, 220):
        cv2.rectangle(line, (x, 30), (x + 28, 85), 255, -1)
    boxes = segment_text_line(line)
    assert len(boxes) == 4
    assert all(box.h >= 40 for box in boxes)


def test_split_touching_box_splits_a_thin_bridge():
    binary = np.zeros((80, 100), dtype=np.uint8)
    cv2.rectangle(binary, (8, 15), (30, 65), 255, -1)
    cv2.rectangle(binary, (55, 15), (77, 65), 255, -1)
    cv2.rectangle(binary, (30, 38), (55, 41), 255, -1)
    parts = split_touching_box(binary, CharBox(8, 15, 70, 51), 51, 20)
    assert len(parts) == 2
    assert parts[0].x < parts[1].x


def test_segment_plate_one_line_interface_and_order():
    result = segment_plate(_one_line())
    assert result["line_type"] == "1_line"
    assert result["num_chars"] == 8
    assert len(result["characters"]) == len(result["positions"]) == 8
    assert all(patch.shape == (32, 32) for patch in result["characters"])
    assert all(patch.shape == (32, 32) for patch in result["char_binary"])
    assert all(position[2] > 0 and position[3] > 0 for position in result["positions"])
    assert [position[0] for position in result["positions"]] == sorted(
        position[0] for position in result["positions"]
    )
    assert result["line_indices"] == [0] * 8
    assert result["binarization"] in {"otsu", "adaptive", "central"}


def test_segment_plate_two_line_interface_and_line_indices():
    result = segment_plate(_two_line())
    assert result["line_type"] == "2_line"
    assert result["num_chars"] == 7
    assert result["line_indices"] == [0, 0, 0, 1, 1, 1, 1]
    assert len(result["line_boxes"]) == 2
    for normalized in result["characters"]:
        assert normalized.shape == (32, 32)
        assert normalized.dtype == np.uint8
        assert normalized.max() > 0


def test_segment_plate_handles_blue_plate_and_empty_input(tmp_path):
    image = np.full((120, 520, 3), (120, 48, 22), dtype=np.uint8)
    cv2.rectangle(image, (2, 2), (517, 117), (245, 245, 245), 4)
    cv2.putText(
        image,
        "51F12345",
        (35, 88),
        cv2.FONT_HERSHEY_SIMPLEX,
        2.0,
        (245, 245, 245),
        5,
        cv2.LINE_AA,
    )
    result = segment_plate(image)
    assert result["num_chars"] == 8

    path = tmp_path / "plate.png"
    assert cv2.imwrite(str(path), image)
    assert segment_plate_file(path)["num_chars"] == 8

    with pytest.raises(ValueError):
        segment_plate(None)
    with pytest.raises(ValueError):
        segment_plate(np.empty((0, 0, 3), dtype=np.uint8))
