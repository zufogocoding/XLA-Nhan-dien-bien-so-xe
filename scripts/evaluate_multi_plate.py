"""Evaluate multi-plate localization on COCO images with two or more plates.

The default split is ``valid`` because thresholds and defaults must not be
tuned on ``test``. Ground-truth text is not available in this dataset, so this
script measures boxes only, not OCR string accuracy.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
import sys
from time import perf_counter

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.character_classifier import CharacterClassifier
from src.detection import _iou
from src.multi_plate import recognize_plates, summarize_plate


def load_classifier(model_dir: Path) -> CharacterClassifier:
    manifest = model_dir / "ocr_manifest.json"
    artifact = json.loads(manifest.read_text(encoding="utf-8"))["artifact"] if manifest.exists() else "svm_hog.pkl"
    classifier = CharacterClassifier(model_dir / artifact)
    classifier.load()
    return classifier


def match(predictions: list[dict], ground_truth: list[tuple], threshold: float = .5) -> tuple[int, int, int]:
    matched: set[int] = set()
    true_positive = 0
    for prediction in predictions:
        best_iou, best_index = max(
            ((_iou(prediction["bbox"], box), index) for index, box in enumerate(ground_truth) if index not in matched),
            default=(0., -1),
        )
        if best_iou >= threshold:
            matched.add(best_index)
            true_positive += 1
    return true_positive, len(predictions) - true_positive, len(ground_truth) - true_positive


def metrics(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else 0.
    recall = tp / (tp + fn) if tp + fn else 0.
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.,
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("split", type=Path, nargs="?", default=ROOT / "Vietnam License Plate.v2i.coco/valid")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/wp_multi_plate_evaluation.json")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "models")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--min-boxes", type=int, default=2)
    parser.add_argument(
        "--min-plate-area",
        type=float,
        default=0.0,
        help="only score plates occupying at least this fraction of the image (e.g. 0.01 for 1%%)",
    )
    parser.add_argument("--max-plates", type=int, default=10)
    args = parser.parse_args()
    if args.split.name == "test":
        print("warning: test split is for reporting only; do not tune defaults on it", file=sys.stderr)

    data = json.loads((args.split / "_annotations.coco.json").read_text(encoding="utf-8"))
    ground_truth: dict[int, list[tuple]] = defaultdict(list)
    for annotation in data["annotations"]:
        x, y, width, height = annotation["bbox"]
        ground_truth[annotation["image_id"]].append((x, y, x + width, y + height))

    def area_fraction(box, item) -> float:
        return (box[2] - box[0]) * (box[3] - box[1]) / max(1, item["width"] * item["height"])

    images = []
    for item in data["images"]:
        boxes = ground_truth[item["id"]]
        if args.min_plate_area > 0:
            boxes = [box for box in boxes if area_fraction(box, item) >= args.min_plate_area]
            ground_truth[item["id"]] = boxes
        if len(boxes) >= args.min_boxes:
            images.append(item)
    if args.limit:
        images = images[:args.limit]
    if not images:
        raise SystemExit("no images with enough ground-truth boxes")

    classifier = load_classifier(args.model_dir)
    start = perf_counter()
    cases = []
    all_tp = all_fp = all_fn = 0
    top1_tp = top1_fp = top1_fn = 0
    complete = 0
    for index, item in enumerate(images, 1):
        image = cv2.imdecode(np.fromfile(args.split / item["file_name"], np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"unreadable image: {item['file_name']}")
        predictions = recognize_plates(
            image,
            classifier,
            max_plates=args.max_plates,
            vehicle_type="unknown",
        )
        if args.min_plate_area > 0:
            predictions = [
                plate for plate in predictions
                if area_fraction(plate["bbox"], item) >= args.min_plate_area
            ]
        boxes = ground_truth[item["id"]]
        tp, fp, fn = match(predictions, boxes)
        one_tp, one_fp, one_fn = match(predictions[:1], boxes)
        all_tp += tp; all_fp += fp; all_fn += fn
        top1_tp += one_tp; top1_fp += one_fp; top1_fn += one_fn
        complete += int(tp == len(boxes))
        cases.append(
            {
                "file": item["file_name"],
                "ground_truth": boxes,
                "predictions": [
                    {"bbox": plate["bbox"], "plate_text": plate["plate_text"], "raw_text": plate["raw_text"],
                     "is_valid": plate["is_valid"], "status": plate["status"]}
                    for plate in predictions
                ],
                "tp": tp, "fp": fp, "fn": fn,
            }
        )
        if index % 25 == 0:
            print(f"processed {index}/{len(images)}", flush=True)

    elapsed = perf_counter() - start
    report = {
        "split": str(args.split),
        "images": len(images),
        "min_boxes": args.min_boxes,
        "min_plate_area": args.min_plate_area,
        "iou_threshold": .5,
        "scope": "multi-plate box localization; no OCR text labels; predictions may include unannotated background plates",
        "elapsed_seconds": elapsed,
        "mean_seconds_per_image": elapsed / len(images),
        "multi": {**metrics(all_tp, all_fp, all_fn), "images_all_boxes_recalled": complete},
        "top1": metrics(top1_tp, top1_fp, top1_fn),
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
