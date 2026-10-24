"""kNN character artifact adapter."""

from pathlib import Path

from .character_classifier import CharacterClassifier


class KNNClassifier(CharacterClassifier):
    def __init__(self, model_path: str | Path | None = None):
        super().__init__(model_path or Path(__file__).resolve().parents[1] / "models/knn.pkl")
