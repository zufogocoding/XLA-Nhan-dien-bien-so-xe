# Nhận diện biển số xe – WP1 & WP2

Pipeline OpenCV truyền thống: WP1 tìm và chuẩn hóa vùng biển số trên ảnh xe, WP2 tách dòng, tách ký tự và chuẩn hóa từng ký tự về 32×32 để bàn giao cho WP3. HOG và nhận dạng ký tự thuộc WP3.

## Trạng thái hiện tại

### WP1 – Phát hiện và chuẩn hóa biển số

Pipeline **đã chạy được**, nhưng **độ chính xác trên tập test chưa đạt mục tiêu brief**:

| Chỉ số | Kết quả (test 169 ảnh) | Mục tiêu |
|---|---:|---:|
| Precision | 0,879 | ≥ 0,85 |
| Recall | 0,721 | ≥ 0,80 |
| F1 | 0,792 | ≥ 0,82 |
| Latency trung bình | 157,6 ms/ảnh | ≤ 200 ms/ảnh |

Chi tiết: [reports/wp1_evaluation.md](reports/wp1_evaluation.md).

### WP2 – Tách dòng, tách ký tự và chuẩn hóa

WP2 nhận `plate_normalized` từ WP1. Trên benchmark tổng hợp có ground truth ký tự chính xác (300 biển, seed 2026):

| Chỉ số | Kết quả | Mục tiêu |
|---|---:|---:|
| Segmentation accuracy | 0,995 – 1,000 | ≥ 0,90 |
| Line separation accuracy | 1,000 | ≥ 0,95 |
| Kích thước ký tự nhất quán ±5% | 100% patch | ±5% |
| Ảnh ra | 32×32, trắng trên đen | 32×32 |
| Exact-plate accuracy | 0,960 – 1,000 | — |
| Latency WP2 | ~3,0 ms/biển | — |

**WP2 đạt mục tiêu kỹ thuật trên benchmark tổng hợp.** Trên ảnh thật, dataset chỉ có box biển nên chưa thể đo độ chính xác ký tự: 41 ảnh WP1 đúng trong 60 ảnh khảo sát cho 90,2% trường hợp có 6–10 ký tự, nhưng một số mảnh khung sát biên vẫn bị đếm thành ký tự. Không nên coi các con số này là accuracy ký tự.

Chi tiết và phân tích lỗi: [reports/wp2_evaluation.md](reports/wp2_evaluation.md). API: [docs/wp2_api.md](docs/wp2_api.md).

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Chạy demo

### WP1

Chạy trên một ảnh đầu vào:

```powershell
.\.venv\Scripts\python.exe run_wp1.py 'duong-dan-anh.jpg'
```

Lệnh trên ghi `outputs/plate_crop.png` và `outputs/plate_normalized.png`, đồng thời in `bbox`, `angle`, `confidence`.

Giao diện Python:

```python
from src.pipeline_wp1 import detect_plate

result = detect_plate(image_path)  # None nếu không có ứng viên
```

`detect_plate` trả về dict gồm `plate_crop`, `plate_normalized` (mảng BGR), `bbox=[x1,y1,x2,y2]` theo tọa độ ảnh gốc, `angle` theo độ và `confidence` là điểm heuristic từ 0 đến 1.

### WP2

Chạy trên ảnh xe (WP1 → WP2):

```powershell
.\.venv\Scripts\python.exe run_wp2.py 'duong-dan-anh.jpg'
```

Hoặc trên ảnh biển đã cắt sẵn:

```powershell
.\.venv\Scripts\python.exe run_wp2.py 'duong-dan-bien.png' --plate
```

Kết quả ghi vào `outputs/`: `wp2_plate.png`, `wp2_binary.png`, `wp2_characters.png` (lưới ký tự) và `wp2_result.json` (metadata). Giao diện Python:

```python
from src.pipeline_wp2 import segment_plate

wp2 = segment_plate(detection["plate_normalized"])
characters = wp2["characters"]       # list ảnh 32×32, trắng trên đen
positions = wp2["positions"]         # box ký tự theo tọa độ ảnh biển
line_type = wp2["line_type"]         # "1_line" hoặc "2_line"
```

Các ký tự được sắp từ trên xuống dưới, trong mỗi dòng từ trái sang phải. Dấu `-` và `.` không nằm trong đầu ra; WP3 dựng lại định dạng từ vị trí và kiểu dòng. Chi tiết đầy đủ tại [docs/wp2_api.md](docs/wp2_api.md).

## Đánh giá

Đo WP1 trên nhãn COCO:

```powershell
.\.venv\Scripts\python.exe evaluate_wp1.py 'Vietnam License Plate.v2i.coco\test'
```

Đo WP2 trên benchmark tổng hợp và audit ảnh thật:

```powershell
.\.venv\Scripts\python.exe evaluate_wp2.py --count 100 --seed 2026 `
  --real-split 'Vietnam License Plate.v2i.coco\test' --real-limit 60 `
  --audit-output demo\wp2_real_audit.png
```

Chạy kiểm thử:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Xem [khảo sát dataset](eda_report.md).

## Ảnh minh họa

- [WP1 before/after](demo/wp1_before_after.png): ảnh gốc, box dự đoán, vùng biển đã cắt, chỉnh phối cảnh, chuyển xám, CLAHE và lọc bilateral.
- [WP1 HOG](demo/hog_character.png): giải thích gradient, histogram theo ô 8×8 cho WP3.
- [WP2 pipeline](demo/wp2_pipeline.png): biển thật đầu vào, ảnh nhị phân sạch và lưới ký tự 32×32.
- [WP2 synthetic](demo/wp2_synthetic.png): các mẫu biển tổng hợp một dòng/hai dòng.
- [WP2 real audit](demo/wp2_real_audit.png): 20 mẫu biển thật sau WP1, dùng kiểm tra bằng mắt.

Tạo lại:

```powershell
.\.venv\Scripts\python.exe -m demo.make_wp1_demo
.\.venv\Scripts\python.exe -m demo.make_wp2_demo
.\.venv\Scripts\python.exe scripts\make_synthetic_wp2.py --count 150 --seed 42 `
  --output data\synthetic_wp2 --showcase demo\wp2_synthetic.png
```

## Tài liệu

- [Brief WP2](wp2.md)
- [Đánh giá WP1](reports/wp1_evaluation.md)
- [Đánh giá WP2](reports/wp2_evaluation.md)
- [API WP2](docs/wp2_api.md)
