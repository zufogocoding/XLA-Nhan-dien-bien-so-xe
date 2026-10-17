<<<<<<< HEAD
# XLA-Nhan-dien-bien-so-xe
Do an phuc vu mon hoc xu ly anh
link dataset: https://universe.roboflow.com/ds/lTzCXt2Gdt?key=OhiLeeSQZU
may die link
=======
# WP1 – Tiền xử lý và phát hiện biển số

Pipeline OpenCV truyền thống tìm ứng viên biển số trên ảnh gốc, cắt và chỉnh phối cảnh để bàn giao cho WP2. HOG thuộc bước nhận dạng ký tự WP3.

## Chạy

Tạo môi trường ảo rồi cài `requirements.txt`:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_wp1.py 'duong-dan-anh.jpg'
```

Lệnh trên ghi `outputs/plate_crop.png` và `outputs/plate_normalized.png`, đồng thời in `bbox`, `angle`, `confidence`. Giao diện Python: `from src.pipeline_wp1 import detect_plate`; gọi `detect_plate(image_path)`. Hàm trả `None` nếu không có ứng viên; nếu có, trả dict gồm `plate_crop`, `plate_normalized` (mảng BGR), `bbox=[x1,y1,x2,y2]` theo tọa độ ảnh gốc, `angle` theo độ và `confidence` là điểm heuristic từ 0 đến 1.

Đánh giá trên nhãn COCO:

```powershell
.\.venv\Scripts\python.exe evaluate_wp1.py 'Vietnam License Plate.v2i.coco\test'
.\.venv\Scripts\python.exe -m pytest -q
```

Xem [khảo sát dataset](eda_report.md) và [đánh giá hiện tại](reports/wp1_evaluation.md). Pipeline hiện là baseline nghiên cứu; độ chính xác trên test chưa đạt mục tiêu brief.

## Ảnh minh họa để demo

[Ảnh before/after](demo/wp1_before_after.png) dùng một ảnh xe máy trong dataset để trình bày ảnh gốc, box dự đoán, vùng biển đã cắt, chỉnh phối cảnh, chuyển xám, CLAHE và lọc nhiễu bilateral. Ba bước cuối minh họa tiền xử lý trên ảnh biển đã chỉnh; interface `detect_plate` hiện trả ảnh biển ở bước chỉnh phối cảnh.

Tạo lại hoặc thay ảnh đầu vào:

```powershell
.\.venv\Scripts\python.exe -m demo.make_wp1_demo
.\.venv\Scripts\python.exe -m demo.make_wp1_demo --image 'duong-dan-anh.jpg' --output 'demo\anh-khac.png'
```

## Minh họa HOG cho WP3

[Ảnh minh họa HOG](demo/hog_character.png) dùng ký tự `9` được cắt thủ công từ biển xe máy để giải thích gradient, histogram theo ô 8×8 và vector 3.780 giá trị. Crop ký tự ở đây chỉ phục vụ giảng giải; nó không thay thế module tách ký tự WP2 hoặc mô hình phân loại WP3.

```powershell
.\.venv\Scripts\python.exe -m demo.make_hog_demo
```
>>>>>>> 3d9350a (frist-commit)
