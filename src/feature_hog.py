"""Character HOG at 32x32; the WP1 crop descriptor remains unchanged."""

import cv2
import numpy as np

from .hog import _gradients


def hog_features(character: np.ndarray) -> np.ndarray:
    if character.ndim != 2 or character.size == 0 or character.dtype != np.uint8:
        raise ValueError("expected a nonempty uint8 grayscale character")
    gray = cv2.resize(character, (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    magnitude, angle = _gradients(gray)
    histograms = np.zeros((4, 4, 9), np.float32)
    for row in range(4):
        for col in range(4):
            magnitudes = magnitude[row * 8:(row + 1) * 8, col * 8:(col + 1) * 8].ravel()
            bins = angle[row * 8:(row + 1) * 8, col * 8:(col + 1) * 8].ravel() / 20
            indices = np.floor(bins).astype(np.int32) % 9
            fraction = bins - np.floor(bins)
            np.add.at(histograms[row, col], indices, magnitudes * (1 - fraction))
            np.add.at(histograms[row, col], (indices + 1) % 9, magnitudes * fraction)
    blocks = []
    for row in range(3):
        for col in range(3):
            block = histograms[row:row + 2, col:col + 2].ravel().copy()
            block /= np.sqrt(np.dot(block, block) + 1e-10)
            block = np.minimum(block, 0.2)
            block /= np.sqrt(np.dot(block, block) + 1e-10)
            blocks.append(block)
    return np.concatenate(blocks).astype(np.float32)
