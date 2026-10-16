# WP2 – CHUẨN HÓA & TÁCH KÝ TỰ

## 1. MỤC TIÊU
Từ ảnh biển số → tách từng ký tự riêng biệt, chuẩn hóa về cùng kích thước.

## 2. INPUT
- Ảnh biển số đã cắt từ WP1
- Format: `np.ndarray` (BGR hoặc grayscale)

## 3. OUTPUT
- Danh sách ảnh ký tự đã tách, đã chuẩn hóa
- Thứ tự ký tự: trái → phải, trên → dưới
- Metadata: vị trí, kích thước, dòng

## 4. INTERFACE
INPUT: plate_image (np.ndarray)
OUTPUT: {
"characters": [np.ndarray, ...], # list ảnh ký tự
"positions": [(x, y, w, h), ...], # vị trí từng ký tự
"line_type": "1_line" | "2_line",
"num_chars": int
}

text

## 5. CÔNG VIỆC CHI TIẾT

### 5.1. Nhị phân hóa
- [ ] Otsu: `cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)`
- [ ] Adaptive: `cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)`
- [ ] Đảo ngược nếu cần: `cv2.bitwise_not(img)`
- [ ] Output: `src/binarization.py`

### 5.2. Tách dòng (biển 2 dòng)
- [ ] Projection profile ngang: `np.sum(binary, axis=1)`
- [ ] Tìm khoảng trắng: `np.where(projection < threshold)`
- [ ] Tách 2 dòng tại khoảng trắng lớn nhất
- [ ] Output: `src/line_separation.py`

### 5.3. Tách ký tự
- [ ] Connected components: `cv2.connectedComponentsWithStats(binary)`
- [ ] Contour: `cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)`
- [ ] Projection profile dọc: `np.sum(binary, axis=0)`
- [ ] Output: `src/character_segmentation.py`

### 5.4. Lọc ký tự
- [ ] Diện tích: `area > min_area` và `area < max_area`
- [ ] Chiều cao: `h > min_height`
- [ ] Aspect ratio: `0.2 < w/h < 1.0`
- [ ] Loại bỏ nhiễu, dấu chấm nhỏ
- [ ] Output: `src/character_filter.py`

### 5.5. Xử lý ký tự dính
- [ ] Erosion để tách: `cv2.erode(binary, kernel, iterations=1)`
- [ ] Watershed nếu cần
- [ ] Output: `src/fix_touching.py`

### 5.6. Xử lý ký tự đứt
- [ ] Dilation: `cv2.dilate(binary, kernel, iterations=1)`
- [ ] Closing: `cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)`
- [ ] Output: `src/fix_broken.py`

### 5.7. Chuẩn hóa ký tự
- [ ] Resize về 28×28 hoặc 32×32
- [ ] Căn giữa: padding đều 4 phía
- [ ] Chuẩn hóa histogram
- [ ] Output: `src/normalize_character.py`

### 5.8. Data augmentation
- [ ] Rotation: ±15°
- [ ] Perspective: 0.1–0.3
- [ ] Blur: Gaussian, Motion
- [ ] Brightness/Contrast: ±30%
- [ ] Output: `src/augmentation.py`

### 5.9. Đánh giá
- [ ] Segmentation accuracy: số ký tự tách đúng / tổng
- [ ] Line separation accuracy
- [ ] Output: `reports/wp2_evaluation.md`

## 6. LÝ THUYẾT CẦN NẮM
- Otsu thresholding: tối đa hóa phương sai giữa 2 lớp
- Adaptive thresholding: ngưỡng cục bộ theo vùng
- Projection profile: histogram chiếu theo trục
- Connected components: gán nhãn vùng liên thông (4 hoặc 8 kết nối)
- Contour hierarchy: RETR_EXTERNAL, RETR_LIST, RETR_TREE
- Xử lý ký tự dính: erosion, watershed
- Xử lý ký tự đứt: dilation, closing

## 7. TIÊU CHÍ ĐÁNH GIÁ
| Metric | Target |
|---|---|
| Segmentation accuracy | ≥ 0.90 |
| Line separation accuracy | ≥ 0.95 |
| Character size consistency | ±5% |

## 8. DEPENDENCIES
- Phụ thuộc WP1 (input: ảnh biển đã cắt)
- Output cung cấp cho WP3

## 9. CẤU TRÚC CODE
src/
├── binarization.py
├── line_separation.py
├── character_segmentation.py
├── character_filter.py
├── fix_touching.py
├── fix_broken.py
├── normalize_character.py
├── augmentation.py
└── pipeline_wp2.py
tests/
├── test_binarization.py
├── test_segmentation.py
└── test_normalize.py

text

## 10. TÀI LIỆU THAM KHẢO
- Gonzalez & Woods. Digital Image Processing. Ch. 10
- Otsu (1979). A Threshold Selection Method. IEEE SMC.
- OpenCV Docs: Thresholding, Connected Components

## 11. CHECKLIST HOÀN THÀNH
- [ ] Code chạy được trên 100 ảnh biển test
- [ ] Segmentation accuracy ≥ 0.90
- [ ] Có unit test cho từng module
- [ ] Có tài liệu API cho WP3
- [ ] Có báo cáo đánh giá
