# Nhận diện biển số xe Việt Nam — bản local

Pipeline OpenCV truyền thống: **WP1 phát hiện biển → WP2 tách ký tự → WP3
HOG/LBP + classifier → WP4 sửa chuỗi, kiểm tra mẫu và lưu SQLite**. Có giao
diện HTML + JavaScript, FastAPI, upload ảnh/video, lịch sử, thống kê, sửa kết
quả và chụp từ webcam. Đây là baseline, chưa đạt toàn bộ mục tiêu accuracy.

**Đã sửa lỗi cắt nhầm logo và mất dòng ký tự ngày 24/10/2026.** Trên 478
crop test: đúng nguyên chuỗi 48,74% → 69,46%, recall box ký tự 76,79% →
92,57%. Giữ nguyên HOG/SVM; tập trung sửa xử lý ảnh và chọn phương án nhị
phân. Xem [báo cáo sửa xử lý ảnh](reports/image_processing_fix.md).

**Đã khôi phục WP1 độc lập và kiểm tra chéo nhánh WP1.** Lỗi tích hợp trước
đó tự chạy WP2 để chọn lại vùng, làm F1 giảm từ 0,792 xuống 0,697. Mặc định
WP1 hiện khớp từng box với nhánh `wp1/fix-char-density-deskew`; luồng ứng
dụng có OCR dùng hàm chọn vùng riêng. [Điều tra và benchmark](reports/wp1_branch_investigation.md).

