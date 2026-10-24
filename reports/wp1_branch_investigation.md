# WP1 branch comparison and regression fix — 24 October 2026

Standalone WP1 now produces **exactly the same 169 output boxes** as
`origin/wp1/fix-char-density-deskew`, commit
`ed80c5e736fc8b110e5c1785cbb3189ef34f3e98`. The integration had changed the
default WP1 selection algorithm, causing a real accuracy and latency regression.
The app's OCR-assisted box score had also been presented too prominently as
the WP1 result. Both the interface and the documentation are corrected.

## Controlled comparison

All runs use the same 169 COCO test images / 172 ground-truth boxes, original
WP1 SVM, one output box per image and IoU ≥0.5. Runs are sequential, in fresh
processes, with one OpenCV thread and one excluded warmup image. Timings include
file read/decode; standalone also includes normalization/warp/deskew. Application
timings include segmentation/OCR selection, and exclude HTTP, upload, image
artifact writes and SQLite. Timing differences between separate runs include
normal machine variation; accuracy is compared per image.

| Mode | TP / FP / FN | Precision | Recall | F1 | Mean ms |
|---|---|---:|---:|---:|---:|
| Original WP1 branch | 124 / 17 / 48 | 0.8794 | 0.7209 | 0.7923 | 189.3 |
| Integrated default before this fix | 116 / 45 / 56 | 0.7205 | 0.6744 | 0.6967 | 1321.3 |
| Restored standalone WP1 | 124 / 17 / 48 | 0.8794 | 0.7209 | 0.7923 | 179.7 |
| Application before optimization, same controls | 138 / 23 / 34 | 0.8571 | 0.8023 | 0.8288 | 2669.1 |
| Explicit application selector | 138 / 23 / 34 | 0.8571 | 0.8023 | 0.8288 | 1658.9 |

Raw reports: [original branch](wp1_branch_baseline.json),
[before fix](wp1_before_contract_fix.json),
[restored WP1](wp1_restored_standalone.json),
[application before optimization](wp1_application_before_optimization.json),
[application after optimization](wp1_application_selector.json),
[equivalence/provenance checks](wp1_audit_checks.json).

The original and restored standalone results match box-for-box, including
images with no detection. Their dataset, model and environment fingerprints
match. Standalone WP1 meets Precision ≥0.85, but still misses Recall ≥0.80
and F1 ≥0.82, just as the reference branch does. Its mean is below 200 ms;
P95 is 298.1 ms and maximum 356.3 ms, so this is not a per-image guarantee.

## Root cause and fix

The WP1 branch's `detect_plate()` selected the first ranked detector proposal.
The earlier uncommitted WP1–WP4 integration on top of `36f1271` replaced that
default with six detector proposals plus aligned-character proposals, multiple
WP2 segmentation hypotheses and geometric reranking. Without a supplied OCR
classifier, a region with a good geometric segmentation score could replace
the original plate. This changed both standalone output and computational cost.
The full app supplied OCR and performed another reranking, so its score
was measuring a different algorithm from standalone WP1's broken default.

`src/pipeline_wp1.py` now restores the original default proposal selection and
five-field return contract. It does not invoke WP2 or load OCR by default.
`src/recognition_selection.py` contains the explicit application selector;
the service and full-scene application evaluator call it directly. The optional
`classifier` keyword on `detect_plate_image` forwards to this selector for
compatibility. No model was retrained and no evaluation labels were changed.

The reference branch and the current starting HEAD have identical Git blobs
for `evaluate_wp1.py`, the test annotations and `models/wp1_svm.pkl`. Detector
changes only expose area limits with unchanged defaults; optional joblib import
handling does not change behavior when joblib is installed. A separate deskew
angle normalization fix affects crop geometry, not which detection box wins.
The data and WP1 model therefore do not explain the standalone F1 regression.

## Runtime investigation

A 12-image profile identified `merge_vertical_fragments` as a major hotspot:
42.76 of 66 profiled seconds were spent in repeated pair scans while repairing
broken glyphs in noisy segmentation masks. Profiler timings are diagnostic,
not latency benchmarks. NumPy now screens pairs for dense component lists,
preserving the first compatible pair, integer unions and greedy merge order;
small lists retain the scalar implementation.

