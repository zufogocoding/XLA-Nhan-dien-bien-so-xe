"""WP3 public interface for supervised OCR on ordered WP2 characters."""

import numpy as np

from .character_classifier import CharacterClassifier
from .classifier_svm import SVMClassifier
from .sequence_builder import build_sequence


def recognize_characters(characters: list[np.ndarray], classifier: CharacterClassifier | None = None) -> dict:
    classifier = classifier or SVMClassifier()
    return build_sequence(classifier.predict(characters))
