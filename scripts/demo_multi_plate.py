"""Demo: detect and read several license plates in one photo.

Example:
    python scripts/demo_multi_plate.py path/to/street.jpg
    python scripts/demo_multi_plate.py path/to/street.jpg --max-plates 12
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from time import perf_counter

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.character_classifier import CharacterClassifier
from src.multi_plate import annotate_plates, recognize_plates, summarize_plate


def load_classifier(model_dir: Path) -> CharacterClassifier:
    manifest_path = model_dir / "ocr_manifest.json"
    if manifest_path.exists():
        artifact = json.loads(manifest_path.read_text(encoding="utf-8"))["artifact"]
    else:
        artifact = "svm_hog.pkl"
    classifier = CharacterClassifier(model_dir / artifact)
    classifier.load()
    return classifier


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="photo that may contain several plates")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs" / "multi_plate")
    parser.add_argument("--model-dir", type=Path, default=ROOT / "models")
    parser.add_argument("--max-plates", type=int, default=10)
    parser.add_argument("--max-candidates", type=int, default=18)
    parser.add_argument("--no-tiles", action="store_true", help="skip tiled proposals for very large photos")
    parser.add_argument(
        "--text-regions",
        choices=("auto", "on", "off"),
        default="auto",
        help="aligned-character fallback: auto only when the contour detector finds nothing",
    )
    parser.add_argument("--vehicle-type", choices=("unknown", "car", "motorcycle"), default="unknown")
    args = parser.parse_args()
    if not args.image.is_file():
        parser.error("input image does not exist")

    image = cv2.imdecode(np.fromfile(args.image, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        parser.error("input image is not readable")

    text_regions = {"auto": None, "on": True, "off": False}[args.text_regions]
    start = perf_counter()
    plates = recognize_plates(
        image,
        load_classifier(args.model_dir),
        max_plates=args.max_plates,
        max_candidates=args.max_candidates,
        use_tiles=not args.no_tiles,
        include_text_regions=text_regions,
        vehicle_type=args.vehicle_type,
    )
    elapsed_ms = (perf_counter() - start) * 1000

    output_dir = args.output_dir / args.image.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    annotated_path = output_dir / "annotated.jpg"
    cv2.imencode(".jpg", annotate_plates(image, plates), [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tofile(annotated_path)
    for index, plate in enumerate(plates, 1):
        cv2.imencode(".png", plate["plate_crop"])[1].tofile(output_dir / f"plate_{index:02d}_crop.png")
        cv2.imencode(".png", plate["plate_normalized"])[1].tofile(output_dir / f"plate_{index:02d}_normalized.png")
    summaries = [summarize_plate(plate) for plate in plates]
    report = {
        "input": str(args.image),
        "image_size": [image.shape[1], image.shape[0]],
        "count": len(plates),
        "elapsed_ms": elapsed_ms,
        "annotated_image": str(annotated_path),
        "plates": summaries,
    }
    (output_dir / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Found {len(plates)} plate(s) in {image.shape[1]}x{image.shape[0]} px, {elapsed_ms:.0f} ms")
    for index, plate in enumerate(summaries, 1):
        state = "valid" if plate["is_valid"] else "review"
        print(
            f"  #{index} {plate['plate_text'] or plate['raw_text'] or '?':<16} "
            f"{state:<6} conf={plate['recognition_confidence']:.3f} "
            f"chars={plate['num_chars']} bbox={plate['bbox']}"
        )
    print(f"Annotated: {annotated_path}")
    print(f"JSON:      {output_dir / 'result.json'}")
    return 0 if plates else 2


if __name__ == "__main__":
    raise SystemExit(main())
