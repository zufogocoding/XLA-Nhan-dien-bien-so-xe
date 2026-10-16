# WP3 – TRÍCH XUẤT ĐẶC TRƯNG & PHÂN LOẠI KÝ TỰ

## 1. MỤC TIÊU
Từ ảnh ký tự → vector đặc trưng → nhãn ký tự (0-9, A-Z).

## 2. INPUT
- Danh sách ảnh ký tự từ WP2
- Format: `np.ndarray` (28×28 hoặc 32×32)

## 3. OUTPUT
- Chuỗi ký tự thô (raw text)
- Confidence score cho từng ký tự

## 4. INTERFACE
INPUT: characters (list[np.ndarray])
OUTPUT: {
"raw_text": "51F12345", # chuỗi ký tự thô
"confidences": [0.95, 0.87, ...],
"char_details": [
{"char": "5", "confidence": 0.95},
...
]
}

text

## 5. CÔNG VIỆC CHI TIẾT

### 5.1. Chuẩn bị dataset ký tự
- [ ] Thu thập ảnh ký tự 0-9, A-Z
- [ ] Gán nhãn: mỗi ảnh → 1 ký tự
- [ ] Chia train/val/test: 70/15/15
- [ ] Output: `data/characters/`, `data/labels.csv`

### 5.2. Trích xuất HOG
- [ ] Cài đặt: `skimage.feature.hog(img, orientations=9, pixels_per_cell=(8,8), cells_per_block=(2,2))`
- [ ] Hoặc tự cài đặt từ đầu
- [ ] Vector size: ~1764 chiều (với 28×28)
- [ ] Output: `src/feature_hog.py`

### 5.3. Trích xuất LBP
- [ ] Cài đặt: `skimage.feature.local_binary_pattern(img, P=8, R=1, method='uniform')`
- [ ] Histogram LBP: `np.histogram(lbp, bins=10)`
- [ ] Vector size: 10–59 chiều
- [ ] Output: `src/feature_lbp.py`

### 5.4. Train SVM
- [ ] SVM + HOG: `sklearn.svm.SVC(kernel='rbf', C=10, gamma='scale')`
- [ ] SVM + LBP: `sklearn.svm.SVC(kernel='rbf', C=10)`
- [ ] SVM + HOG+LBP: kết hợp 2 vector
- [ ] Grid search: C, gamma
- [ ] Output: `models/svm_hog.pkl`, `models/svm_lbp.pkl`

### 5.5. Train kNN
- [ ] `sklearn.neighbors.KNeighborsClassifier(n_neighbors=5)`
- [ ] Thử k = 3, 5, 7, 9
- [ ] Output: `models/knn.pkl`

### 5.6. Train Random Forest
- [ ] `sklearn.ensemble.RandomForestClassifier(n_estimators=100)`
- [ ] Grid search: n_estimators, max_depth
- [ ] Output: `models/rf.pkl`

### 5.7. So sánh classifier
- [ ] Bảng so sánh: SVM vs kNN vs RF
- [ ] Metrics: Accuracy, Precision, Recall, F1
- [ ] Thời gian train, thời gian inference
- [ ] Output: `reports/wp3_comparison.md`

### 5.8. Confusion matrix
- [ ] Vẽ confusion matrix cho từng classifier
- [ ] Phân tích cặp ký tự dễ nhầm
- [ ] Output: `reports/wp3_confusion_matrix.png`

### 5.9. Đánh giá robustness
- [ ] Test với ảnh nghiêng, mờ, che khuất
- [ ] Test với ảnh tối, ngược sáng
- [ ] Output: `reports/wp3_robustness.md`

### 5.10. Ablation study
- [ ] HOG only
- [ ] LBP only
- [ ] HOG + LBP
- [ ] Output: `reports/wp3_ablation.md`

### 5.11. Ghép chuỗi
- [ ] Sắp xếp ký tự theo thứ tự
- [ ] Xử lý dấu `-`, `.`
- [ ] Ghép 2 dòng
- [ ] Output: `src/sequence_builder.py`

## 6. LÝ THUYẾT CẦN NẮM
- HOG: chia cell → histogram gradient → chuẩn hóa block
- LBP: so sánh pixel trung tâm với 8 láng giềng → mã nhị phân
- SVM: hyperplane tối ưu, kernel trick
- kNN: phân loại dựa trên k láng giềng
- Random Forest: ensemble decision trees
- Cross-validation: K-fold
- Confusion matrix: TP, FP, FN, TN
- CER/WER: Character/Word Error Rate

## 7. TIÊU CHÍ ĐÁNH GIÁ
| Metric | Target |
|---|---|
| Accuracy (ký tự) | ≥ 0.85 |
| Accuracy (chuỗi) | ≥ 0.75 |
| CER | ≤ 0.15 |
| WER | ≤ 0.20 |
| Latency | ≤ 100ms/ký tự |

## 8. DEPENDENCIES
- Phụ thuộc WP2 (input: ảnh ký tự đã tách)
- Output cung cấp cho WP4

## 9. CẤU TRÚC CODE
src/
├── feature_hog.py
├── feature_lbp.py
├── classifier_svm.py
├── classifier_knn.py
├── classifier_rf.py
├── sequence_builder.py
└── pipeline_wp3.py
models/
├── svm_hog.pkl
├── svm_lbp.pkl
├── knn.pkl
└── rf.pkl
tests/
├── test_hog.py
├── test_lbp.py
└── test_classifier.py

text

## 10. TÀI LIỆU THAM KHẢO
- Dalal & Triggs (2005). HOG for Human Detection. CVPR.
- Ojala et al. (2002). LBP. TPAMI.
- Cortes & Vapnik (1995). SVM. Machine Learning.
- Cover & Hart (1967). kNN. IEEE IT.
- scikit-learn Docs: SVM, kNN, Random Forest

## 11. CHECKLIST HOÀN THÀNH
- [ ] Dataset ký tự đầy đủ (0-9, A-Z)
- [ ] Train xong 4 model: SVM+HOG, SVM+LBP, kNN, RF
- [ ] Accuracy ≥ 0.85
- [ ] Có báo cáo so sánh classifier
- [ ] Có confusion matrix
- [ ] Có tài liệu API cho WP4
