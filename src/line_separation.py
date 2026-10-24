"""Line separation for one-line and two-line Vietnamese plates.

Primary method: horizontal projection profile. A two-line plate leaves a
low-ink horizontal band between the lines. If a residual skew smears that
band, the fallback clusters connected components by their vertical centers.
"""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class LineRegion:
    """Vertical extent of one text line inside the plate image."""

    y1: int
    y2: int
    index: int

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    def to_bbox(self, width: int) -> tuple[int, int, int, int]:
        return 0, self.y1, width, self.height


def horizontal_projection(binary: np.ndarray) -> np.ndarray:
    """Count foreground pixels per row."""
    return (binary > 0).sum(axis=1).astype(np.float32)


def _smooth(profile: np.ndarray, window: int) -> np.ndarray:
    window = max(1, window | 1)
    if window <= 1:
        return profile
    return np.convolve(profile, np.ones(window, dtype=np.float32) / window, mode="same")


def _active_span(profile: np.ndarray, threshold: float) -> tuple[int, int] | None:
    rows = np.flatnonzero(profile > threshold)
    if rows.size == 0:
        return None
    return int(rows[0]), int(rows[-1]) + 1


def _trim_region(profile: np.ndarray, y1: int, y2: int, threshold: float) -> tuple[int, int]:
    span = _active_span(profile[y1:y2], threshold)
    if span is None:
        return y1, y2
    return y1 + span[0], y1 + span[1]


def _find_valley(profile: np.ndarray, height: int, width: int) -> int | None:
    """Return a split row between two lines, or None for a one-line plate."""
    if height < 24:
        return None
    smooth = _smooth(profile, max(3, height // 50))
    low = int(height * 0.20)
    high = int(height * 0.80)
    if high - low < 4:
        return None

    band = smooth[low:high]
    split = low + int(np.argmin(band))
    positive = smooth[smooth > 0]
    if positive.size == 0:
        return None
    peak = float(np.percentile(positive, 90))
    valley = float(smooth[split])
    # A real line gap is both small relative to text rows and narrow relative
    # to the plate width. The second term tolerates a few pixels of skew.
    if peak <= 0 or valley > min(0.22 * peak, 0.12 * width):
        return None

    total = float(profile.sum())
    if total <= 0:
        return None
    if profile[:split].sum() < 0.08 * total or profile[split:].sum() < 0.08 * total:
        return None
    if split < 0.14 * height or split > 0.86 * height:
        return None
    return split


def _component_centers(binary: np.ndarray) -> list[float]:
    height, width = binary.shape[:2]
    count, _, stats, centroids = cv2.connectedComponentsWithStats(
        (binary > 0).astype(np.uint8), connectivity=8
    )
    centers = []
    for label in range(1, count):
        x, y, bw, bh, area = stats[label]
        if area < max(20, binary.size * 0.0015):
            continue
        if bh < max(5, height * 0.18) or bh > height * 0.95:
            continue
        if bw < max(3, width * 0.025) or bw > width * 0.80:
            continue
        centers.append(float(centroids[label][1]))
    return sorted(centers)


def _cluster_split_row(binary: np.ndarray) -> int | None:
    """Find a two-line split from component centers when projection fails."""
    height = binary.shape[0]
    centers = np.asarray(_component_centers(binary), dtype=np.float32)
    if centers.size < 4:
        return None
    gaps = np.diff(centers)
    index = int(np.argmax(gaps))
    gap = float(gaps[index])
    upper = centers[: index + 1]
    lower = centers[index + 1 :]
    if gap < height * 0.16 or upper.size < 2 or lower.size < 2:
        return None
    if lower.mean() - upper.mean() < height * 0.28:
        return None
    split = int(round((upper.max() + lower.min()) / 2))
    if split <= height * 0.15 or split >= height * 0.85:
        return None
    return split


def detect_lines(
    binary: np.ndarray, min_line_height_ratio: float = 0.18
) -> tuple[list[LineRegion], str]:
    """Return line regions in reading order and ``"1_line"``/``"2_line"``."""
    if binary is None or binary.size == 0:
        raise ValueError("binary image is empty")
    if binary.ndim != 2:
        raise ValueError("binary image must be single-channel")
    height, width = binary.shape[:2]
    profile = horizontal_projection(binary)
    threshold = max(1.0, width * 0.005)
    span = _active_span(profile, threshold)
    if span is None:
        return [], "1_line"

    # A properly normalized two-line Vietnamese plate is close to square.
    # Wide crops with a skewed one-line plate must not be split by a smeared
    # projection valley.
    split = None
    if width / max(1, height) < 2.25:
        split = _find_valley(profile, height, width)
        if split is None:
            split = _cluster_split_row(binary)

    if split is not None:
        top = _trim_region(profile, 0, split, threshold)
        bottom = _trim_region(profile, split, height, threshold)
        top_ok = top[1] - top[0] >= min_line_height_ratio * height
        bottom_ok = bottom[1] - bottom[0] >= min_line_height_ratio * height
        if top_ok and bottom_ok and top[1] <= bottom[0]:
            return [
                LineRegion(top[0], top[1], 0),
                LineRegion(bottom[0], bottom[1], 1),
            ], "2_line"
        if bottom_ok and not top_ok:
            return [LineRegion(bottom[0], bottom[1], 0)], "1_line"
        if top_ok and not bottom_ok:
            return [LineRegion(top[0], top[1], 0)], "1_line"

    y1, y2 = _trim_region(profile, span[0], span[1], threshold)
    return [LineRegion(y1, y2, 0)], "1_line"
