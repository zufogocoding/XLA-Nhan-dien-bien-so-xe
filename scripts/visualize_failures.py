"""Visualize WP1 failures for debugging: ground truth vs predicted boxes."""

import argparse
from pathlib import Path
from collections import defaultdict
import json

import cv2
import numpy as np

from src.pipeline_wp1 import detect_plate


def iou(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    overlap = max(0, right - left) * max(0, bottom - top)
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - overlap
    return overlap / max(1, union)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("split_dir", type=Path)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--out", type=Path, default=Path("outputs/failures"))
    args = parser.parse_args()

    data = json.loads((args.split_dir / "_annotations.coco.json").read_text(encoding="utf-8"))
    by_image = defaultdict(list)
    for ann in data["annotations"]:
        x, y, w, h = ann["bbox"]
        by_image[ann["image_id"]].append((x, y, x + w, y + h))

    args.out.mkdir(parents=True, exist_ok=True)
    n_fail = 0
    for item in data["images"][:args.limit]:
        image = cv2.imdecode(np.fromfile(args.split_dir / item["file_name"], dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            continue
        result = detect_plate(args.split_dir / item["file_name"])
        pred = [tuple(result["bbox"])] if result else []
        gt = by_image[item["id"]]
        matched = set()
        for box in pred:
            best = max(((iou(box, g), i) for i, g in enumerate(gt) if i not in matched), default=(0, -1))
            if best[0] >= 0.5:
                matched.add(best[1])
        if len(matched) < len(gt):
            n_fail += 1
            vis = image.copy()
            for (x, y, x2, y2) in gt:
                cv2.rectangle(vis, (int(x), int(y)), (int(x2), int(y2)), (0, 255, 0), 4)
            for box in pred:
                cv2.rectangle(vis, (box[0], box[1]), (box[2], box[3]), (0, 0, 255), 4)
            cv2.putText(vis, item["file_name"][:24], (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imwrite(str(args.out / f"fail_{n_fail:02d}_{item['file_name']}"), vis)
            print(f"fail_{n_fail:02d} {item['file_name']}")
    print(f"total failures: {n_fail}")