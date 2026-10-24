# Local artifacts and Git hygiene

Git includes application source, tests, reproducible benchmark results,
comparison reports, and the two OCR artifacts needed by the runtime/Python API.
The existing WP1 model is unchanged. See `models/README.md` for model scope.

The following stay on the local machine and are intentionally ignored:

- `.venv`, caches, `.env` files, uploads, SQLite databases, logs and `outputs/`.
- Downloaded OCR/video sources, prepared character crops and label manifests.
- User-upload screenshots, before/after contact sheets and smoke responses
  containing local paths, record IDs and runtime image URLs.
- Generated `demo/video_demo.mp4` and the non-runtime kNN/RF/LBP experiments.

Nothing was deleted locally when these artifacts were removed from staging.
The COCO dataset already tracked on the upstream branches is left intact;
an ignore rule prevents additional copies from being added but does not
rewrite its existing history.

References to ignored screenshots/video in older reports are marked as
local artifacts. For reproducible shared measurements, use the checked-in
WP1 branch audit and `scripts/benchmark_wp1.py`, rather than local smoke files.
