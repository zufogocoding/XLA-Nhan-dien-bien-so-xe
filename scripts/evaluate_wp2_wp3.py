"""Evaluate segmentation and OCR on held-out annotated plate crops, not full scenes."""

import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
from time import perf_counter

import cv2
import numpy as np
from sklearn.metrics import accuracy_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.character_classifier import CharacterClassifier
from src.plate_reader import read_plate


def edit_distance(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, left in enumerate(a, 1):
        current = [i]
        for j, right in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def ground_truth_lines(characters: list[dict]) -> list[list[dict]]:
    typical_height = float(np.median([item["bbox"][3] for item in characters]))
    lines = []
    for item in sorted(characters, key=lambda c: c["bbox"][1] + c["bbox"][3] / 2):
        center = item["bbox"][1] + item["bbox"][3] / 2
        if not lines or center - np.mean([c["bbox"][1] + c["bbox"][3] / 2 for c in lines[-1]]) > 0.65 * typical_height:
            lines.append([])
        lines[-1].append(item)
    return [sorted(line, key=lambda c: c["bbox"][0]) for line in lines]


def box_iou(a, b):
    x, y = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    overlap = max(0, right - x) * max(0, bottom - y)
    return overlap / max(1, a[2] * a[3] + b[2] * b[3] - overlap)


def evaluate(data: Path, models: Path, reports: Path):
    manifest = json.loads((models / "ocr_manifest.json").read_text(encoding="utf-8"))
    classifier = CharacterClassifier(models / manifest["artifact"])
    plates = [item for item in json.loads((data / "plates.json").read_text(encoding="utf-8")) if item["split"] == "test" and not item["font_chart"]]
    tp, fp, total, line_correct, eligible_lines, exact, edits, total_chars = 0, 0, 0, 0, 0, 0, 0, 0
    durations, failures = [], []
    for item in plates:
        image = cv2.imdecode(np.fromfile(item["image_path"],np.uint8),cv2.IMREAD_COLOR)
        start = perf_counter()
        segmentation = read_plate(image, classifier)
        durations.append((perf_counter() - start) * 1000)
        ground = item["characters"]
        matched = set()
        for box in segmentation["positions"]:
            overlap, index = max(((box_iou(box, char["bbox"]), i) for i, char in enumerate(ground) if i not in matched), default=(0, -1))
            if overlap >= 0.5:
                matched.add(index)
        tp += len(matched)
        fp += len(segmentation["positions"]) - len(matched)
        total += len(ground)
        lines = ground_truth_lines(ground)
        if len(lines) <= 2:
            eligible_lines += 1
            line_correct += len(segmentation["line_ranges"]) == len(lines)
        expected = "".join(char["char"] for line in lines for char in line)
        prediction = segmentation['ocr']['raw_text']
        exact += prediction == expected
        edits += edit_distance(expected, prediction)
        total_chars += len(expected)
        if prediction != expected:
            failures.append({"image":item["source_image"],"expected":expected,"predicted":prediction,"matched_characters":len(matched),"gt_characters":len(ground)})
    summary = {"images":len(plates),"gt_characters":total,"matched_characters":tp,"false_proposals":fp,"segmentation_accuracy_at_iou_0_5":tp/total,"segmentation_precision":tp/(tp+fp) if tp+fp else 0,"line_count_accuracy":line_correct/eligible_lines,"line_count_images":eligible_lines,"excluded_more_than_two_lines":len(plates)-eligible_lines,"mean_wp2_wp3_ms":float(np.mean(durations)),"sequence_accuracy":exact/len(plates),"cer":edits/total_chars,"wer_one_token_per_plate":1-exact/len(plates),"model":manifest["artifact"],"scope":"held-out annotated plate crops; WP1/full-scene detection not included; mixed-country source; HOG/SVM selects threshold hypothesis","line_labels":"derived from GT box centers with 0.65*median-height clustering, not manual line annotations","sample_failures":failures[:30]}
    (reports / "wp2_wp3_plate_metrics.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding="utf-8")
    (reports / "wp2_evaluation.md").write_text(f"""# WP2 evaluation

Held-out source plate crops: {len(plates)} images, {total} labeled characters.
Segmentation accuracy (matched GT boxes / GT boxes, IoU ≥ 0.5): **{tp/total:.4f}**.
Proposal precision: **{summary['segmentation_precision']:.4f}**.
Derived line-count accuracy: **{summary['line_count_accuracy']:.4f}** ({eligible_lines} eligible images).
Mean threshold selection + OCR time: {summary['mean_wp2_wp3_ms']:.2f} ms.
All returned normalized character images use 32×32 pixels.

Line count is derived from annotated glyph geometry, not independently labeled lines.
Multi-line layouts beyond two lines are counted separately. Source images are cropped
plates without a labeled perspective rectification. This is a mixed-source baseline;
do not interpret it as validation of WP1 or all Vietnamese traffic scenes.

Targets: segmentation ≥ 0.90, line separation ≥ 0.95. A line-count check does not
certify that every split boundary is correct. Raw data and failure cases:
[wp2_wp3_plate_metrics.json](wp2_wp3_plate_metrics.json).
""",encoding="utf-8")
    (reports / "wp3_sequence_evaluation.md").write_text(f"""# WP3 sequence evaluation

WP2 segmentation + selected OCR on {len(plates)} held-out plate crops:

| Metric | Result | Brief target |
|---|---:|---:|
| Exact sequence accuracy | {summary['sequence_accuracy']:.4f} | ≥ 0.75 |
| CER | {summary['cer']:.4f} | ≤ 0.15 |
| WER (one plate = one token) | {summary['wer_one_token_per_plate']:.4f} | ≤ 0.20 |

Ground-truth reading order is derived from box geometry; the source has no separate
manually transcribed line-order file. Punctuation is excluded. WP1 and WP4 are not
included, and these mixed-country cropped plates do not establish full-scene
Vietnamese end-to-end accuracy.
""",encoding="utf-8")
    rows = [row for row in csv.DictReader((data / "labels.csv").open(encoding="utf-8")) if row["split"] == "test"]
    images = [cv2.imdecode(np.fromfile(data / row["image_path"],np.uint8),cv2.IMREAD_GRAYSCALE) for row in rows]
    expected = [row["label"] for row in rows]
    def rotate(image):
        matrix=cv2.getRotationMatrix2D((15.5,15.5),15,1)
        return cv2.warpAffine(image,matrix,(32,32))
    def occlude(image):
        result=image.copy(); result[10:18,12:20]=0; return result
    perturbations = {"clean":lambda image:image,"rotation_15_degrees":rotate,"gaussian_blur_3x3":lambda image:cv2.GaussianBlur(image,(3,3),0),"dark_contrast_0_5":lambda image:(image.astype(np.float32)*0.5).astype(np.uint8),"central_8x8_occlusion":occlude}
    robustness = {}
    for name, transform in perturbations.items():
        perturbed = [transform(image) for image in images]
        predicted = [item["char"] for item in classifier.predict(perturbed)]
        robustness[name] = float(accuracy_score(expected,predicted))
    start = perf_counter()
    for image in images[:100]:
        classifier.predict([image])
    robustness["mean_single_character_feature_and_classifier_ms_100_samples"]=(perf_counter()-start)*10
    (reports / "wp3_robustness.json").write_text(json.dumps(robustness,indent=2)+'\n',encoding="utf-8")
    lines=["# WP3 controlled robustness check","","Synthetic perturbations of held-out GT character crops, not new independently collected adverse-condition scenes.","","| Condition | Character accuracy |","|---|---:|"]
    lines += [f"| {name} | {value:.4f} |" for name,value in robustness.items() if name != "mean_single_character_feature_and_classifier_ms_100_samples"]
    lines += ["",f"Mean single-character feature extraction + classification: {robustness['mean_single_character_feature_and_classifier_ms_100_samples']:.3f} ms over 100 crops. This is not full-scene latency.","","Glare, backlighting, motion blur and natural occlusion still require independently labeled evaluation data."]
    (reports / "wp3_robustness.md").write_text('\n'.join(lines)+'\n',encoding="utf-8")
    print(json.dumps({key:value for key,value in summary.items() if key!='sample_failures'},indent=2),flush=True)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--data",type=Path,default=Path("data"))
    parser.add_argument("--models",type=Path,default=Path("models"))
    parser.add_argument("--reports",type=Path,default=Path("reports"))
    args=parser.parse_args()
    evaluate(args.data,args.models,args.reports)
