# WP3 controlled robustness check

Synthetic perturbations of held-out GT character crops, not new independently collected adverse-condition scenes.

| Condition | Character accuracy |
|---|---:|
| clean | 0.9653 |
| rotation_15_degrees | 0.7040 |
| gaussian_blur_3x3 | 0.9118 |
| dark_contrast_0_5 | 0.9653 |
| central_8x8_occlusion | 0.7267 |

Mean single-character feature extraction + classification: 4.647 ms over 100 crops. This is not full-scene latency.

Glare, backlighting, motion blur and natural occlusion still require independently labeled evaluation data.
