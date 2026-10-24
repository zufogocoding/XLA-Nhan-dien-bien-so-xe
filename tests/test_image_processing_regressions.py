import cv2
import numpy as np

from src.character_segmentation import merge_vertical_fragments
from src.pipeline_wp2 import SegmentationConfig, segment_plate
from src.pipeline_wp4 import postprocess
from src.text_regions import text_regions
from src.detection import _iou


def test_tall_side_fragment_does_not_make_bottom_characters_too_short():
    image=np.full((120,240,3),245,np.uint8)
    for y,xs in ((12,(35,70,105)),(70,(20,55,90,125,160))):
        for x in xs:
            image[y:y+30,x:x+15]=0
    image[20:105,213:228]=0
    result=segment_plate(image)
    assert result['num_chars']==8
    assert result['line_ids']==[0]*3+[1]*5


def test_frame_stroke_cleanup_retains_attached_characters():
    image=np.full((110,250,3),245,np.uint8)
    cv2.rectangle(image,(1,1),(248,108),(0,0,0),2)
    for x in (40,100,160):
        image[25:85,x:x+25]=0
    image[2:26,49:51]=0
    result=segment_plate(image,SegmentationConfig(threshold_method='otsu',frame_cleanup=True))
    assert result['num_chars']==3


def test_vertical_repair_rejoins_parts_without_merging_next_character():
    result=merge_vertical_fragments([(10,5,10,10),(10,18,10,12),(32,5,15,25)],35)
    assert sorted(result)==[(10,5,10,25),(32,5,15,25)]


def test_large_character_row_proposes_plate_without_closed_vehicle_contour():
    image=np.full((480,800,3),120,np.uint8)
    cv2.rectangle(image,(80,285),(720,400),(235,235,235),-1)
    cv2.putText(image,'24B63825',(115,370),cv2.FONT_HERSHEY_SIMPLEX,2.2,(15,15,15),5)
    proposals=text_regions(image)
    text_width,text_height=cv2.getTextSize('24B63825',cv2.FONT_HERSHEY_SIMPLEX,2.2,5)[0]
    assert any(_iou(c.bbox,(115,370-text_height,115+text_width,370))>.6 for c in proposals)


def test_two_letter_motorcycle_series_are_preserved_during_confusion_fix():
    for raw in ('29AC88688','29AA12345'):
        result=postprocess(raw,[.95]*len(raw))
        assert result['is_valid']
        assert result['corrected_text']==raw
        assert result['vehicle_type']=='motorcycle'
        assert result['corrections']==[]
