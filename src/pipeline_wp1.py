"""WP1 interface: image path -> detected and normalized plate."""

from pathlib import Path

import cv2
import numpy as np

from .detection import find_candidates
from .deskew import deskew_plate
from .warp import order_points, warp_plate


def detect_plate(image_path: str | Path) -> dict | None:
    """Return the strongest detection, or None when no plate candidate exists.

    Confidence is a heuristic ranking score, not a calibrated probability.
    """
    path = Path(image_path)
    image = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"cannot read image: {path}")
    candidates = find_candidates(image, max_candidates=3)
    if not candidates:
        return None
    # Pick best; could extend to return top-3 for WP2
    chosen = candidates[0]
    x1, y1, x2, y2 = chosen.bbox
    crop = image[y1:y2, x1:x2].copy()
    local_corners = chosen.corners - np.array([x1, y1], dtype=np.float32)
    normalized, angle = _normalize(crop, local_corners)
    return {
        "plate_crop": crop,
        "plate_normalized": normalized,
        "bbox": [x1, y1, x2, y2],
        "angle": angle,
        "confidence": min(1.0, chosen.score),
    }


def _normalize(crop: np.ndarray, local_corners: np.ndarray) -> tuple[np.ndarray, float]:
    """Perspective-warp when corners are reliable; otherwise fall back to deskew."""
    corner_area = cv2.contourArea(local_corners.astype(np.float32))
    can_warp = corner_area >= 0.60 * crop.shape[0] * crop.shape[1]
    if can_warp:
        try:
            warped = warp_plate(crop, local_corners)
            if warped.shape[0] >= 12 and warped.shape[1] >= 18 and 0.45 < warped.shape[1] / warped.shape[0] < 7:
                ordered = order_points(local_corners)
                top = ordered[1] - ordered[0]
                raw_angle = float(np.degrees(np.arctan2(top[1], top[0])))
                angle = (raw_angle + 90) % 180 - 90
                return warped, angle
        except (ValueError, cv2.error):
            pass
    contour = local_corners.astype(np.int32).reshape(-1, 1, 2)
    return deskew_plate(crop, contour)
