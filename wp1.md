\# WP1 – TIỀN XỬ LÝ \& PHÁT HIỆN BIỂN SỐ



\## 1. MỤC TIÊU

Từ ảnh gốc → tìm và cắt vùng biển số xe Việt Nam.



\## 2. INPUT

\- Ảnh gốc: JPG, PNG, kích thước tùy ý

\- Nguồn: ô tô, xe máy, nhiều điều kiện ánh sáng/góc chụp



\## 3. OUTPUT

\- Ảnh biển số đã cắt (bounding box)

\- Ảnh biển số đã chuẩn hóa (warped, deskewed)

\- Metadata: tọa độ box, góc nghiêng, confidence



\## 4. INTERFACE

INPUT: image\_path (str)

OUTPUT: {

"plate\_crop": np.ndarray, # ảnh biển đã cắt

"plate\_normalized": np.ndarray, # ảnh đã warp/deskew

"bbox": \[x1, y1, x2, y2], # tọa độ

"angle": float, # góc nghiêng

"confidence": float # độ tin cậy

}



\## 5. CÔNG VIỆC CHI TIẾT



\### 5.1. Thu thập \& Phân tích dataset

\- \[ ] Thu thập ảnh gốc có biển số VN

\- \[ ] Phân loại: ô tô/xe máy, 1 dòng/2 dòng, sáng/tối/nghiêng/mờ

\- \[ ] Thống kê: số lượng, phân bố, mất cân bằng

\- \[ ] Output: `dataset\_raw/`, `eda\_report.md`



\### 5.2. Tiền xử lý cơ bản

\- \[ ] Chuyển grayscale: `cv2.cvtColor(img, cv2.COLOR\_BGR2GRAY)`

\- \[ ] CLAHE: `cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))`

\- \[ ] Lọc nhiễu: Gaussian, Median, Bilateral

\- \[ ] Output: `src/preprocessing.py`



\### 5.3. Phát hiện cạnh

\- \[ ] Canny: `cv2.Canny(gray, 100, 200)`

\- \[ ] Sobel: `cv2.Sobel(gray, cv2.CV\_64F, 1, 0)`

\- \[ ] Laplacian: `cv2.Laplacian(gray, cv2.CV\_64F)`

\- \[ ] Output: `src/edge\_detection.py`



\### 5.4. Phát hiện biển bằng màu sắc

\- \[ ] Chuyển HSV: `cv2.cvtColor(img, cv2.COLOR\_BGR2HSV)`

\- \[ ] Lọc màu trắng: `lower = \[0, 0, 200]`, `upper = \[180, 30, 255]`

\- \[ ] Lọc màu vàng: `lower = \[15, 80, 150]`, `upper = \[35, 255, 255]`

\- \[ ] Lọc màu xanh: `lower = \[90, 50, 50]`, `upper = \[130, 255, 255]`

\- \[ ] Lọc màu đỏ: 2 dải `\[0, 100, 100]–\[10, 255, 255]` và `\[160, 100, 100]–\[180, 255, 255]`

\- \[ ] Output: `src/color\_detection.py`



\### 5.5. Phát hiện biển bằng morphology + contour

\- \[ ] Morphology: `cv2.morphologyEx(mask, cv2.MORPH\_CLOSE, kernel)`

\- \[ ] Tìm contour: `cv2.findContours(mask, cv2.RETR\_EXTERNAL, cv2.CHAIN\_APPROX\_SIMPLE)`

\- \[ ] Lọc theo diện tích: `area > 1000`

\- \[ ] Lọc theo aspect ratio: `2.0 < w/h < 6.0` (1 dòng), `0.8 < w/h < 1.5` (2 dòng)

\- \[ ] Lọc theo solidity: `solidity > 0.7`

\- \[ ] Output: `src/detection.py`



\### 5.6. Warp perspective

\- \[ ] Tìm 4 góc: `cv2.approxPolyDP(contour, 0.02\*peri, True)`

\- \[ ] Sắp xếp 4 góc: top-left, top-right, bottom-right, bottom-left

\- \[ ] Transform: `M = cv2.getPerspectiveTransform(src, dst)`

\- \[ ] Warp: `cv2.warpPerspective(img, M, (width, height))`

\- \[ ] Output: `src/warp.py`



\### 5.7. Deskew

\- \[ ] Tính góc: `angle = cv2.minAreaRect(contour)\[-1]`

\- \[ ] Xoay: `M = cv2.getRotationMatrix2D(center, angle, 1.0)`

\- \[ ] `cv2.warpAffine(img, M, (w, h))`

\- \[ ] Output: `src/deskew.py`



\### 5.8. Đánh giá

\- \[ ] Precision, Recall, F1

\- \[ ] Confusion matrix

\- \[ ] Phân tích lỗi: miss, false positive

\- \[ ] Output: `reports/wp1\_evaluation.md`



\## 6. LÝ THUYẾT CẦN NẮM

\- Canny edge detection: Gaussian → gradient → NMS → double threshold → hysteresis

\- Morphology: erosion, dilation, opening, closing, top-hat, black-hat

\- Contour analysis: hierarchy, approximation, bounding box

\- Perspective transform: ma trận homography 3×3

\- HSV color space: H (0–180), S (0–255), V (0–255)

\- Deskew: minAreaRect trả về góc \[-90, 0)



\## 7. TIÊU CHÍ ĐÁNH GIÁ

| Metric | Target |

|---|---|

| Precision | ≥ 0.85 |

| Recall | ≥ 0.80 |

| F1 | ≥ 0.82 |

| Latency | ≤ 200ms/ảnh |



\## 8. DEPENDENCIES

\- Không phụ thuộc WP nào

\- Output cung cấp cho WP2



\## 9. CẤU TRÚC CODE

src/

├── preprocessing.py

├── edge\_detection.py

├── color\_detection.py

├── detection.py

├── warp.py

├── deskew.py

└── pipeline\_wp1.py

tests/

├── test\_preprocessing.py

├── test\_detection.py

└── test\_warp.py



\## 10. TÀI LIỆU THAM KHẢO

\- Gonzalez \& Woods. Digital Image Processing. Ch. 10 (Segmentation)

\- Canny (1986). A Computational Approach to Edge Detection. TPAMI.

\- OpenCV Docs: Contours, Morphology, Geometric Transformations



\## 11. CHECKLIST HOÀN THÀNH

\- \[ ] Code chạy được trên 100 ảnh test

\- \[ ] Precision ≥ 0.85

\- \[ ] Có unit test cho từng module

\- \[ ] Có tài liệu API cho WP2

\- \[ ] Có báo cáo đánh giá

