"""Plate proposals from edges, morphology, HSV color and contours."""

from dataclasses import dataclass

import cv2
import numpy as np

from .color_detection import color_masks
from .edge_detection import canny, sobel
from .preprocessing import enhance


def _has_plate_border(gray_roi: np.ndarray) -> bool:
    """Quick border check: dark rectangular outline around plate region."""
    if gray_roi.size < 400:
        return False
    # Blackhat highlights dark structures (border) on bright background
    blackhat = cv2.morphologyEx(gray_roi, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    _, th = cv2.threshold(blackhat, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = cv2.contourArea(cnt)
        if w > 15 and h > 10 and area / max(1, w * h) > 0.5:
            ratio = w / max(1, h)
            if 1.5 < ratio < 6 or 0.8 < ratio < 1.5:
                return True
    return False


@dataclass
class Candidate:
    bbox: tuple[int, int, int, int]
    corners: np.ndarray
    score: float
    source: str


def _proposal_masks(image: np.ndarray, gray: np.ndarray) -> dict[str, np.ndarray]:
    h, w = gray.shape
    scale = max(1, round(w / 640))
    masks = {}
    edges = canny(gray)
    masks["edges"] = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (13 * scale, 5 * scale)))
    blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_RECT, (19 * scale, 9 * scale)))
    grad = sobel(blackhat)
    _, grad = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    masks["characters"] = cv2.morphologyEx(grad, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (17 * scale, 7 * scale)))
    for name, mask in color_masks(image).items():
        clean = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (9 * scale, 9 * scale)))
        masks[name] = cv2.morphologyEx(clean, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return masks


def _iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return intersection / max(1, area_a + area_b - intersection)


def find_candidates(image: np.ndarray, max_candidates: int = 10) -> list[Candidate]:
    """Return ranked candidates; scores are heuristics, not probabilities."""
    if image is None or image.size == 0:
        raise ValueError("image is empty")
    original_h, original_w = image.shape[:2]
    if image.ndim != 3 or image.shape[2] != 3:
        raise ValueError("expected BGR image")
    resize_factor = min(1.0, 800 / max(original_w, original_h))
    work = cv2.resize(image, None, fx=resize_factor, fy=resize_factor) if resize_factor < 1 else image
    h, w = work.shape[:2]
    gray = enhance(work)
    evidence_edges = canny(gray)
    hsv_masks = color_masks(work)
    candidates = []
    for source, mask in _proposal_masks(work, gray).items():
        contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            x, y, bw, bh = cv2.boundingRect(contour)
            if bw < 18 or bh < 12:
                continue
            area_fraction = bw * bh / (w * h)
            ratio = bw / bh
            if not (0.0015 <= area_fraction <= 0.30 and (0.65 <= ratio <= 6.5 or (0.8 <= ratio <= 1.5))):
                continue
            rect_area = cv2.contourArea(contour) / (bw * bh)
            if rect_area < 0.20:
                continue
            x1 = max(0, x - round(bw * 0.04))
            y1 = max(0, y - round(bh * 0.04))
            x2 = min(w, x + bw + round(bw * 0.04))
            y2 = min(h, y + bh + round(bh * 0.04))
            roi_edges = evidence_edges[y1:y2, x1:x2]
            edge_density = cv2.countNonZero(roi_edges) / max(1, roi_edges.size)
            color_coverage = max(cv2.countNonZero(mask_[y1:y2, x1:x2]) / max(1, roi_edges.size) for mask_ in hsv_masks.values())
            if edge_density < 0.025 and color_coverage < 0.55:
                continue
            shape_score = max(np.exp(-abs(np.log(ratio / target)) / 0.75) for target in (1.0, 2.2, 4.0))
            edge_score = min(1.0, edge_density / 0.13)
            size_score = min(1.0, area_fraction / 0.10)
            color_score = min(1.0, color_coverage / 0.55)
            # Character density: minority-class fraction after Otsu on the ROI.
            # Plates mix dark glyphs with a light background (~0.15-0.40 minority);
            # solid regions (lights, plain panels) stay near zero.
            roi_gray = gray[y1:y2, x1:x2]
            _, roi_th = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            fg = cv2.countNonZero(roi_th)
            char_density = min(fg, roi_th.size - fg) / max(1, roi_th.size)
            char_score = min(1.0, char_density / 0.45)
            color_boost = 0.08 if source in ("white", "yellow", "blue") else 0.0
            # Border highlight (viền biển) — mới thêm cho WP1
            border_ok = _has_plate_border(gray[y1:y2, x1:x2])
            border_boost = 0.06 if border_ok else 0.0
            score = float(0.23 * shape_score + 0.18 * edge_score + 0.19 * size_score + 0.13 * color_score + 0.08 * min(1.0, rect_area / 0.7) + 0.10 * char_score + 0.05 * color_boost + border_boost)
            center_x = (x1 + x2) / (2 * w)
            center_y = (y1 + y2) / (2 * h)
            score += 0.06 * (1 - 2 * abs(center_x - 0.5))
            score += 0.06 * (1 - 2 * abs(center_y - 0.55))
            if x1 == 0 or y1 == 0 or x2 == w or y2 == h:
                score -= 0.08
            epsilon = 0.025 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            corners = approx.reshape(4, 2).astype(np.float32) if len(approx) == 4 else cv2.boxPoints(cv2.minAreaRect(contour))
            box = tuple(round(v / resize_factor) for v in (x1, y1, x2, y2))
            box = (max(0, box[0]), max(0, box[1]), min(original_w, box[2]), min(original_h, box[3]))
            candidates.append(Candidate(box, corners / resize_factor, score, source))
    candidates.sort(key=lambda item: item.score, reverse=True)
    unique = []
    for item in candidates:
        if all(_iou(item.bbox, other.bbox) < 0.65 for other in unique):
            unique.append(item)
            if len(unique) >= max_candidates:
                break
    return unique
