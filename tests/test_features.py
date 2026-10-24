import numpy as np
import pytest

from src.feature_hog import hog_features
from src.feature_lbp import lbp_features
from src.character_classifier import CharacterClassifier, ModelNotReadyError


def test_feature_shapes_finite_values_and_uniform_patch_lbp():
    source = np.zeros((32, 32), np.uint8)
    assert hog_features(source).shape == (324,)
    assert np.isfinite(hog_features(source)).all()
    histogram = lbp_features(source)
    assert histogram.shape == (10,)
    assert histogram.sum() == 1
    assert histogram[8] == 1
    source[:, 15:17] = 255
    assert np.linalg.norm(hog_features(source)) > 0


def test_missing_ocr_artifact_is_reported_explicitly(tmp_path):
    with pytest.raises(ModelNotReadyError, match="Labeled character data"):
        CharacterClassifier(tmp_path / "absent.pkl").predict([np.zeros((32, 32), np.uint8)])
