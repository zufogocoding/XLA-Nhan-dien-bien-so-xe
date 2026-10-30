"""Reproduce the WP1 failure analysis on the COCO test split.

The script separates three questions that are often mixed together:

* Does the top-1 standalone WP1 box match a plate? (the reported F1)
* Is a correct box anywhere in the top-10 detector proposals?
* Do large ground-truth boxes fall outside the default 30% area cap?

It also retries the large-box images with ``max_area_fraction=1.0`` to test
whether the cap, rather than the detector, causes those misses. Boxes only:
COCO has no plate-text labels.

Example:
    python scripts/diagnose_wp1_failures.py
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
import sys
from time import perf_counter

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.detection import _iou, find_candidates

IOU_THRESHOLD = 0.5
TOP_K = 10
DEFAULT_MAX_AREA = 0.30


def metrics(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def match_one(prediction, ground_truth, matched: set[int], threshold: float = IOU_THRESHOLD):
    """Return the index of the best unmatched ground-truth box, or None."""
    best_iou, best_index = 0.0, None
    for index, box in enumerate(ground_truth):
        if index in matched:
            continue
        iou = _iou(prediction, box)
        if iou > best_iou:
            best_iou, best_index = iou, index
    return best_index if best_iou >= threshold else None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "split",
        type=Path,
        nargs="?",
        default=ROOT / "Vietnam License Plate.v2i.coco/test",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "reports/wp1_failure_diagnosis.json",
    )
    parser.add_argument("--max-candidates", type=int, default=TOP_K)
    args = parser.parse_args()

    data = json.loads((args.split / "_annotations.coco.json").read_text(encoding="utf-8"))
    ground_truth: dict[int, list[tuple[int, int, int, int]]] = defaultdict(list)
    categories: dict[int, list[int]] = defaultdict(list)
    for annotation in data["annotations"]:
        x, y, width, height = annotation["bbox"]
        ground_truth[annotation["image_id"]].append((x, y, x + width, y + height))
        categories[annotation["image_id"]].append(annotation["category_id"])

    start = perf_counter()
    top1_tp = top1_fp = top1_fn = 0
    top10_tp = top10_fp = top10_fn = 0
    fn_without_correct_proposal = 0
    fn_best_iou: list[float] = []
    large_boxes = 0
    large_boxes_hit = 0
    large_retry_hits = 0
    images_with_large_boxes = 0
    category_tp: Counter[int] = Counter()
    category_boxes: Counter[int] = Counter()
    cases = []

    for index, item in enumerate(data["images"], 1):
        image = cv2.imdecode(
            np.fromfile(args.split / item["file_name"], np.uint8), cv2.IMREAD_COLOR
        )
        if image is None:
            raise ValueError(f"unreadable image: {item['file_name']}")
        boxes = ground_truth[item["id"]]
        labels = categories[item["id"]]
        proposals = find_candidates(image, max_candidates=args.max_candidates)

        # Top-1 standalone WP1: one prediction per image, as reported in the benchmark.
        matched: set[int] = set()
        if proposals:
            hit = match_one(proposals[0].bbox, boxes, matched)
            if hit is None:
                top1_fp += 1
            else:
                matched.add(hit)
                top1_tp += 1
                category_tp[labels[hit]] += 1
        top1_fn += len(boxes) - len(matched)
        for label in labels:
            category_boxes[label] += 1

        # Top-10 proposals, all returned: precision cost of "keep everything".
        matched10: set[int] = set()
        for proposal in proposals:
            hit = match_one(proposal.bbox, boxes, matched10)
            if hit is None:
                top10_fp += 1
            else:
                matched10.add(hit)
                top10_tp += 1
        top10_fn += len(boxes) - len(matched10)

        # Per-ground-truth-box coverage by the top-10 proposals.
        for box in boxes:
            best_iou = max((_iou(proposal.bbox, box) for proposal in proposals), default=0.0)
            if best_iou >= IOU_THRESHOLD:
                continue
            fn_without_correct_proposal += 1
            fn_best_iou.append(best_iou)

        # Large plates excluded by the default max_area_fraction=0.30.
        area_fractions = [
            (box[2] - box[0]) * (box[3] - box[1]) / max(1, item["width"] * item["height"])
            for box in boxes
        ]
        large_indices = [i for i, fraction in enumerate(area_fractions) if fraction > DEFAULT_MAX_AREA]
        if large_indices:
            images_with_large_boxes += 1
            large_boxes += len(large_indices)
            for i in large_indices:
                hit_now = max((_iou(proposal.bbox, boxes[i]) for proposal in proposals), default=0.0)
                large_boxes_hit += int(hit_now >= IOU_THRESHOLD)
            retry = find_candidates(
                image,
                max_candidates=args.max_candidates,
                max_area_fraction=1.0,
            )
            for i in large_indices:
                best = max((_iou(proposal.bbox, boxes[i]) for proposal in retry), default=0.0)
                large_retry_hits += int(best >= IOU_THRESHOLD)

        cases.append(
            {
                "file": item["file_name"],
                "gt_boxes": len(boxes),
                "proposals": len(proposals),
                "top1_iou": max((_iou(proposals[0].bbox, box) for box in boxes), default=0.0)
                if proposals
                else 0.0,
                "top10_covered_boxes": len(matched10),
                "large_boxes": len(large_indices),
            }
        )
        if index % 25 == 0:
            print(f"processed {index}/{len(data['images'])}", file=sys.stderr, flush=True)

    category_report = {}
    for label in sorted(category_boxes):
        tp = category_tp[label]
        fn = category_boxes[label] - tp
        category_report[str(label)] = {
            "boxes": category_boxes[label],
            "tp_top1": tp,
            "fn_top1": fn,
            "box_recall_top1": tp / category_boxes[label] if category_boxes[label] else 0.0,
        }

    fn_buckets = Counter()
    for value in fn_best_iou:
        if value < 0.10:
            fn_buckets["<0.10"] += 1
        elif value < 0.30:
            fn_buckets["0.10-0.30"] += 1
        elif value < 0.50:
            fn_buckets["0.30-0.50"] += 1
        else:
            fn_buckets[">=0.50"] += 1

    report = {
        "split": str(args.split),
        "images": len(data["images"]),
        "gt_boxes": sum(len(boxes) for boxes in ground_truth.values()),
        "iou_threshold": IOU_THRESHOLD,
        "max_candidates": args.max_candidates,
        "max_area_fraction": DEFAULT_MAX_AREA,
        "scope": "box localization only; COCO has no plate-text labels",
        "elapsed_seconds": perf_counter() - start,
        "top1": metrics(top1_tp, top1_fp, top1_fn),
        "top10_all": metrics(top10_tp, top10_fp, top10_fn),
        "top10_coverage": {
            "missed_gt_boxes": fn_without_correct_proposal,
            "missed_best_iou_buckets": dict(fn_buckets),
            "missed_best_iou_values": fn_best_iou,
        },
        "large_boxes": {
            "threshold_area_fraction": DEFAULT_MAX_AREA,
            "images": images_with_large_boxes,
            "boxes": large_boxes,
            "hit_with_default_cap": large_boxes_hit,
            "hit_when_cap_disabled": large_retry_hits,
        },
        "by_category_top1": category_report,
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    printable = {key: value for key, value in report.items() if key != "cases"}
    printable["top10_coverage"] = {
        key: value for key, value in printable["top10_coverage"].items() if key != "missed_best_iou_values"
    }
    print(json.dumps(printable, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
