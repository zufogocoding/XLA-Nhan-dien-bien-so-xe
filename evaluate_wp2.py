"""Evaluate WP2 character segmentation.

Synthetic plates provide exact character boxes, so they are used for the
numeric metrics. The public dataset only labels plate boxes, so real plates are
audited visually and by character-count plausibility instead.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from time import perf_counter

import cv2
import numpy as np

from scripts.make_synthetic_wp2 import make_dataset
from src.pipeline_wp1 import detect_plate
from src.pipeline_wp2 import segment_plate


def box_iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    """IoU of two ``(x, y, w, h)`` boxes."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    left, top = max(ax, bx), max(ay, by)
    right, bottom = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    intersection = max(0, right - left) * max(0, bottom - top)
    union = aw * ah + bw * bh - intersection
    return intersection / max(1, union)


def match_boxes(
    predicted: list[tuple[int, int, int, int]],
    ground_truth: list[tuple[int, int, int, int]],
    threshold: float = 0.5,
) -> list[tuple[int, int, float]]:
    """Greedily match boxes one-to-one, highest IoU first."""
    pairs = [
        (box_iou(prediction, target), pred_index, gt_index)
        for pred_index, prediction in enumerate(predicted)
        for gt_index, target in enumerate(ground_truth)
    ]
    pairs.sort(reverse=True)
    used_predicted: set[int] = set()
    used_gt: set[int] = set()
    matches = []
    for score, pred_index, gt_index in pairs:
        if score < threshold:
            break
        if pred_index in used_predicted or gt_index in used_gt:
            continue
        used_predicted.add(pred_index)
        used_gt.add(gt_index)
        matches.append((pred_index, gt_index, float(score)))
    return matches


def _ink_height(patch: np.ndarray) -> int:
    rows = np.flatnonzero((patch > 0).any(axis=1))
    return int(rows[-1] - rows[0] + 1) if rows.size else 0


def _size_consistency(heights: list[int]) -> tuple[float, float, float]:
    """Return ``(within_5pct, mean, std)`` for normalized glyph heights."""
    if not heights:
        return 0.0, 0.0, 0.0
    values = np.asarray(heights, dtype=np.float32)
    median = float(np.median(values))
    within = float(np.mean(np.abs(values - median) <= 0.05 * max(1.0, median)))
    return within, float(values.mean()), float(values.std())


def evaluate_synthetic(
    count: int = 100,
    seed: int = 2026,
    strengths: tuple[str, ...] = ("easy", "typical", "hard"),
    iou_threshold: float = 0.5,
) -> dict:
    """Run WP2 on synthetic plates with exact character ground truth."""
    report: dict = {
        "config": {
            "count_per_strength": count,
            "seed": seed,
            "strengths": list(strengths),
            "iou_threshold": iou_threshold,
        },
        "levels": {},
    }
    for strength in strengths:
        plates = make_dataset(count, seed=seed, strength=strength)
        tp = fp = fn = 0
        exact_plates = 0
        line_ok = 0
        output_sizes_ok = 0
        durations = []
        heights: list[int] = []
        by_line: dict[str, dict[str, int]] = defaultdict(
            lambda: {"tp": 0, "fp": 0, "fn": 0, "plates": 0, "line_ok": 0}
        )
        failures = []

        for index, plate in enumerate(plates):
            start = perf_counter()
            result = segment_plate(plate.image)
            durations.append(1000 * (perf_counter() - start))

            ground_truth = [char["bbox"] for char in plate.chars]
            predicted = result["positions"]
            matches = match_boxes(predicted, ground_truth, iou_threshold)
            matched = len(matches)
            tp += matched
            fp += len(predicted) - matched
            fn += len(ground_truth) - matched
            if len(predicted) == len(ground_truth) and matched == len(ground_truth):
                exact_plates += 1
            if result["line_type"] == plate.line_type:
                line_ok += 1

            bucket = by_line[plate.line_type]
            bucket["tp"] += matched
            bucket["fp"] += len(predicted) - matched
            bucket["fn"] += len(ground_truth) - matched
            bucket["plates"] += 1
            bucket["line_ok"] += int(result["line_type"] == plate.line_type)

            size = result["normalized_size"]
            if all(
                patch.shape == (size, size) and patch.dtype == np.uint8
                for patch in result["characters"]
            ):
                output_sizes_ok += 1
            heights.extend(_ink_height(patch) for patch in result["char_binary"])

            if matched < len(ground_truth) or len(predicted) != len(ground_truth):
                failures.append(
                    {
                        "index": index,
                        "seed": seed + index,
                        "line_type": plate.line_type,
                        "predicted_line_type": result["line_type"],
                        "gt_chars": len(ground_truth),
                        "predicted_chars": len(predicted),
                        "matched_chars": matched,
                        "binarization": result["binarization"],
                    }
                )

        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        f1 = 2 * precision * recall / max(1e-9, precision + recall)
        consistency, height_mean, height_std = _size_consistency(heights)
        level = {
            "plates": len(plates),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "segmentation_accuracy": recall,
            "exact_plate_accuracy": exact_plates / max(1, len(plates)),
            "line_separation_accuracy": line_ok / max(1, len(plates)),
            "output_size_consistency": output_sizes_ok / max(1, len(plates)),
            "glyph_height_within_5pct": consistency,
            "glyph_height_mean": height_mean,
            "glyph_height_std": height_std,
            "mean_ms": float(np.mean(durations)),
            "median_ms": float(np.median(durations)),
            "by_line_type": dict(by_line),
            "failures": failures[:10],
        }
        report["levels"][strength] = level
    return report


