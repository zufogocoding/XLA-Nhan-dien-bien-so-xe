"""Import the user-approved winter2897 VOC archive without splitting plate groups."""

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

import cv2
import numpy as np
from sklearn.model_selection import GroupShuffleSplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.binarization import binarize
from src.normalize_character import normalize_character


def prepare(archive: Path, output: Path, seed: int = 42) -> dict:
    if (output / "labels.csv").exists():
        raise FileExistsError("labels.csv already exists; reuse the prepared data or choose a new output")
    output.mkdir(parents=True, exist_ok=True)
    characters = output / "characters"
    characters.mkdir(exist_ok=True)
    image_dir = archive.parent / "images"
    image_dir.mkdir(exist_ok=True)
    records, plates = [], []
    with zipfile.ZipFile(archive) as source:
        images = {Path(info.filename).name: info for info in source.infolist() if info.filename.lower().endswith((".jpg", ".jpeg", ".png"))}
        for info in source.infolist():
            if not info.filename.lower().endswith(".xml"):
                continue
            root = ET.fromstring(source.read(info))
            name = Path(root.findtext("filename")).name
            content = source.read(images[name])
            image = cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError(f"unreadable image: {name}")
            digest = hashlib.sha256(content).hexdigest()
            height, width = image.shape[:2]
            if (width, height) != (int(root.findtext("size/width")), int(root.findtext("size/height"))):
                raise ValueError(f"annotation/image size mismatch: {name}")
            (image_dir / name).write_bytes(content)
            ground_truth = []
            for index, obj in enumerate(root.findall("object")):
                label = obj.findtext("name")
                if label not in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ" or len(label) != 1:
                    raise ValueError(f"unsupported label: {label!r}")
                # VOC boxes are 1-based inclusive; convert once to half-open pixel coordinates.
                x1, y1, x2, y2 = [int(float(obj.findtext("bndbox/" + key))) for key in ("xmin", "ymin", "xmax", "ymax")]
                x1, y1 = max(0, x1 - 1), max(0, y1 - 1)
                x2, y2 = min(width, x2), min(height, y2)
                if x2 <= x1 or y2 <= y1:
                    raise ValueError(f"empty character box: {name}")
                glyph = normalize_character(binarize(image[y1:y2, x1:x2]))
                relative = Path("characters") / f"{digest[:16]}_{index:02d}_{label}.png"
                ok, encoded = cv2.imencode(".png", glyph)
                if not ok:
                    raise ValueError(f"cannot encode character: {name}")
                encoded.tofile(output / relative)
                records.append({"image_path": relative.as_posix(), "label": label, "group_id": digest, "source_image": name})
                ground_truth.append({"char": label, "bbox": [x1, y1, x2 - x1, y2 - y1]})
            plates.append({"image_path": str((image_dir / name).resolve()), "source_image": name, "group_id": digest, "characters": ground_truth, "font_chart": name == "0.jpg"})
    groups = np.array(sorted({record["group_id"] for record in records}))
    train_indices, rest_indices = next(GroupShuffleSplit(n_splits=1, train_size=0.7, random_state=seed).split(groups, groups=groups))
    rest = groups[rest_indices]
    valid_indices, test_indices = next(GroupShuffleSplit(n_splits=1, train_size=0.5, random_state=seed + 1).split(rest, groups=rest))
    assignment = {str(group): "train" for group in groups[train_indices]}
    assignment.update({str(group): "valid" for group in rest[valid_indices]})
    assignment.update({str(group): "test" for group in rest[test_indices]})
    # The font chart is supplemental training material, never real-plate evaluation data.
    for plate in plates:
        if plate["font_chart"]:
            assignment[plate["group_id"]] = "train"
    # Preserve all observed classes in training. Rare classes may lack independent test support.
    for label in sorted({record["label"] for record in records}):
        eligible = sorted({r["group_id"] for r in records if r["label"] == label})
        if not any(assignment[group] == "train" for group in eligible):
            assignment[eligible[0]] = "train"
    for record in records:
        record["split"] = assignment[record["group_id"]]
    for plate in plates:
        plate["split"] = assignment[plate["group_id"]]
    with (output / "labels.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["image_path", "label", "group_id", "source_image", "split"])
        writer.writeheader()
        writer.writerows(records)
    (output / "plates.json").write_text(json.dumps(plates, ensure_ascii=False, indent=2), encoding="utf-8")
    report = {
        "source": str(archive), "seed": seed, "character_size": 32,
        "split_unit": "source image SHA256; no character from one image crosses splits",
        "voc_coordinates": "1-based inclusive converted to half-open; zero minima clipped",
        "font_chart": "0.jpg is train-only",
        "counts": {split: dict(sorted(Counter(r["label"] for r in records if r["split"] == split).items())) for split in ("train", "valid", "test")},
        "images_per_split": dict(Counter(assignment.values())),
        "characters_per_split": dict(Counter(r["split"] for r in records)),
        "limitations": ["Near-duplicate images/plate identities are not labeled; splitting is by exact source image only.", "Rare O/Q/W classes do not support reliable independent per-class evaluation.", "Dataset includes non-Vietnamese plates and a font chart; results are a mixed-source baseline."],
    }
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data"))
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    report = prepare(args.archive, args.output, args.seed)
    Path("reports/wp3_data_preparation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))
