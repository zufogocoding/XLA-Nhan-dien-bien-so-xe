"""Reproducible, single-worker localization benchmark with explicit scope.

--source-root can point to an exported branch to compare the same data/models
without switching the active checkout. Labels are used only after inference.
"""

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import platform
import sys
from time import perf_counter

import cv2
import numpy as np
import sklearn

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('detector', 'standalone', 'application'), default='standalone')
    parser.add_argument('--source-root', type=Path, default=ROOT)
    parser.add_argument('--legacy-application', action='store_true',
                        help='benchmark an archived integration via detect_plate_image(..., classifier=...)')
    parser.add_argument('--split', type=Path, default=ROOT / 'Vietnam License Plate.v2i.coco/test')
    parser.add_argument('--label', default='working tree')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--limit', type=int)
    args = parser.parse_args()
    if args.threads < 1:
        parser.error('--threads must be positive')
    if args.legacy_application and args.mode != 'application':
        parser.error('--legacy-application requires --mode application')
    if Path.cwd().resolve() != ROOT:
        parser.error('run from the project root so archived WP1 uses the same runtime model')
    sys.path.insert(0, str(args.source_root.resolve()))
    from src.detection import find_candidates, _iou
    from src.pipeline_wp1 import detect_plate
    from src import reclassifier

    if reclassifier._load() is None:
        raise RuntimeError('WP1 SVM must load; refusing to benchmark a silent heuristic fallback')

    cv2.setNumThreads(args.threads)
    classifier = None
    if args.mode == 'application':
        from src.character_classifier import CharacterClassifier
        if args.legacy_application:
            from src.pipeline_wp1 import detect_plate_image
        else:
            from src.recognition_selection import select_plate_for_recognition
        manifest = json.loads((ROOT / 'models/ocr_manifest.json').read_text(encoding='utf-8'))
        classifier = CharacterClassifier(ROOT / 'models' / manifest['artifact'])
        classifier.load()

    annotation_path = args.split / '_annotations.coco.json'
    annotation_bytes = annotation_path.read_bytes()
    data = json.loads(annotation_bytes)
    ground = defaultdict(list)
    for annotation in data['annotations']:
        x, y, width, height = annotation['bbox']
        ground[annotation['image_id']].append((x, y, x + width, y + height))
    images = data['images'][:args.limit]
    if not images:
        raise ValueError('no benchmark images')

    def infer(item):
        path = args.split / item['file_name']
        if args.mode == 'standalone':
            result = detect_plate(path)
            return (result['bbox'] if result else None), None
        image = cv2.imdecode(np.fromfile(path, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f'unreadable image: {path}')
        if args.mode == 'detector':
            candidates = find_candidates(image, max_candidates=1)
            return (list(candidates[0].bbox) if candidates else None), None
        result = (detect_plate_image(image, classifier=classifier) if args.legacy_application
                  else select_plate_for_recognition(image, classifier))
        return (result['bbox'], result['ocr']['raw_text']) if result else (None, None)

    start = perf_counter()
    infer(images[0])  # same warmup, excluded from all per-image timings
    warmup_ms = (perf_counter() - start) * 1000
    cases = []
    tp = fp = fn = 0
    image_hash = hashlib.sha256()
    for index, item in enumerate(images):
        start = perf_counter()
        box, raw_text = infer(item)
        elapsed_ms = (perf_counter() - start) * 1000
        overlap = max((_iou(box, label) for label in ground[item['id']]), default=0.) if box else 0.
        matched = int(overlap >= .5)
        tp += matched
        fp += int(box is not None) - matched
        fn += len(ground[item['id']]) - matched
        case = {'file': item['file_name'], 'bbox': box, 'best_iou': overlap, 'ms': elapsed_ms}
        if args.mode == 'application':
            case['raw_text'] = raw_text
        cases.append(case)
        image_hash.update(item['file_name'].encode('utf-8'))
        image_hash.update((args.split / item['file_name']).read_bytes())
        if (index + 1) % 25 == 0:
            print(f'{args.label}: {index+1}/{len(images)}', flush=True)
    precision = tp / (tp + fp) if tp + fp else 0.
    recall = tp / (tp + fn) if tp + fn else 0.
    timings = [case['ms'] for case in cases]
    source_hash = hashlib.sha256()
    for path in sorted((args.source_root / 'src').glob('*.py')):
        source_hash.update(path.name.encode())
        source_hash.update(path.read_bytes())
    report = {
        'label': args.label, 'mode': args.mode, 'images': len(images),
        'gt_boxes': tp + fn, 'tp': tp, 'fp': fp, 'fn': fn,
        'precision': precision, 'recall': recall,
        'f1': 2 * precision * recall / (precision + recall) if precision + recall else 0.,
        'mean_ms': float(np.mean(timings)), 'median_ms': float(np.median(timings)),
        'p95_ms': float(np.percentile(timings, 95)), 'max_ms': float(np.max(timings)),
        'warmup_ms': warmup_ms, 'iou_threshold': .5, 'max_output_boxes': 1,
        'annotation_sha256': hashlib.sha256(annotation_bytes).hexdigest(),
        'images_sha256': image_hash.hexdigest(), 'source_sha256': source_hash.hexdigest(),
        'wp1_model_sha256': hashlib.sha256((ROOT / 'models/wp1_svm.pkl').read_bytes()).hexdigest(),
        'ocr_model_sha256': hashlib.sha256(classifier.model_path.read_bytes()).hexdigest() if classifier else None,
        'environment': {'python': platform.python_version(), 'opencv': cv2.__version__,
                        'opencv_threads': cv2.getNumThreads(), 'numpy': np.__version__,
                        'sklearn': sklearn.__version__, 'platform': platform.platform()},
        'scope': 'warm sequential localization, one box/image, IoU >= .5; includes disk read/decode; application includes segmentation/OCR candidate selection; excludes HTTP/upload/SQLite; no full-scene text labels',
        'cases': cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'cases'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
