# API và hợp đồng các pipeline

## Chạy local

`.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000`

Ứng dụng và OpenAPI: `http://127.0.0.1:8000/`, `http://127.0.0.1:8000/docs`.
SQLite: `outputs/runtime/plates.sqlite3`; ảnh upload/crop/ký tự nằm dưới
`outputs/runtime/public/`. Database không nằm trong thư mục được phục vụ tĩnh.

## WP1 → WP2

`src.pipeline_wp1.detect_plate(image_path)` giữ hợp đồng đã có. Thêm
`detect_plate_image(bgr_array)` để tái sử dụng trên video, tránh ghi frame tạm.
Kết quả gồm `plate_crop`, `plate_normalized`, `bbox`, `angle`, `confidence`.
`confidence` của detector là điểm xếp hạng, không phải xác suất đúng.
`detect_plate` và `detect_plate_image` mặc định chỉ chạy WP1, lấy ứng viên
đầu của detector như nhánh WP1 gốc; không tải OCR hoặc chạy WP2.

Ứng dụng đầy đủ gọi rõ ràng
`src.recognition_selection.select_plate_for_recognition(image, classifier)`.
Hàm này thêm ứng viên từ chữ thẳng hàng, dùng WP2–WP4 kiểm tra nhiều vùng,
trả thêm `source`, `segmentation`, `ocr` và chẩn đoán. Đây là phạm vi ứng
dụng, không phải benchmark WP1 độc lập. Tham số `classifier` tùy chọn của
`detect_plate_image` còn được giữ để tương thích và chuyển tới hàm này.

`scripts/benchmark_wp1.py --mode standalone` đo WP1 đầy đủ, còn `--mode
application` đo chọn vùng có OCR; phải truyền `--output` cho file kết quả.
Cả hai gồm đọc/giải mã ảnh, loại trừ HTTP/upload/SQLite và dùng một thread
OpenCV mặc định. [Đối chiếu nhánh và kết quả](../reports/wp1_branch_investigation.md).

## WP2 → WP3

```python
from src.pipeline_wp2 import segment_plate, SegmentationConfig
result = segment_plate(plate_normalized, SegmentationConfig(character_size=32))
```

- `characters`: ảnh uint8 32×32, nền đen và nét trắng, giữ tỷ lệ và căn giữa.
- `positions`: các `(x,y,w,h)` trong tọa độ ảnh biển đầu vào WP2.
- `line_type`: `1_line`, `2_line`; `None` khi không có foreground.
- `num_chars`, `line_ids`, `line_ranges`: số lượng, thứ tự dòng và khoảng hàng.
- `binary`: ảnh nhị phân phục vụ chẩn đoán.
- `algorithm_version`, `line_method`, `working_scale`: phiên bản thuật toán,
  cách tách dòng và hệ số chuẩn hóa nội bộ.

Thứ tự: trên xuống dưới, trong mỗi dòng từ trái sang phải. Hỗ trợ Otsu/adaptive;
connected components/contours/projection; xử lý ký tự dính và nét đứt. Closing
chỉ bật khi truyền `broken_kernel` để tránh tự động nối các ký tự đang rời.
Mặc định `threshold_method="auto"` tạo các phương án Otsu, CLAHE+Otsu và
adaptive Gaussian 31/51, có/không lọc viền. `segment_plate` chọn theo hình
học; `src.plate_reader.read_plate(image, classifier)` dùng HOG/SVM hiện có
để chọn phương án cho luồng thực tế, trả `ocr` cùng metadata WP2. Báo cáo
phân biệt tách thuần hình học với phương án chọn bằng HOG/SVM.
Mặc định xử lý ở chiều cao 128 px, so sánh hai cực tính foreground và nhóm
thành phần theo tâm dòng để giữ nguyên ký tự trên biển nghiêng. Projection
ngang là phương án dự phòng. `positions`, `line_ranges` và `binary` được đưa
về tọa độ/kích thước đầu vào; ảnh ký tự đầu ra vẫn là 32×32. Cấu hình này chọn
trên valid, không có nghĩa đã đạt mục tiêu tách ký tự của brief.
Augmentation trong `src/augmentation.py` dành cho dữ liệu train; không sửa nhãn
test hoặc tạo ra nhãn đánh giá mới.

## WP3 → WP4

```python
from src.pipeline_wp3 import recognize_characters
result = recognize_characters(characters)
```

Trả `raw_text`, `confidences`, `char_details`; giữ thứ tự WP2, bỏ dấu `-` và `.`
khỏi chuỗi thô. Artifact OCR có `task=character_recognition`, kích thước 32,
loại feature, model sklearn, phiên bản sklearn và fingerprint dữ liệu. Model
phát hiện WP1 không dùng làm model OCR. Khi chưa có artifact, phát sinh
`ModelNotReadyError` thay vì trả chuỗi minh họa.

