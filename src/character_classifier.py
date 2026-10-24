"""Shared artifact contract for supervised WP3 character classifiers."""

from pathlib import Path

import joblib
import numpy as np

from .feature_hog import hog_features
from .feature_lbp import lbp_features


class ModelNotReadyError(RuntimeError):
    """No trained OCR artifact is available; never substitute a fake prediction."""


def extract_features(character: np.ndarray, feature: str) -> np.ndarray:
    if feature == "hog":
        return hog_features(character)
    if feature == "lbp":
        return lbp_features(character)
    if feature == "hog_lbp":
        return np.concatenate([hog_features(character), lbp_features(character)])
    raise ValueError("feature must be 'hog', 'lbp' or 'hog_lbp'")


class CharacterClassifier:
    def __init__(self, model_path: str | Path):
        self.model_path = Path(model_path)
        self._bundle = None

    def load(self) -> dict:
        if self._bundle is None:
            if not self.model_path.is_file():
                raise ModelNotReadyError(f"OCR model is missing: {self.model_path}. Labeled character data and training are required.")
            bundle = joblib.load(self.model_path)
            if not isinstance(bundle, dict) or bundle.get("task") != "character_recognition" or bundle.get("character_size") != 32:
                raise ValueError("incompatible artifact: expected a WP3 32x32 character model")
            if bundle.get("feature") not in ("hog", "lbp", "hog_lbp") or not hasattr(bundle.get("model"), "predict_proba"):
                raise ValueError("artifact lacks its feature definition or probability classifier")
            self._bundle = bundle
        return self._bundle

    def predict(self, characters: list[np.ndarray]) -> list[dict]:
        bundle = self.load()
        if not characters:
            return []
        if any(char.shape != (32, 32) or char.dtype != np.uint8 for char in characters):
            raise ValueError("WP3 expects normalized 32x32 uint8 grayscale characters")
        matrix = np.stack([extract_features(char, bundle["feature"]) for char in characters])
        probabilities = bundle["model"].predict_proba(matrix)
        indices = probabilities.argmax(axis=1)
        return [
            {"char": str(bundle["model"].classes_[index]), "confidence": float(row[index])}
            for row, index in zip(probabilities, indices)
        ]
