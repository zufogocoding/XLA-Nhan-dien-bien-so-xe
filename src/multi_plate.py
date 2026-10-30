"""Detect and read several license plates in one image.

The public WP1 contract stays single-plate on purpose. This module composes
WP1 proposals (including tiled proposals for large photos), WP2 segmentation
and WP3 OCR so a demo can show every plausible plate in the same frame.
"""

from __future__ import annotations

import cv2
import numpy as np

from .detection import Candidate, _iou, find_candidates
from .pipeline_wp1 import _normalize
from .pipeline_wp2 import segment_plate_candidates
from .pipeline_wp4 import postprocess
from .plate_reader import rank_plate_candidates
from .text_regions import text_regions

DEFAULT_MAX_CANDIDATES = 18
DEFAULT_MAX_OCR = 10
DEFAULT_MAX_PLATES = 10
TILE_TRIGGER_SIDE = 1600
TILE_SIZE = 1600
TILE_OVERLAP = 0.20
HYPOTHESES_PER_CANDIDATE = 5


def _tile_windows(width: int, height: int) -> list[tuple[int, int, int, int]]:
    """Return overlapping windows for photos too large for one 800px pass."""
    if max(width, height) <= TILE_TRIGGER_SIDE:
        return []
    tile_w = min(TILE_SIZE, width)
    tile_h = min(TILE_SIZE, height)
    step_x = max(1, round(tile_w * (1 - TILE_OVERLAP)))
    step_y = max(1, round(tile_h * (1 - TILE_OVERLAP)))
    xs = list(range(0, max(1, width - tile_w + 1), step_x))
    ys = list(range(0, max(1, height - tile_h + 1), step_y))
    if xs[-1] != width - tile_w:
        xs.append(max(0, width - tile_w))
    if ys[-1] != height - tile_h:
        ys.append(max(0, height - tile_h))
    return [(x, y, x + tile_w, y + tile_h) for y in ys for x in xs]


def _map_tile_candidate(candidate: Candidate, x0: int, y0: int, width: int, height: int) -> Candidate:
    x1, y1, x2, y2 = candidate.bbox
    bbox = (
        max(0, min(width, x1 + x0)),
        max(0, min(height, y1 + y0)),
        max(0, min(width, x2 + x0)),
        max(0, min(height, y2 + y0)),
    )
    if bbox[2] <= bbox[0] or bbox[3] <= bbox[1]:
        return candidate
    corners = candidate.corners + np.array([x0, y0], np.float32)
    return Candidate(bbox, corners, candidate.score, f"{candidate.source}@tile")


