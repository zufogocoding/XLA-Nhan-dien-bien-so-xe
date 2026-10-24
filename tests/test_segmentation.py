import cv2
import numpy as np
import pytest

from src.pipeline_wp2 import SegmentationConfig, segment_plate
from src.fix_touching import split_touching


@pytest.mark.parametrize("method", ["components", "contours", "projection"])
def test_two_line_plate_frame_noise_and_reading_order(method):
    image = np.full((110, 230, 3), 245, np.uint8)
    cv2.rectangle(image, (1, 1), (228, 108), (0, 0, 0), 2)
    for top, xs in [(14, [35, 70, 105, 140]), (65, [20, 55, 90, 125, 160])]:
        for x in xs:
            image[top:top + 30, x:x + 15] = 0
    image[53:55, 110:112] = 0
    result = segment_plate(image, SegmentationConfig(segmentation_method=method))
    assert result["num_chars"] == 9
    assert result["line_type"] == "2_line"
    assert result["line_ids"] == [0] * 4 + [1] * 5
    assert all(char.shape == (32, 32) for char in result["characters"])
    assert [b[0] for b in result["positions"][:4]] == [35, 70, 105, 140]


def test_projection_can_split_a_thin_bridge_between_glyphs():
    binary = np.zeros((32, 40), np.uint8)
    binary[:, :17] = 255
    binary[:, 23:] = 255
    binary[16, :] = 255
    pieces = split_touching(binary)
    assert len(pieces) == 2
    assert pieces[0][0] == 0
    assert pieces[-1][0] + pieces[-1][2] == 40


def test_blank_plate_does_not_invent_characters():
    result = segment_plate(np.full((80, 200), 255, np.uint8))
    assert result["num_chars"] == 0
    assert result["line_type"] is None


def test_dark_surroundings_do_not_reverse_character_polarity():
    image = np.zeros((120,240,3),np.uint8)
    image[20:100,30:210] = 240
    for x in (45,80,115,150,185):
        image[40:80,x:x+10] = 0
    # More dark pixels than light pixels in the complete crop.
    assert np.count_nonzero(image[:,:,0] == 0) > image.shape[0]*image.shape[1]/2
    result = segment_plate(image)
    assert result["num_chars"] == 5
    assert result["foreground_inverted"] is True


def test_tilted_rows_keep_whole_glyphs_when_row_extents_overlap():
    image=np.full((120,200,3),245,np.uint8)
    for index,x in enumerate((20,50,80,110)):
        top=10+index*6
        image[top:top+30,x:x+13]=0
    for index,x in enumerate((20,50,80,110,140)):
        top=50+index*6
        image[top:top+30,x:x+13]=0
    result=segment_plate(image)
    assert result["line_type"]=='2_line'
    assert result["num_chars"]==9
    assert result["line_ids"]==[0]*4+[1]*5
    assert result["line_method"]=='component_centers'
