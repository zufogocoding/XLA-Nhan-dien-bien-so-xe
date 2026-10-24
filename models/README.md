# Model artifacts

The repository includes the models needed to run a fresh checkout:

| File | Purpose |
|---|---|
| `wp1_svm.pkl` | Existing binary plate/background re-ranker; unchanged |
| `svm_hog_lbp.pkl` | Selected OCR model used by `ocr_manifest.json` |
| `svm_hog.pkl` | Default model of the standalone WP3 Python interface |

`knn.pkl`, `rf.pkl` and `svm_lbp.pkl` are local experiment outputs, ignored by
Git. Their comparison metrics and confusion matrices remain in `reports/`;
`scripts/train_wp3.py` regenerates them from the prepared labeled dataset.
The files already trained on this machine are retained locally.

No model was retrained for the WP1 branch investigation. The benchmark
reports record the WP1 artifact SHA256 and dataset fingerprints.
