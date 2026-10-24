import numpy as np

from src.pipeline_wp2 import SegmentationConfig,segment_plate


def test_working_scale_keeps_output_positions_in_original_coordinates():
    source=np.full((160,400,3),240,np.uint8)
    source[50:110,80:100]=0
    result=segment_plate(source,SegmentationConfig(working_height=128))
    assert result['num_chars']==1
    x,y,width,height=result['positions'][0]
    assert abs(x-80)<=1 and abs(y-50)<=1
    assert abs(width-20)<=2 and abs(height-60)<=2
    assert result['binary'].shape==(160,400)
    assert result['characters'][0].shape==(32,32)
