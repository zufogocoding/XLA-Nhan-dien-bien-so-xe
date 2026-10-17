"""Evaluate WP1 proposals against COCO boxes without using labels in detection."""

import argparse
import json
from collections import defaultdict
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

from src.detection import find_candidates


def iou(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    overlap = max(0, right - left) * max(0, bottom - top)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - overlap
    return overlap / max(1, union)


def evaluate(split_dir: Path, limit: int | None = None, threshold: float = 0.50, max_candidates: int = 1, category: int | None = None):
    data = json.loads((split_dir / "_annotations.coco.json").read_text(encoding="utf-8"))
    by_image = defaultdict(list)
    for annotation in data["annotations"]:
        if category is not None and annotation["category_id"] != category:
            continue
        x, y, w, h = annotation["bbox"]
        by_image[annotation["image_id"]].append((x, y, x + w, y + h))
    counts = {"tp": 0, "fp": 0, "fn": 0, "images": 0, "read_errors": 0}
    durations = []
    failures = []
    images = data["images"] if category is None else [item for item in data["images"] if item["id"] in by_image]
    for item in images[:limit]:
        image = cv2.imdecode(np.fromfile(split_dir / item["file_name"], dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            counts["read_errors"] += 1
            continue
        start = perf_counter()
        candidates = find_candidates(image, max_candidates=max_candidates)
        durations.append(1000 * (perf_counter() - start))
        gt = by_image[item["id"]]
        matched = set()
        local_tp = 0
        for candidate in candidates:
            best = max(((iou(candidate.bbox, box), index) for index, box in enumerate(gt) if index not in matched), default=(0, -1))
            if best[0] >= threshold:
                matched.add(best[1])
                local_tp += 1
        counts["tp"] += local_tp
        counts["fp"] += len(candidates) - local_tp
        counts["fn"] += len(gt) - local_tp
        counts["images"] += 1
        if local_tp < len(gt):
            failures.append({"file": item["file_name"], "ground_truth": gt, "predicted": [c.bbox for c in candidates]})
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    counts.update(precision=precision, recall=recall, f1=2 * precision * recall / (precision + recall) if precision + recall else 0.0,
                  mean_ms=float(np.mean(durations)) if durations else None, median_ms=float(np.median(durations)) if durations else None,
                  iou_threshold=threshold, max_candidates=max_candidates, category=category, sample_failures=failures[:10])
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-candidates", type=int, default=1)
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument("--category", type=int)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.split_dir, args.limit, args.iou, args.max_candidates, args.category), indent=2))