def _audit_tile(
    name: str, plate: np.ndarray, positions: list[tuple[int, int, int, int]], note: str
) -> np.ndarray:
    tile = plate.copy()
    if tile.ndim == 2:
        tile = cv2.cvtColor(tile, cv2.COLOR_GRAY2BGR)
    for x, y, w, h in positions:
        cv2.rectangle(tile, (x, y), (x + w, y + h), (0, 0, 255), 1)
    target_width = 420
    scale = target_width / max(1, tile.shape[1])
    tile = cv2.resize(
        tile,
        (target_width, max(1, round(tile.shape[0] * scale))),
        interpolation=cv2.INTER_AREA,
    )
    tile = cv2.copyMakeBorder(tile, 28, 0, 0, 0, cv2.BORDER_CONSTANT, value=(32, 32, 32))
    label = f"{name} | {note}"
    cv2.putText(
        tile,
        label[:64],
        (4, 19),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.48,
        (245, 245, 245),
        1,
        cv2.LINE_AA,
    )
    return tile


def _save_audit(rows: list[dict], output_path: Path) -> None:
    tiles = [
        _audit_tile(
            row["name"],
            row["plate"],
            row["positions"],
            f'n={row["num_chars"]} {row["line_type"]} {row["binarization"]}',
        )
        for row in rows
    ]
    if not tiles:
        return
    height = max(tile.shape[0] for tile in tiles)
    tiles = [
        cv2.copyMakeBorder(
            tile, 0, height - tile.shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(32, 32, 32)
        )
        for tile in tiles
    ]
    rows_of_tiles = [
        np.hstack(tiles[index : index + 2]) for index in range(0, len(tiles), 2)
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), np.vstack(rows_of_tiles))


def _plate_annotations(split_dir: Path) -> tuple[dict, dict]:
    data = json.loads((split_dir / "_annotations.coco.json").read_text(encoding="utf-8"))
    plate_category = next(
        (
            category["id"]
            for category in data["categories"]
            if category["name"].strip().lower() == "plate"
        ),
        None,
    )
    annotated_categories = {annotation["category_id"] for annotation in data["annotations"]}
    # Some exports name the plate class "plate" but attach every box to the
    # sub-categories "0"/"1". In that case all boxes are still plate boxes.
    use_all = plate_category is None or plate_category not in annotated_categories

    by_image: dict[int, list] = defaultdict(list)
    for annotation in data["annotations"]:
        if not use_all and annotation["category_id"] != plate_category:
            continue
        by_image[annotation["image_id"]].append(annotation["bbox"])
    return data, by_image