The optimized merge matched the original function exactly on 140 generated
fragment cases. Regression tests protect both the independent WP1 contract
and dense fragment repair. Full test suite: **53 passed**, with one existing
TestClient/httpx deprecation warning. JavaScript syntax and Git whitespace
checks also pass. The full application comparison matches **all 169 boxes
and raw OCR strings** between the archived pre-fix integration and the
optimized application. Data, WP1 model and environment fingerprints match.
The observed application mean was 2669.1 ms before and 1658.9 ms after;
these sequential runs are subject to machine variation and are not a fixed
speedup guarantee.

The previous [application report](image_processing_fullscene.json), F1 0.8408,
differs on four images from the controlled current run (two lost true-positive
boxes). Both the original scalar merge and optimized merge produce the current
outputs on these cases, at OpenCV thread counts 1 and 16. Loading the original
pre-fix selector also reproduces the current outputs. This rules out the merge
optimization and selector extraction as the cause on those cases. The old
report lacks source/environment fingerprints; its exact cause is unresolved,
so it is retained as historical evidence and replaced by the current F1 0.8288.
The app still misses the one-second target: mean 1658.9 ms, median 1154.2 ms,
P95 4776.9 ms, maximum 10062.3 ms before HTTP/artifact writes/SQLite.

## Reproduce

Run from the project root using the checked-in runtime models and the COCO
dataset. Run benchmarks sequentially, without an upload/video job in parallel.

```powershell
New-Item -ItemType Directory -Force outputs/wp1-reference | Out-Null
git archive origin/wp1/fix-char-density-deskew src -o outputs/wp1-reference.tar
tar -xf outputs/wp1-reference.tar -C outputs/wp1-reference
.\.venv\Scripts\python.exe scripts/benchmark_wp1.py --mode standalone --source-root outputs/wp1-reference --label reference --output outputs/reference.json
.\.venv\Scripts\python.exe scripts/benchmark_wp1.py --mode standalone --label restored --output outputs/restored.json
.\.venv\Scripts\python.exe scripts/benchmark_wp1.py --mode application --label application --output outputs/application.json
```

Use `--mode detector` to measure detector-only output with the same timing
controls. The older `evaluate_wp1.py` timing only surrounds `find_candidates`;
its 145.8 ms result must not be compared directly with full WP1/app timings.
The before-fix run used a local source snapshot of the uncommitted integration,
not a remote commit. Its report includes a source fingerprint for provenance.

Shared fingerprints (SHA256):

- Test annotations: `dad11262f47afecf8fbd7a1c95d3db3b1e9b25c69f0c3c136b4ecfa0a4e2066f`.
- Ordered image names and bytes: `cfef22f1c32cbc1023473b4eeb82e60f193536fe4158045eb99a137f9f6c2ee6`.
- WP1 artifact: `5af589b10e2f3dbfa714871696e5e0060f5ef84e43655b4b8e272e1945e67332`.
- Selected OCR artifact (`svm_hog_lbp.pkl`): `9e8445d7fc5a2a824e7dcb3a7eadf4dbf6466308afdcfac1ca84d251af5ff4af`.

Environment: Python 3.12.14, OpenCV 5.0.0, NumPy 2.5.4,
scikit-learn 1.8.0, Windows 11. Full source hashes and per-image predictions
are in each JSON report.

## What the scores mean

F1 0.8288 is **application plate-box localization**, using WP2–WP4 evidence.
The COCO test has no text labels, so it cannot measure full-scene OCR accuracy.
The unchanged 96.53% character accuracy uses ground-truth character crops.
The 69.46% complete-string accuracy / 9.36% CER uses 478 plate crops from the
separate OCR test split. These are three different tasks and populations;
none proves the project's full-scene reading target has been met.

Runtime data and user diagnostics remain local; necessary runtime models and
reproducible reports are committed. See [artifact policy](artifact_policy.md).
Docker remains unverified following the user's instruction to stop its repair.
