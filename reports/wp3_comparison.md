# WP3 classifier baseline

User-approved winter2897 VOC data; 32×32 normalized characters. Source-image groups remain disjoint; the font chart is training-only. O/Q/W have extremely limited support. Full 36-class generalization is not established.

Model selection: validation macro F1; test scores are reported after selection. CV is grouped by source image. Near-duplicate/identity leakage cannot be excluded without identity labels.

| Model | Feature dimensions | Valid accuracy | Test accuracy | Test macro F1 (36) | Train s | Classifier batch ms/char |
|---|---:|---:|---:|---:|---:|---:|
| svm_hog | 324 | 0.9676 | 0.9650 | 0.8434 | 243.5 | 1.2247 |
| svm_lbp | 10 | 0.4138 | 0.3965 | 0.1088 | 356.4 | 1.5046 |
| svm_hog_lbp | 334 | 0.9681 | 0.9653 | 0.8484 | 267.6 | 1.1785 |
| knn | 324 | 0.9561 | 0.9559 | 0.8095 | 6.4 | 0.1732 |
| rf | 324 | 0.9522 | 0.9562 | 0.8077 | 311.3 | 0.0729 |

Selected artifact: `svm_hog_lbp.pkl`.

Timing is batched classifier inference on precomputed features. It excludes feature extraction and is not end-to-end latency. Character accuracy on GT crops does not establish sequence accuracy or WP4 end-to-end accuracy.

At 32×32, 8×8 cells and 2×2-cell blocks produce 3×3×4×9 = **324 HOG features**. The approximate dimension in the original brief does not match this geometry. Uniform LBP contributes 10 features; HOG+LBP has 334.
