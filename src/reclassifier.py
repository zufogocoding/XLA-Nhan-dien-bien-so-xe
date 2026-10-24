"""Optional HOG+SVM re-ranker for WP1 candidates.

Loaded lazily from models/wp1_svm.pkl. If the model file is missing, every
function degrades to "no opinion" so the heuristic detector keeps working.
"""
from pathlib import Path

import numpy as np

try:
    import joblib
except ImportError:
    joblib = None

from .hog import hog_features, crop_features

_MODEL = None
_LOADED = False
_MODEL_PATHS = (Path("models/wp1_svm.pkl"), Path("models/wp1_svm.joblib"))


import os as _os

def _load():
    global _MODEL, _LOADED
    if _os.environ.get('WP1_DISABLE_SVM') or joblib is None:
        return None
    if _LOADED:
        return _MODEL
    _LOADED = True
    for p in _MODEL_PATHS:
        if p.exists():
            try:
                bundle = joblib.load(p)
                _MODEL = bundle["model"]
            except Exception:
                _MODEL = None
            break
    # also try absolute path relative to this file's repo root
    if _MODEL is None:
        repo = Path(__file__).resolve().parents[1]
        for rel in ("models/wp1_svm.pkl", "models/wp1_svm.joblib"):
            p = repo / rel
            if p.exists():
                try:
                    bundle = joblib.load(p)
                    _MODEL = bundle["model"]
                except Exception:
                    _MODEL = None
                break
    return _MODEL


def svm_probability(crop: np.ndarray) -> float | None:
    """Return P(plate) in [0,1] for a BGR crop, or None if no model."""
    model = _load()
    if model is None or crop is None or crop.size == 0:
        return None
    try:
        feat = np.concatenate([hog_features(crop), crop_features(crop)]).reshape(1, -1)
        proba = model.predict_proba(feat)[0]
        # class 1 = plate
        classes = list(model.classes_)
        idx = classes.index(1) if 1 in classes else -1
        return float(proba[idx]) if idx >= 0 else float(proba[-1])
    except Exception:
        try:
            feat = np.concatenate([hog_features(crop), crop_features(crop)]).reshape(1, -1)
            val = model.decision_function(feat)[0]
            return float(1.0 / (1.0 + np.exp(-val)))
        except Exception:
            return None
