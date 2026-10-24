"""Regression coverage for the optional WP1 model loader."""

import numpy as np

from src import reclassifier


def test_missing_joblib_keeps_heuristic_detector_available(monkeypatch):
    monkeypatch.setattr(reclassifier, "joblib", None)
    monkeypatch.setattr(reclassifier, "_LOADED", False)
    monkeypatch.setattr(reclassifier, "_MODEL", None)
    assert reclassifier.svm_probability(np.zeros((32, 64, 3), dtype=np.uint8)) is None


def test_explicit_disable_does_not_load_saved_model(monkeypatch):
    monkeypatch.setenv("WP1_DISABLE_SVM", "1")
    monkeypatch.setattr(reclassifier, "_LOADED", False)
    assert reclassifier._load() is None
    assert reclassifier._LOADED is False
