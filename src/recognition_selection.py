"""Application-level plate selection using WP1 proposals and WP2-WP4 evidence.

This intentionally does more work than standalone WP1. Keep it explicit so
WP1 users and benchmarks do not silently invoke segmentation or OCR.
"""

import numpy as np

from .detection import find_candidates
from .pipeline_wp1 import _normalize
from .pipeline_wp2 import segment_plate_candidates
from .pipeline_wp4 import postprocess
from .plate_reader import rank_plate_candidates
from .text_regions import text_regions


def select_plate_for_recognition(image: np.ndarray, classifier) -> dict | None:
    if classifier is None:
        raise ValueError('recognition-assisted selection requires an OCR classifier')
    candidates = find_candidates(image, max_candidates=6) + text_regions(image)
    if not candidates:
        return None
    prepared = []
    for candidate in candidates:
        x1, y1, x2, y2 = candidate.bbox
        crop = image[y1:y2, x1:x2].copy()
        normalized, angle = _normalize(crop, candidate.corners - np.array([x1, y1], np.float32))
        hypotheses = segment_plate_candidates(normalized)
        segmentation = max(hypotheses, key=lambda result: result['segmentation_score'])
        prepared.append({
            'candidate': candidate, 'plate_crop': crop, 'plate_normalized': normalized,
            'angle': angle, 'hypotheses': hypotheses, 'segmentation': segmentation,
            'selection_score': segmentation['segmentation_score'] + .1 * candidate.score,
        })
    prepared.sort(key=lambda item: item['selection_score'], reverse=True)
    for item in prepared[:5]:
        ranked = rank_plate_candidates(item['plate_normalized'], classifier, hypotheses=item['hypotheses'])
        segmentation = ranked[0]
        ocr = segmentation['ocr']
        valid = postprocess(ocr['raw_text'], ocr['confidences'])['is_valid']
        item['segmentation'] = segmentation
        item['ocr'] = ocr
        item['selection_score'] = segmentation['recognition_score'] + .5 * valid + .05 * item['candidate'].score
    prepared = prepared[:5]
    chosen = max(prepared, key=lambda item: item['selection_score'])
    return {
        'plate_crop': chosen['plate_crop'], 'plate_normalized': chosen['plate_normalized'],
        'bbox': list(chosen['candidate'].bbox), 'angle': chosen['angle'],
        'confidence': min(1., chosen['candidate'].score),
        'source': chosen['candidate'].source, 'segmentation': chosen['segmentation'],
        'ocr': chosen['ocr'],
        'candidate_diagnostics': [
            {'bbox': list(item['candidate'].bbox), 'source': item['candidate'].source,
             'score': float(item['selection_score']), 'num_chars': item['segmentation']['num_chars'],
             'raw_text': item['ocr']['raw_text']}
            for item in prepared
        ],
    }
