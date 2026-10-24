import joblib
import numpy as np
import pytest
from sklearn.neighbors import KNeighborsClassifier

from src.character_classifier import CharacterClassifier, extract_features
from src.pipeline_wp3 import recognize_characters


def test_saved_ocr_contract_and_sequence_order(tmp_path):
    vertical = np.zeros((32,32),np.uint8)
    horizontal = vertical.copy()
    vertical[3:29,14:18] = 255
    horizontal[14:18,3:29] = 255
    model = KNeighborsClassifier(n_neighbors=1).fit(np.stack([extract_features(image,"hog") for image in (vertical,horizontal)]),["1","2"])
    path=tmp_path / "ocr.pkl"
    joblib.dump({"task":"character_recognition","character_size":32,"feature":"hog","model":model},path)
    classifier=CharacterClassifier(path)
    result=recognize_characters([vertical,horizontal],classifier)
    assert result["raw_text"] == "12"
    assert result["confidences"] == [1.0,1.0]
    with pytest.raises(ValueError,match="32x32"):
        classifier.predict([np.zeros((28,28),np.uint8)])


def test_plate_background_model_cannot_be_used_as_ocr(tmp_path):
    path=tmp_path / "wp1.pkl"
    joblib.dump({"model":None,"win":(64,32)},path)
    with pytest.raises(ValueError,match="incompatible artifact"):
        CharacterClassifier(path).load()
