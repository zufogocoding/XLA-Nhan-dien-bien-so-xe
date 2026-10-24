"""Uniform P=8, R=1 local binary patterns with a normalized 10-bin histogram."""

import numpy as np


def lbp_features(character: np.ndarray) -> np.ndarray:
    if character.ndim != 2 or min(character.shape) < 3 or character.dtype != np.uint8:
        raise ValueError("expected a uint8 grayscale character at least 3x3")
    center = character[1:-1, 1:-1]
    # Eight nearest neighbors around the radius-one 3x3 neighborhood.
    neighbors = [
        character[:-2, 1:-1], character[:-2, 2:], character[1:-1, 2:],
        character[2:, 2:], character[2:, 1:-1], character[2:, :-2],
        character[1:-1, :-2], character[:-2, :-2],
    ]
    bits = np.stack([neighbor >= center for neighbor in neighbors])
    transitions = np.count_nonzero(bits != np.roll(bits, 1, axis=0), axis=0)
    codes = np.where(transitions <= 2, bits.sum(axis=0), 9)
    histogram = np.bincount(codes.ravel(), minlength=10).astype(np.float32)
    return histogram / histogram.sum()