## Chạy ứng dụng local

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Mở [giao diện](http://127.0.0.1:8000/) hoặc [OpenAPI](http://127.0.0.1:8000/docs).
Có thể dùng `.\run_local.ps1`. Ctrl+C để dừng server. Phiên bản thư viện đã
kiểm chứng: `requirements-lock.txt` (Python 3.12). SQLite và ảnh runtime nằm
dưới `outputs/runtime/`, đã gitignore. Webcam mở theo nút bấm/quyền trình duyệt
và gửi từng ảnh chụp. Video mặc định lấy mẫu mỗi 5 frame, voting 20 quan sát;
mỗi frame đã xử lý đều lưu một bản ghi, kể cả không có biển.

## OCR và đánh giá các giai đoạn

Bộ OCR winter2897 do người dùng duyệt có 3.188 ảnh, 25.781 ký tự, 36 lớp.
Split theo SHA256 ảnh nguồn khoảng 70/15/15; bảng phông chữ chỉ dùng train.
O/Q/W có 4/2/4 mẫu và không có valid/test độc lập trong split hiện tại.
[Nguồn dữ liệu](reports/data_sources.md), [audit](reports/wp3_dataset_audit.json),
[split](reports/wp3_data_preparation.json).

Đã huấn luyện 5 model: SVM+HOG, SVM+LBP, SVM+HOG+LBP, kNN, Random Forest.
Service chọn SVM+HOG+LBP theo valid; accuracy trên **ký tự test cắt theo nhãn**
là 96,53%. Đây chưa phải accuracy đọc nguyên biển.
Sau sửa, trên 478 crop test, OpenCV + HOG/SVM chọn phương án nhị phân đạt
69,46% đúng chuỗi, CER 9,36%, recall/precision box ký tự 92,57%/97,15%.
Đúng chuỗi chưa đạt 75%; không suy accuracy toàn cảnh từ ảnh crop này.

- [WP2 segmentation](reports/wp2_evaluation.md).
- [So sánh classifier](reports/wp3_comparison.md), [ablation](reports/wp3_ablation.md).
- [Đánh giá chuỗi/CER/WER](reports/wp3_sequence_evaluation.md).
- [Robustness](reports/wp3_robustness.md), [confusion matrix](reports/wp3_confusion_matrix.png).
- [Hợp đồng WP1–WP4 và HTTP](docs/api.md).
- [Kiểm tra ứng dụng local WP4](reports/wp4_evaluation.md).

Benchmark baseline trước sửa là 176,9 ms/ảnh, lưu 169/169 kết quả
([số lịch sử](reports/baseline_local_latency.json)). Số này không đại diện
luồng hiện tại. Benchmark hiện tại tách WP1 độc lập khỏi bộ chọn vùng của
ứng dụng; xem bảng bên dưới và phạm vi thời gian trong báo cáo điều tra.

```powershell
.\.venv\Scripts\python.exe scripts\prepare_wp3_data.py data\external\winter2897\voc_plate_ocr_dataset.zip
.\.venv\Scripts\python.exe scripts\train_wp3.py
.\.venv\Scripts\python.exe scripts\evaluate_wp2_wp3.py
```

Các lệnh chuẩn bị/huấn luyện dành cho tái lập, không cần chạy lại khi artifact
đã có. Importer từ chối ghi đè `labels.csv`; dùng output mới cho phiên bản
dữ liệu khác. HOG ký tự 32×32 có 324 chiều, LBP 10 chiều, HOG+LBP 334 chiều.
Artifact `wp1_svm.pkl` giữ nguyên và chỉ lọc vùng biển/background.

Theo lựa chọn người dùng, bảng mã đăng ký dùng 34 địa phương và mã cơ quan 80,
có [nguồn](data/provinces.sources.md). `is_valid` chỉ kiểm tra mẫu hỗ trợ và
mã trong bảng. Loại xe giữ `unknown` nếu ô tô/xe máy đều phù hợp chuỗi.
Chưa có tập ảnh giao thông gốc kèm chuỗi thật độc lập để xác nhận mục tiêu
WP4 end-to-end ≥70%.

Đã có Dockerfile backend/frontend, nginx và compose. Người dùng yêu cầu dừng
sửa Docker Desktop nên build container chưa được xác nhận. Mục tiêu local
dùng SQLite; PostgreSQL và hosting production chưa triển khai.

## Kết quả WP1

Đo cùng 169 ảnh / 172 box, IoU ≥0,5, tối đa một biển mỗi ảnh. Phải phân
biệt WP1 độc lập và bộ chọn vùng dùng thêm thông tin từ WP2–WP4:

| Phạm vi | Precision | Recall | F1 |
|---|---:|---:|---:|
| WP1 độc lập, đã khôi phục | 0,879 | 0,721 | 0,792 |
| Ứng dụng: OpenCV + segmentation + HOG/SVM chọn vùng | 0,857 | 0,802 | 0,829 |

WP1 độc lập đạt Precision ≥0,85 nhưng chưa đạt Recall ≥0,80 và F1 ≥0,82.
Thời gian trung bình WP1 đầy đủ là 179,7 ms/ảnh, gồm đọc ảnh và warp/deskew;
P95 298,1 ms. [Đánh giá WP1](reports/wp1_evaluation.md),
[đối chiếu nhánh và phạm vi đo](reports/wp1_branch_investigation.md).

Bộ chọn vùng ứng dụng trung bình 1.658,9 ms/ảnh, P95 4.776,9 ms, chưa gồm
HTTP/ghi ảnh/SQLite; chưa đạt 1 giây. Báo cáo 0,841 trước đó không tái lập
được trong đợt đối chứng này; không dùng làm số hiện hành.

Để đo đầy đủ và tái lập cùng điều kiện, chạy:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_wp1.py --mode standalone --label WP1 --output outputs\wp1.json
.\.venv\Scripts\python.exe scripts\benchmark_wp1.py --mode application --label app --output outputs\application.json
```

Chạy từng lệnh tuần tự. `evaluate_wp1.py` vẫn đo riêng detector; không gọi
thời gian chọn vùng kèm OCR là thời gian riêng của detector OpenCV. F1 trên
box COCO cũng không phải accuracy đọc đúng nội dung biển.

Tiến độ WP1–WP4: [reports/implementation_status.md](reports/implementation_status.md).
WP2–WP4 đã có mã baseline và báo cáo; các mục chưa đạt được ghi rõ trong
bảng tiến độ. Thử nới ngưỡng diện tích WP1 trên valid làm F1 giảm, nên giữ
mặc định: [báo cáo thử nghiệm](reports/wp1_validation_tuning.md).

## Cài đặt

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Chạy demo

Chạy trên một ảnh đầu vào:

```powershell
.\.venv\Scripts\python.exe run_pipeline.py 'duong-dan-anh.jpg'
```

Lệnh này chạy WP1→WP4, in JSON và lưu SQLite/ảnh runtime. Có thể truyền
`--vehicle-type car` hoặc `motorcycle` nếu đã biết loại xe. Để chỉ chạy WP1:

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

Các model cần chạy được giữ trong Git; dataset tải thêm, runtime, ảnh người
dùng và model thử nghiệm được ignore. Xem [chính sách artifact](reports/artifact_policy.md)
và [model đi kèm](models/README.md).

## Ảnh minh họa

- [Ảnh before/after](demo/wp1_before_after.png): ảnh gốc, box dự đoán, vùng biển đã cắt, chỉnh phối cảnh, chuyển xám, CLAHE và lọc bilateral.
- [Ảnh minh họa HOG](demo/hog_character.png): giải thích gradient, histogram theo ô 8×8 cho WP3.
- Ảnh giao diện local: `reports/local_web_demo.png` (tạo local, không đưa lên Git).
- Video kết quả thật có chú thích: `demo/video_demo.mp4` (tạo local, không đưa lên Git). Cài `requirements-demo.txt`,
  rồi chạy `.\.venv\Scripts\python.exe -m demo.make_video_demo` sau khi xử lý
  video qua API. Đây là demo inference; quay kịch bản web/webcam hoàn chỉnh còn lại.

Tạo lại hoặc thay ảnh đầu vào:

```powershell
.\.venv\Scripts\python.exe -m demo.make_wp1_demo
.\.venv\Scripts\python.exe -m demo.make_wp1_demo --image 'duong-dan-anh.jpg' --output 'demo\anh-khac.png'
```
