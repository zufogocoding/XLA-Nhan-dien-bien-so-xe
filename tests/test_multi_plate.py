"""Multi-plate proposal and API contracts."""

import cv2
import numpy as np
from fastapi.testclient import TestClient

from api.main import create_app
from src.detection import Candidate
from src.multi_plate import _dedupe_candidates, _dedupe_plates, _tile_windows
from src.pipeline_wp1 import detect_plates_image


def _candidate(bbox, score):
    x1, y1, x2, y2 = bbox
    corners = np.array(
        [[0, 0], [x2 - x1 - 1, 0], [x2 - x1 - 1, y2 - y1 - 1], [0, y2 - y1 - 1]],
        np.float32,
    )
    return Candidate(bbox, corners, score, "edges")


def test_standalone_wp1_multi_returns_every_detector_proposal(monkeypatch):
    image = np.full((160, 320, 3), 230, np.uint8)
    candidates = [_candidate((20, 30, 130, 80), .9), _candidate((180, 90, 290, 140), .7)]
    monkeypatch.setattr("src.pipeline_wp1.find_candidates", lambda *_args, **_kwargs: candidates)

    results = detect_plates_image(image, max_plates=10)

    assert [result["bbox"] for result in results] == [list(item.bbox) for item in candidates]
    assert all(set(result) == {"bbox", "plate_crop", "plate_normalized", "angle", "confidence"} for result in results)


def test_tile_windows_cover_a_large_photo():
    windows = _tile_windows(4000, 3000)
    assert len(windows) >= 4
    assert min(x1 for x1, _, _, _ in windows) == 0
    assert max(x2 for _, _, x2, _ in windows) == 4000
    assert min(y1 for _, y1, _, _ in windows) == 0
    assert max(y2 for _, _, _, y2 in windows) == 3000
    assert all(0 <= x1 < x2 <= 4000 and 0 <= y1 < y2 <= 3000 for x1, y1, x2, y2 in windows)


def test_nested_candidates_do_not_crowd_out_distinct_plates():
    large = _candidate((0, 0, 400, 200), .99)
    nested = [_candidate((10 + i, 10 + i, 390 - i, 190 - i), .98 - i * .01) for i in range(5)]
    other_top = _candidate((500, 0, 700, 100), .8)
    other_bottom = _candidate((0, 400, 200, 500), .7)

    kept = _dedupe_candidates([large, *nested, other_top, other_bottom], 3)

    assert [candidate.bbox for candidate in kept] == [
        large.bbox,
        other_top.bbox,
        other_bottom.bbox,
    ]


def test_contained_sub_box_does_not_become_a_second_plate():
    plate = {"bbox": [100, 100, 300, 220], "raw_text": "59B49136", "is_valid": True, "selection_score": 1.0}
    contained = {"bbox": [110, 110, 290, 210], "raw_text": "59B49136", "is_valid": True, "selection_score": .9}
    assert _dedupe_plates([contained, plate]) == [plate]


def test_multi_plate_api_without_ocr_still_returns_an_annotated_image(tmp_path):
    with TestClient(create_app(tmp_path / "runtime", tmp_path / "empty-models")) as client:
        content = cv2.imencode(".png", np.full((80, 120, 3), 255, np.uint8))[1].tobytes()
        response = client.post("/api/upload/image/multi", files={"file": ("empty.png", content, "image/png")})
        assert response.status_code == 200
        result = response.json()
        assert result["count"] == 0
        assert result["items"][0]["status"] in {"no_plate", "ocr_unavailable"}
        assert client.get(result["annotated_url"]).status_code == 200
        assert client.get(result["source_url"]).status_code == 200