def _containment(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    overlap = max(0, right - left) * max(0, bottom - top)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return overlap / max(1, min(area_a, area_b))


def _dedupe_candidates(candidates: list[Candidate], limit: int) -> list[Candidate]:
    unique: list[Candidate] = []
    for candidate in sorted(candidates, key=lambda item: item.score, reverse=True):
        duplicate = False
        for other in unique:
            if _iou(candidate.bbox, other.bbox) >= 0.55 or _containment(candidate.bbox, other.bbox) >= 0.75:
                duplicate = True
                break
        if duplicate:
            continue
        unique.append(candidate)
        if len(unique) >= limit:
            break
    return unique


def propose_plate_candidates(
    image: np.ndarray,
    *,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    use_tiles: bool = True,
    include_text_regions: bool = True,
) -> list[Candidate]:
    """Return deduplicated WP1-style proposals for every plate in the frame."""
    if image is None or image.size == 0:
        return []
    height, width = image.shape[:2]
    proposals = find_candidates(image, max_candidates=max_candidates)
    if use_tiles:
        for x0, y0, x1, y1 in _tile_windows(width, height):
            tile = image[y0:y1, x0:x1]
            for candidate in find_candidates(tile, max_candidates=6):
                proposals.append(_map_tile_candidate(candidate, x0, y0, width, height))
    if include_text_regions:
        proposals.extend(text_regions(image))
    return _dedupe_candidates(proposals, max_candidates)


def _prepare_candidate(
    image: np.ndarray,
    candidate: Candidate,
    classifier,
    *,
    vehicle_type: str,
) -> dict | None:
    x1, y1, x2, y2 = candidate.bbox
    if x2 - x1 < 18 or y2 - y1 < 10:
        return None
    crop = image[y1:y2, x1:x2].copy()
    if crop.size == 0:
        return None
    try:
        normalized, angle = _normalize(crop, candidate.corners - np.array([x1, y1], np.float32))
        hypotheses = segment_plate_candidates(normalized)
        hypotheses = sorted(hypotheses, key=lambda item: item["segmentation_score"], reverse=True)
        hypotheses = hypotheses[:HYPOTHESES_PER_CANDIDATE]
        if not hypotheses:
            return None
        segmentation = hypotheses[0]
        if segmentation["num_chars"] < 4:
            return None
        ranked = rank_plate_candidates(normalized, classifier, hypotheses=hypotheses)
    except (ValueError, cv2.error):
        return None
    segmentation = ranked[0]
    ocr = segmentation["ocr"]
    if not ocr["confidences"]:
        return None
    result = postprocess(ocr["raw_text"], ocr["confidences"], vehicle_type=vehicle_type)
    mean_confidence = float(np.mean(ocr["confidences"]))
    min_confidence = float(np.min(ocr["confidences"]))
    quality_ok = bool(
        len(ocr["confidences"]) >= 4
        and min_confidence >= 0.35
        and mean_confidence >= 0.80
    )
    plausible = bool(result["is_valid"]) or (
        segmentation["num_chars"] >= 7 and mean_confidence >= 0.60
    )
    if not plausible or mean_confidence < 0.52:
        return None
    selection_score = (
        segmentation["recognition_score"]
        + 0.5 * float(result["is_valid"])
        + 0.05 * candidate.score
        + 0.10 * mean_confidence
    )
    return {
        "plate_crop": crop,
        "plate_normalized": normalized,
        "bbox": list(candidate.bbox),
        "angle": angle,
        "confidence": min(1.0, candidate.score),
        "source": candidate.source,
        "segmentation": segmentation,
        "ocr": ocr,
        "postprocessing": result,
        "plate_text": result["plate_text"],
        "raw_text": ocr["raw_text"],
        "is_valid": result["is_valid"],
        "province": result["province"],
        "vehicle_type": result["vehicle_type"],
        "recognition_confidence": mean_confidence,
        "quality_ok": quality_ok,
        "status": "recognized" if result["is_valid"] and quality_ok else "needs_review",
        "selection_score": selection_score,
    }


def _dedupe_plates(plates: list[dict]) -> list[dict]:
    def containment(a, b) -> float:
        left, top = max(a[0], b[0]), max(a[1], b[1])
        right, bottom = min(a[2], b[2]), min(a[3], b[3])
        overlap = max(0, right - left) * max(0, bottom - top)
        area_a = (a[2] - a[0]) * (a[3] - a[1])
        area_b = (b[2] - b[0]) * (b[3] - b[1])
        return overlap / max(1, min(area_a, area_b))

    unique: list[dict] = []
    for plate in sorted(plates, key=lambda item: item["selection_score"], reverse=True):
        duplicate = False
        for other in unique:
            if _iou(plate["bbox"], other["bbox"]) >= 0.55 or containment(plate["bbox"], other["bbox"]) >= 0.75:
                duplicate = True
                break
            same_text = plate["raw_text"] and plate["raw_text"] == other["raw_text"]
            centers_close = (
                abs((plate["bbox"][0] + plate["bbox"][2]) - (other["bbox"][0] + other["bbox"][2]))
                < 0.10 * max(plate["bbox"][2] - plate["bbox"][0], other["bbox"][2] - other["bbox"][0])
                and abs((plate["bbox"][1] + plate["bbox"][3]) - (other["bbox"][1] + other["bbox"][3]))
                < 0.10 * max(plate["bbox"][3] - plate["bbox"][1], other["bbox"][3] - other["bbox"][1])
            )
            if same_text and centers_close:
                duplicate = True
                break
        if not duplicate:
            unique.append(plate)
    unique.sort(key=lambda item: (bool(item["is_valid"]), item["selection_score"]), reverse=True)
    return unique


def _read_candidates(
    image: np.ndarray,
    classifier,
    candidates: list[Candidate],
    *,
    vehicle_type: str,
) -> list[dict]:
    prepared = []
    for candidate in candidates:
        item = _prepare_candidate(image, candidate, classifier, vehicle_type=vehicle_type)
        if item is not None:
            prepared.append(item)
    prepared.sort(key=lambda item: item["selection_score"], reverse=True)
    return _dedupe_plates(prepared)


def recognize_plates(
    image: np.ndarray,
    classifier,
    *,
    max_plates: int = DEFAULT_MAX_PLATES,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    max_ocr: int = DEFAULT_MAX_OCR,
    use_tiles: bool = True,
    include_text_regions: bool | None = None,
    vehicle_type: str = "unknown",
) -> list[dict]:
    """Return all plausible plate readings with boxes and OCR details.

    ``include_text_regions=None`` tries the contour detector first. Only when
    that finds nothing does it fall back to aligned-character proposals, which
    recover plates joined to the vehicle body but also invite false positives.
    """
    if not 1 <= max_plates <= 30:
        raise ValueError("max_plates must be between 1 and 30")
    if not 1 <= max_candidates <= 60:
        raise ValueError("max_candidates must be between 1 and 60")
    candidates = propose_plate_candidates(
        image,
        max_candidates=max_candidates,
        use_tiles=use_tiles,
        include_text_regions=bool(include_text_regions),
    )
    plates = _read_candidates(image, classifier, candidates[:max_ocr], vehicle_type=vehicle_type)
    if not plates and include_text_regions is None:
        fallback = propose_plate_candidates(
            image,
            max_candidates=max_candidates,
            use_tiles=use_tiles,
            include_text_regions=True,
        )
        plates = _read_candidates(image, classifier, fallback[:max_ocr], vehicle_type=vehicle_type)
    return plates[:max_plates]


def annotate_plates(image: np.ndarray, plates: list[dict]) -> np.ndarray:
    """Draw numbered boxes and plate strings on a copy of the source image."""
    canvas = image.copy()
    height, width = canvas.shape[:2]
    scale = max(1.0, min(width, height) / 900)
    thickness = max(2, round(2 * scale))
    font_scale = max(0.55, min(1.25, min(width, height) / 850))
    font_thickness = max(1, round(1.2 * scale))
    for index, plate in enumerate(plates, 1):
        x1, y1, x2, y2 = (int(value) for value in plate["bbox"])
        valid = bool(plate.get("is_valid"))
        color = (65, 170, 75) if valid else (0, 165, 255)
        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, thickness)
        text = f"#{index} {plate.get('plate_text') or plate.get('raw_text') or '?'}"
        (text_width, text_height), baseline = cv2.getTextSize(
            text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness
        )
        label_bottom = max(text_height + baseline + 4, y1 - 4)
        label_top = label_bottom - text_height - baseline - 6
        label_right = min(width - 1, x1 + text_width + 8)
        cv2.rectangle(canvas, (x1, label_top), (label_right, label_bottom), color, -1)
        cv2.putText(
            canvas,
            text,
            (x1 + 4, label_bottom - baseline - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            (20, 20, 20) if not valid else (255, 255, 255),
            font_thickness,
            cv2.LINE_AA,
        )
    return canvas


def summarize_plate(plate: dict) -> dict:
    """Serialize a plate reading without image arrays."""
    keys = (
        "bbox",
        "angle",
        "confidence",
        "source",
        "plate_text",
        "raw_text",
        "is_valid",
        "province",
        "vehicle_type",
        "recognition_confidence",
        "quality_ok",
        "status",
        "selection_score",
    )
    summary = {key: plate[key] for key in keys}
    segmentation = plate["segmentation"]
    summary.update(
        {
            "num_chars": segmentation["num_chars"],
            "line_type": segmentation["line_type"],
            "threshold_method": segmentation["threshold_method"],
        }
    )
    return summary
