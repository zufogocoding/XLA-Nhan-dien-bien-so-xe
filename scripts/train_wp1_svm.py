"""Train a HOG+SVM re-ranker for WP1 plate candidates.

Positives: GT plate crops from the train split.
Negatives: (a) hard negatives = heuristic detector FPs on train,
           (b) random crops that don't overlap any GT box.

Saves a calibrated LinearSVC to models/wp1_svm.pkl.
"""
import argparse, json, time
from pathlib import Path
from collections import defaultdict

import cv2
import joblib
import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.svm import LinearSVC

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.detection import find_candidates, _iou
from src.hog import hog_features as _hog, crop_features as _cf

WIN = (64, 32)  # (width, height)


def hog_features(img_bgr: np.ndarray) -> np.ndarray:
    return np.concatenate([_hog(img_bgr), _cf(img_bgr)])


def load_split(split_dir: Path):
    data = json.loads((split_dir / "_annotations.coco.json").read_text())
    by_image = defaultdict(list)
    for ann in data["annotations"]:
        x, y, w, h = ann["bbox"]
        by_image[ann["image_id"]].append((x, y, x + w, y + h))
    return data, by_image


def collect_positives(split_dir: Path, by_image, limit=None):
    data = json.loads((split_dir / "_annotations.coco.json").read_text())
    feats = []
    for item in data["images"][:limit]:
        img = cv2.imdecode(np.fromfile(split_dir / item["file_name"], dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        for (x1, y1, x2, y2) in by_image[item["id"]]:
            crop = img[int(y1):int(y2), int(x1):int(x2)]
            if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 8:
                continue
            feats.append(hog_features(crop))
    return np.asarray(feats)


def collect_hard_negatives(split_dir: Path, by_image, max_per_image=5, limit=None):
    data = json.loads((split_dir / "_annotations.coco.json").read_text())
    feats = []
    for item in data["images"][:limit]:
        img = cv2.imdecode(np.fromfile(split_dir / item["file_name"], dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        gt = by_image[item["id"]]
        try:
            cands = find_candidates(img, max_candidates=10)
        except Exception:
            continue
        for c in cands:
            x1, y1, x2, y2 = c.bbox
            if any(_iou(c.bbox, g) >= 0.5 for g in gt):
                continue
            crop = img[y1:y2, x1:x2]
            if crop.size == 0 or crop.shape[0] < 8 or crop.shape[1] < 8:
                continue
            feats.append(hog_features(crop))
            if len(feats) >= max_per_image * (limit or len(data["images"])):
                break
    return np.asarray(feats)


def collect_random_negatives(split_dir: Path, by_image, n, rng):
    data = json.loads((split_dir / "_annotations.coco.json").read_text())
    feats = []
    tries = 0
    while len(feats) < n and tries < n * 20:
        tries += 1
        item = data["images"][rng.integers(0, len(data["images"]))]
        img = cv2.imdecode(np.fromfile(split_dir / item["file_name"], dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue
        H, W = img.shape[:2]
        bw = int(rng.integers(40, 200)); bh = int(rng.integers(15, 80))
        x = int(rng.integers(0, max(1, W - bw))); y = int(rng.integers(0, max(1, H - bh)))
        # reject if overlaps GT
        box = (x, y, x + bw, y + bh)
        gt = by_image[item["id"]]
        if any(_iou(box, g) >= 0.3 for g in gt):
            continue
        crop = img[y:y + bh, x:x + bw]
        if crop.size == 0:
            continue
        feats.append(hog_features(crop))
    return np.asarray(feats)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("train_dir", type=Path)
    ap.add_argument("--out", type=Path, default=Path("models/wp1_svm.pkl"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--neg-ratio", type=float, default=2.0)
    args = ap.parse_args()

    rng = np.random.default_rng(42)
    data, by_image = load_split(args.train_dir)

    print("collecting positives...")
    Xp = collect_positives(args.train_dir, by_image, args.limit)
    print(f"  positives: {len(Xp)}")

    print("collecting hard negatives...")
    Xh = collect_hard_negatives(args.train_dir, by_image, limit=args.limit)
    print(f"  hard negatives: {len(Xh)}")

    n_rand = max(0, int(len(Xp) * args.neg_ratio) - len(Xh))
    print(f"collecting {n_rand} random negatives...")
    Xr = collect_random_negatives(args.train_dir, by_image, n_rand, rng)
    print(f"  random negatives: {len(Xr)}")

    if len(Xh) and len(Xr):
        Xn = np.concatenate([Xh, Xr], axis=0)
    elif len(Xh):
        Xn = Xh
    else:
        Xn = Xr
    # balance
    if len(Xn) > len(Xp) * args.neg_ratio:
        idx = rng.choice(len(Xn), int(len(Xp) * args.neg_ratio), replace=False)
        Xn = Xn[idx]

    X = np.concatenate([Xp, Xn], axis=0)
    y = np.concatenate([np.ones(len(Xp)), np.zeros(len(Xn))])

    print(f"training on {len(X)} samples (pos={len(Xp)}, neg={len(Xn)})...")
    base = LinearSVC(C=1.0, class_weight="balanced", max_iter=5000, random_state=42)
    clf = CalibratedClassifierCV(base, cv=3, method="sigmoid")
    t0 = time.time()
    clf.fit(X, y)
    print(f"  done in {time.time()-t0:.1f}s")

    # quick valid-set sanity if available
    args.out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": clf, "win": WIN}, args.out)
    print(f"saved {args.out}")


if __name__ == "__main__":
    main()
