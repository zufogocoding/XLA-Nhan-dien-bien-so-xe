"""SVM character artifact adapter (distinct from WP1 plate/background SVM)."""

from pathlib import Path

from .character_classifier import CharacterClassifier


class SVMClassifier(CharacterClassifier):
    def __init__(self, model_path: str | Path | None = None):
        super().__init__(model_path or Path(__file__).resolve().parents[1] / "models/svm_hog.pkl")