HOG 32×32: 324 chiều (8×8 cell, 2×2-cell block, stride một cell, 9 bins,
L2-Hys). LBP: uniform 8 láng giềng của cửa sổ 3×3, histogram 10 bins. HOG+LBP:
334 chiều. LBP này dùng láng giềng rời rạc; không dùng nội suy tròn của skimage.
Service chọn model theo `models/ocr_manifest.json`, được chọn bằng valid;
API Python mặc định dùng `svm_hog.pkl`, hoặc truyền classifier rõ ràng.

## WP4

`postprocess(raw_text, confidences, vehicle_type="unknown")` kiểm tra ba mẫu
trong brief và bảng mã hiện hành có nguồn tại `data/provinces.sources.md`.
Trả chuỗi gốc, chuỗi sửa, định dạng, danh sách thay thế, tỉnh/cơ quan cấp mã và
`is_valid`. Mẫu ô tô 5 số và xe máy có thể trùng nhau; loại xe giữ `unknown`
nếu chưa có gợi ý đủ phân biệt. Không suy loại xe từ category 1/2 của COCO.
`is_valid` chỉ có nghĩa đúng mẫu được hỗ trợ và mã đăng ký có trong bảng.
Điểm trung bình ký tự không phải xác suất đúng cả biển.
Hỗ trợ thêm sê-ri xe máy hai chữ, ví dụ `29AC88688`; chuỗi đã đúng mẫu
được giữ nguyên trước bước sửa nhầm. Parser không bao phủ mọi loại biển.

## HTTP

| Method | Path | Nội dung |
|---|---|---|
| GET | `/api/health` | Trạng thái server, khả năng nạp model OCR |
| POST | `/api/upload/image` | Multipart `file`, `vehicle_type` tùy chọn |
| POST | `/api/upload/video` | Multipart `file`, `vehicle_type`, `stride` 1–60 (mặc định 5) |
| GET | `/api/plates` | `q`, `limit` 1–200, `offset` |
| GET | `/api/plates/{id}` | Chi tiết một bản ghi |
| POST | `/api/plates` | JSON `plate_text`, `vehicle_type`: nhập thủ công |
| PATCH | `/api/plates/{id}` | JSON như trên: chỉnh kết quả, giữ chuỗi OCR gốc |
| DELETE | `/api/plates/{id}` | Xóa bản ghi database; giữ file ảnh nguồn |
| GET | `/api/stats` | Số bản ghi theo trạng thái/tỉnh; không phải accuracy |

Ảnh trung gian ở `metadata.processing_images` gồm ảnh xám, nhị phân được
chọn và box/thứ tự ký tự, có URL `/files/processing/...`. Có `threshold_method`,
`frame_cleanup`, `candidate_diagnostics`, `ocr_requires_review` để giải thích
kết quả. `/api/health` trả thêm `segmentation_version` để phát hiện server cũ.

Trạng thái: `recognized`, `needs_review`, `no_plate`, `segmentation_empty`,
`ocr_unavailable`, `processing_error`, `manual`. Mỗi frame được lấy mẫu đều
lưu một bản ghi, kể cả không phát hiện được biển. Kết quả đúng mẫu nhưng có
ký tự điểm thấp vẫn là `needs_review`. Kết quả video trả tối đa 50 bản ghi
cuối để giới hạn kích thước response; toàn bộ vẫn nằm trong DB.
Voting dùng cửa sổ 20 quan sát, bỏ quyết định khi hòa phiếu, reset nếu box
nhảy vị trí, có số frame/vote ratio riêng. Chưa có multi-object tracking;
biển đổi trong cùng vị trí có thể làm lẫn cửa sổ voting.

Upload mặc định tối đa 256 MB, chỉnh qua `ALPR_MAX_UPLOAD_MB`. Runtime directory
chỉnh qua `ALPR_RUNTIME_DIR`. Webcam dùng quyền trình duyệt khi người dùng
bấm mở và gửi ảnh chụp tới cùng endpoint ảnh; chưa phải stream webcam tự động.

## Docker

`docker compose up --build -d`: backend tại 127.0.0.1:8000, frontend nginx tại
127.0.0.1:8080. Runtime bind mount giữ DB/ảnh khi tái tạo container. Frontend
proxy `/api` và `/files` tới backend. Đây là cấu hình local SQLite đã được
người dùng chọn; PostgreSQL/hosting production chưa được triển khai.
Docker build chưa được xác nhận vì Docker Desktop lỗi lúc khởi động; người
dùng đã yêu cầu dừng sửa Docker và tiếp tục chạy Python local.
