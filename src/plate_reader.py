"""Compare classical thresholding hypotheses with the existing HOG/SVM reader."""

import numpy as np

from .pipeline_wp2 import segment_plate_candidates, SegmentationConfig
from .sequence_builder import build_sequence


def rank_plate_candidates(image, classifier, config: SegmentationConfig | None = None, *, hypotheses=None):
    hypotheses=segment_plate_candidates(image,config) if hypotheses is None else hypotheses
    all_characters=[character for result in hypotheses for character in result['characters']]
    unique={character.tobytes():character for character in all_characters}
    predictions=classifier.predict(list(unique.values())) if unique else []
    lookup=dict(zip(unique,predictions))
    details=[lookup[character.tobytes()] for character in all_characters]
    offset=0
    for result in hypotheses:
        count=result['num_chars']
        predictions=details[offset:offset+count];offset+=count
        result['ocr']=build_sequence(predictions)
        confidence=result['ocr']['confidences']
        result['recognition_score']=float(np.mean(np.log(np.clip(confidence,1e-6,1)))+.04*min(count,9)-.3*max(0,count-9)-result['height_cv']-.4*result['edge_fragments']) if confidence else -10.
    return sorted(hypotheses,key=lambda result:result['recognition_score'],reverse=True)


def read_plate(image, classifier, config: SegmentationConfig | None = None):
    hypotheses=rank_plate_candidates(image,classifier,config)
    chosen=hypotheses[0]
    chosen['hypotheses']=[{'method':r['threshold_method'],'frame_cleanup':r['frame_cleanup'],'num_chars':r['num_chars'],'raw_text':r['ocr']['raw_text'],'score':r['recognition_score']} for r in hypotheses]
    return chosen
