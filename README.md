# WP1 – Tiền xử lý và phát hiện biển số

Pipeline OpenCV truyền thống tìm ứng viên biển số trên ảnh gốc, cắt và chỉnh phối cảnh để bàn giao cho WP2. HOG thuộc bước nhận dạng ký tự WP3.

## Trạng thái hiện tại

Pipeline **đã chạy được**, nhưng **độ chính xác trên tập test chưa đạt mục tiêu brief**:

| Chỉ số | Kết quả (test 169 ảnh) | Mục tiêu |
|---|---:|---:|
| Precision | 0,879 | ≥ 0,85 |
| Recall | 0,721 | ≥ 0,80 |
| F1 | 0,792 | ≥ 0,82 |
| Latency trung bình | 157,6 ms/ảnh | ≤ 200 ms/ảnh |

Chi tiết đánh giá: [reports/wp1_evaluation.md](reports/wp1_evaluation.md)

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Chạy demo

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

## Đánh giá

Đo trên nhãn COCO:

```powershell
.\.venv\Scripts\python.exe evaluate_wp1.py 'Vietnam License Plate.v2i.coco\test'
.\.venv\Scripts\python.exe -m pytest -q
```

Xem [khảo sát dataset](eda_report.md).

## Ảnh minh họa

- [Ảnh before/after](demo/wp1_before_after.png): ảnh gốc, box dự đoán, vùng biển đã cắt, chỉnh phối cảnh, chuyển xám, CLAHE và lọc bilateral.
- [Ảnh minh họa HOG](demo/hog_character.png): giải thích gradient, histogram theo ô 8×8 cho WP3.

Tạo lại hoặc thay ảnh đầu vào:

```powershell
.\.venv\Scripts\python.exe -m demo.make_wp1_demo
.\.venv\Scripts\python.exe -m demo.make_wp1_demo --image 'duong-dan-anh.jpg' --output 'demo\anh-khac.png'
```