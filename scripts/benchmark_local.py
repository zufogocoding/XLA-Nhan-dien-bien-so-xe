"""Measure warm local latency on a COCO split, using an isolated runtime."""

import argparse
from collections import Counter
import json
from pathlib import Path
import shutil
import sys
from time import perf_counter
import uuid

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.pipeline_wp1 import detect_plate
from src.service import RecognitionService


def summary(values):
    return {
        "mean_ms": float(np.mean(values)),
        "median_ms": float(np.median(values)),
        "p95_ms": float(np.percentile(values, 95)),
        "max_ms": float(np.max(values)),
    }


def benchmark(split: Path, output: Path):
    annotations = json.loads((split / "_annotations.coco.json").read_text(encoding="utf-8"))
    runtime = ROOT / "outputs" / ("benchmark-" + uuid.uuid4().hex)
    service = RecognitionService(runtime)
    paths = []
    for index, item in enumerate(annotations["images"]):
        source = split / item["file_name"]
        target = service.public / "uploads" / (str(index) + source.suffix)
        shutil.copyfile(source, target)
        paths.append((item["file_name"], target))
    if not paths:
        raise ValueError("split has no images")

    # Load models and initialize OpenCV before timing; remove only our warmup row.
    warmup = service.process_image(paths[0][1])
    service.database.delete(warmup["id"])
    samples = []
    for filename, path in paths:
        start = perf_counter()
        detect_plate(path)
        wp1_ms = (perf_counter() - start) * 1000
        start = perf_counter()
        record = service.process_image(path)
        pipeline_ms = (perf_counter() - start) * 1000
        samples.append({"file": filename, "wp1_ms": wp1_ms, "pipeline_ms": pipeline_ms, "status": record["status"]})

    counts = dict(Counter(sample["status"] for sample in samples))
    persisted = service.database.list(limit=1)["total"]
    assert persisted == len(paths)
    result = {
        "images": len(paths),
        "split": str(split),
        "runtime": str(runtime.relative_to(ROOT)),
        "model_version": service.readiness()["model_version"],
        "wp1": summary([sample["wp1_ms"] for sample in samples]),
        "pipeline": summary([sample["pipeline_ms"] for sample in samples]),
        "persisted_records": persisted,
        "statuses": counts,
        "scope": "warm single-process local latency; WP1 includes decode, detection and warp/deskew; pipeline includes decode, WP1-WP4, crop/glyph writes and SQLite, excluding HTTP/upload; original test has no OCR text labels, so statuses are not accuracy",
        "samples": samples,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "samples"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("split", type=Path, nargs="?", default=ROOT / "Vietnam License Plate.v2i.coco/test")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/local_latency.json")
    arguments = parser.parse_args()
    benchmark(arguments.split, arguments.output)
