"""Train and compare the five supervised WP3 baselines on prepared 32x32 data."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

import cv2
import joblib
import numpy as np
import sklearn
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.character_classifier import extract_features

ALPHABET = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def metrics(actual, predicted):
    precision, recall, f1, support = precision_recall_fscore_support(actual, predicted, labels=ALPHABET, zero_division=0)
    return {
        "accuracy": float(accuracy_score(actual, predicted)),
        "macro_precision_36": float(precision.mean()), "macro_recall_36": float(recall.mean()),
        "macro_f1_36": float(f1.mean()),
        "observed_macro_f1": float(f1[support > 0].mean()),
        "per_class": {label: {"precision": float(p), "recall": float(r), "f1": float(f), "support": int(n)} for label, p, r, f, n in zip(ALPHABET, precision, recall, f1, support)},
        "confusion_matrix": confusion_matrix(actual, predicted, labels=ALPHABET).tolist(),
    }


def train(labels_path: Path, model_dir: Path, report_dir: Path) -> dict:
    rows = list(csv.DictReader(labels_path.open(encoding="utf-8")))
    if not rows or not all({"image_path", "label", "group_id", "split"} <= row.keys() for row in rows):
        raise ValueError("labels.csv needs image_path, label, group_id, split")
    for group in {row["group_id"] for row in rows}:
        if len({row["split"] for row in rows if row["group_id"] == group}) != 1:
            raise ValueError("source image leakage across data splits")
    labels = np.array([row["label"] for row in rows])
    groups = np.array([row["group_id"] for row in rows])
    masks = {split: np.array([row["split"] == split for row in rows]) for split in ("train", "valid", "test")}
    if any(not mask.any() for mask in masks.values()):
        raise ValueError("train, valid and test must all be nonempty")
    if set(labels[masks["train"]]) != set(ALPHABET):
        raise ValueError("baseline training must retain all 36 observed character classes")
    images = []
    for row in rows:
        image = cv2.imdecode(np.fromfile(labels_path.parent / row["image_path"], np.uint8), cv2.IMREAD_GRAYSCALE)
        if image is None or image.shape != (32, 32):
            raise ValueError(f"invalid prepared character: {row['image_path']}")
        images.append(image)
    feature_sets = {}
    for feature in ("hog", "lbp"):
        print(f"extracting {feature} features for {len(images)} characters", flush=True)
        feature_sets[feature] = np.stack([extract_features(image, feature) for image in images])
    feature_sets["hog_lbp"] = np.concatenate([feature_sets["hog"], feature_sets["lbp"]], axis=1)
    specifications = [
        ("svm_hog", "hog", SVC(kernel="rbf", class_weight="balanced", cache_size=512, random_state=42), {"C": [1, 10], "gamma": ["scale", 0.01]}),
        ("svm_lbp", "lbp", SVC(kernel="rbf", class_weight="balanced", cache_size=512, random_state=42), {"C": [1, 10], "gamma": ["scale", 0.01]}),
        ("svm_hog_lbp", "hog_lbp", SVC(kernel="rbf", class_weight="balanced", cache_size=512, random_state=42), {"C": [1, 10], "gamma": ["scale", 0.01]}),
        ("knn", "hog", KNeighborsClassifier(weights="distance"), {"n_neighbors": [3, 5, 7, 9]}),
        ("rf", "hog", RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=1), {"n_estimators": [100, 200], "max_depth": [None, 20]}),
    ]
    model_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    fingerprint = hashlib.sha256(labels_path.read_bytes()).hexdigest()
    results = {}
    for name, feature, estimator, parameters in specifications:
        print(f"training {name}: grouped 3-fold grid search", flush=True)
        matrix = feature_sets[feature]
        start = perf_counter()
        search = GridSearchCV(estimator, parameters, cv=GroupKFold(3), scoring="f1_macro", n_jobs=1, refit=True)
        search.fit(matrix[masks["train"]], labels[masks["train"]], groups=groups[masks["train"]])
        model = search.best_estimator_
        if isinstance(model, SVC):
            model = clone(model).set_params(probability=True)
            model.fit(matrix[masks["train"]], labels[masks["train"]])
        elapsed = perf_counter() - start
        bundle = {"task": "character_recognition", "character_size": 32, "feature": feature, "model": model, "data_sha256": fingerprint, "sklearn_version": sklearn.__version__, "model_version": f"wp3-{name}-{fingerprint[:12]}", "parameters": search.best_params_}
        joblib.dump(bundle, model_dir / f"{name}.pkl", compress=3)
        result = {"feature": feature, "features": int(matrix.shape[1]), "train_seconds": elapsed, "parameters": search.best_params_, "cv_macro_f1": float(search.best_score_)}
        for split in ("valid", "test"):
            start = perf_counter()
            probabilities = model.predict_proba(matrix[masks[split]])
            predicted = model.classes_[probabilities.argmax(axis=1)]
            elapsed_ms = (perf_counter() - start) * 1000
            result[split] = metrics(labels[masks[split]], predicted)
            result[split]["batch_classifier_ms_per_character"] = elapsed_ms / int(masks[split].sum())
        results[name] = result
        (report_dir / "wp3_training_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{name}: validation accuracy={result['valid']['accuracy']:.4f}; test accuracy={result['test']['accuracy']:.4f}", flush=True)
    selected = max(results, key=lambda name: results[name]["valid"]["macro_f1_36"])
    manifest = {"selected": selected, "artifact": f"{selected}.pkl", "selection": "maximum validation macro F1 over 36 classes; test unused for selection", "data_sha256": fingerprint, "character_size": 32}
    (model_dir / "ocr_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for name, result in results.items():
        matrix = np.array(result["test"]["confusion_matrix"])
        fig, ax = plt.subplots(figsize=(14, 12))
        plotted = ax.imshow(np.log1p(matrix), cmap="Blues")
        ax.set_xticks(range(36), ALPHABET)
        ax.set_yticks(range(36), ALPHABET)
        ax.set_xlabel("Predicted character")
        ax.set_ylabel("Ground truth")
        ax.set_title(f"{name} — held-out source images (color = log(1 + count))")
        for row, col in zip(*np.nonzero(matrix)):
            ax.text(col, row, str(matrix[row, col]), ha="center", va="center", fontsize=6, color="white" if matrix[row, col] > matrix.max() * 0.4 else "black")
        fig.colorbar(plotted, ax=ax)
        fig.tight_layout()
        fig.savefig(report_dir / f"wp3_confusion_{name}.png", dpi=150)
        if name == selected:
            fig.savefig(report_dir / "wp3_confusion_matrix.png", dpi=150)
        plt.close(fig)
    lines = ["# WP3 classifier baseline", "", "User-approved winter2897 VOC data; 32×32 normalized characters. Source-image groups remain disjoint; the font chart is training-only. O/Q/W have extremely limited support. Full 36-class generalization is not established.", "", "Model selection: validation macro F1; test scores are reported after selection. CV is grouped by source image. Near-duplicate/identity leakage cannot be excluded without identity labels.", "", "| Model | Feature dimensions | Valid accuracy | Test accuracy | Test macro F1 (36) | Train s | Classifier batch ms/char |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name, result in results.items():
        lines.append(f"| {name} | {result['features']} | {result['valid']['accuracy']:.4f} | {result['test']['accuracy']:.4f} | {result['test']['macro_f1_36']:.4f} | {result['train_seconds']:.1f} | {result['test']['batch_classifier_ms_per_character']:.4f} |")
    lines += ["", f"Selected artifact: `{selected}.pkl`.", "", "Timing is batched classifier inference on precomputed features. It excludes feature extraction and is not end-to-end latency. Character accuracy on GT crops does not establish sequence accuracy or WP4 end-to-end accuracy.", "", "At 32×32, 8×8 cells and 2×2-cell blocks produce 3×3×4×9 = **324 HOG features**. The approximate dimension in the original brief does not match this geometry. Uniform LBP contributes 10 features; HOG+LBP has 334."]
    (report_dir / "wp3_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (report_dir / "wp3_ablation.md").write_text("# WP3 feature ablation\n\nHOG, LBP and HOG+LBP use the same SVM family, grouped CV and fixed train/valid/test data. Results and selected hyperparameters: [comparison](wp3_comparison.md), [raw metrics](wp3_training_results.json).\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("labels", type=Path, nargs="?", default=Path("data/labels.csv"))
    parser.add_argument("--models", type=Path, default=Path("models"))
    parser.add_argument("--reports", type=Path, default=Path("reports"))
    args = parser.parse_args()
    print(json.dumps(train(args.labels, args.models, args.reports), indent=2))