def evaluate_real(
    split_dir: Path,
    limit: int = 60,
    iou_threshold: float = 0.5,
    audit_output: Path | None = None,
    audit_limit: int = 20,
) -> dict:
    """Audit WP2 on real plates whose WP1 crop is correct.

    The dataset has no character labels, so this measures response shape,
    character-count plausibility and speed, not character accuracy.
    """
    data, by_image = _plate_annotations(split_dir)
    count_distribution: Counter[int] = Counter()
    line_distribution: Counter[str] = Counter()
    method_distribution: Counter[str] = Counter()
    durations = []
    audit_rows = []
    checked = 0
    correct_wp1 = 0
    read_errors = 0

    for item in data["images"]:
        if len(by_image[item["id"]]) != 1:
            continue
        if checked >= limit:
            break
        path = split_dir / item["file_name"]
        try:
            detection = detect_plate(path)
        except ValueError:
            read_errors += 1
            continue
        if detection is None:
            checked += 1
            continue
        checked += 1

        x, y, w, h = by_image[item["id"]][0]
        x1, y1, x2, y2 = detection["bbox"]
        if box_iou((x, y, w, h), (x1, y1, x2 - x1, y2 - y1)) < iou_threshold:
            continue
        correct_wp1 += 1

        start = perf_counter()
        result = segment_plate(detection["plate_normalized"])
        durations.append(1000 * (perf_counter() - start))
        count_distribution[result["num_chars"]] += 1
        line_distribution[result["line_type"]] += 1
        method_distribution[result["binarization"]] += 1
        if len(audit_rows) < audit_limit:
            audit_rows.append(
                {
                    "name": item["file_name"].split("_")[1],
                    "plate": detection["plate_normalized"],
                    "positions": result["positions"],
                    "num_chars": result["num_chars"],
                    "line_type": result["line_type"],
                    "binarization": result["binarization"],
                }
            )

    if audit_output is not None and audit_rows:
        _save_audit(audit_rows, audit_output)

    total = sum(count_distribution.values())
    plausible = sum(
        value for count, value in count_distribution.items() if 6 <= count <= 10
    )
    plausible_7_9 = sum(
        value for count, value in count_distribution.items() if 7 <= count <= 9
    )
    return {
        "config": {
            "split": str(split_dir),
            "limit": limit,
            "iou_threshold": iou_threshold,
        },
        "images_checked": checked,
        "correct_wp1_detections": correct_wp1,
        "read_errors": read_errors,
        "count_distribution": dict(sorted(count_distribution.items())),
        "line_type_distribution": dict(line_distribution),
        "binarization_distribution": dict(method_distribution),
        "plausible_count_6_to_10": plausible / max(1, total),
        "plausible_count_7_to_9": plausible_7_9 / max(1, total),
        "mean_ms": float(np.mean(durations)) if durations else None,
        "median_ms": float(np.median(durations)) if durations else None,
        "audit_output": str(audit_output) if audit_output else None,
        "samples": [
            {key: value for key, value in row.items() if key != "plate"}
            for row in audit_rows
        ],
        "note": (
            "Real split has plate boxes only, so character accuracy cannot be "
            "measured. Count plausibility and the saved montage are a manual "
            "audit aid, not ground truth."
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100, help="plates per difficulty")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--iou", type=float, default=0.5)
    parser.add_argument(
        "--strengths",
        nargs="+",
        choices=("easy", "typical", "hard"),
        default=("easy", "typical", "hard"),
    )
    parser.add_argument("--skip-synthetic", action="store_true")
    parser.add_argument("--real-split", type=Path)
    parser.add_argument("--real-limit", type=int, default=60)
    parser.add_argument("--audit-output", type=Path, default=Path("demo/wp2_real_audit.png"))
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    output: dict = {}
    if not args.skip_synthetic:
        output["synthetic"] = evaluate_synthetic(
            args.count, args.seed, tuple(args.strengths), args.iou
        )
    if args.real_split is not None:
        output["real"] = evaluate_real(
            args.real_split,
            limit=args.real_limit,
            iou_threshold=args.iou,
            audit_output=args.audit_output,
        )
    text = json.dumps(output, ensure_ascii=False, indent=2)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(text, encoding="utf-8")
    print(text)
