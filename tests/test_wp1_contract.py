"""Protect the independent WP1 interface used by the original branch."""

import numpy as np

from src.detection import Candidate
from src.pipeline_wp1 import detect_plate_image
from src.character_segmentation import merge_vertical_fragments


def test_standalone_wp1_keeps_top_detector_proposal_without_wp2(monkeypatch):
    image = np.full((80, 160, 3), 230, np.uint8)
    corners = np.array([[10, 20], [140, 20], [140, 60], [10, 60]], np.float32)
    candidate = Candidate((10, 20, 141, 61), corners, .8, 'edges')
    monkeypatch.setattr('src.pipeline_wp1.find_candidates', lambda *_args, **_kwargs: [candidate])

    def forbidden(*_args, **_kwargs):
        raise AssertionError('standalone WP1 must not invoke segmentation or OCR')

    monkeypatch.setattr('src.pipeline_wp2.segment_plate_candidates', forbidden)
    monkeypatch.setattr('src.character_classifier.CharacterClassifier.load', forbidden)
    result = detect_plate_image(image)
    assert result['bbox'] == list(candidate.bbox)
    assert set(result) == {'bbox', 'plate_crop', 'plate_normalized', 'angle', 'confidence'}


def test_dense_fragment_repair_keeps_greedy_order_and_other_columns():
    # The first three fragments belong together. Dense, unrelated columns
    # trigger the optimized path and must retain their order and geometry.
    fragments = [(5, 0, 8, 7), (5, 10, 8, 7), (5, 20, 8, 7)]
    unrelated = [(50 + 20 * index, 2, 9, 12) for index in range(80)]
    assert merge_vertical_fragments(fragments + unrelated, 40) == [(5, 0, 8, 27)] + unrelated
