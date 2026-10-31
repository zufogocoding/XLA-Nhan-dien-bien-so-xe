# Nhận diện biển số xe Việt Nam — baseline local

Pipeline OpenCV + machine learning, chạy hoàn toàn local:

**WP1 phát hiện biển → WP2 tách ký tự → WP3 HOG/LBP + classifier → WP4 sửa chuỗi,
kiểm tra mẫu và lưu SQLite.**

Kèm giao diện web để upload ảnh/video, chụp webcam, xem lịch sử, thống kê và sửa
kết quả. Đây là **baseline**, chưa đạt toàn bộ mục tiêu accuracy toàn cảnh; các số
đo và giới hạn được ghi rõ bên dưới.

## Demo nhanh bằng Podman

Yêu cầu: Linux, Podman và `podman-compose`. Trên Fedora:

```bash
sudo dnf install podman podman-compose
```

Chạy từ thư mục gốc của repo:

```bash
mkdir -p outputs
cp .env.example .env      # tuỳ chọn: đổi cổng / giới hạn upload
podman-compose up --build -d
podman-compose ps         # chờ backend chuyển sang healthy
```

Mở các địa chỉ sau:

| Địa chỉ | Nội dung |
|---|---|
| <http://127.0.0.1:8080> | Giao diện web qua nginx (khuyên dùng) |
| <http://127.0.0.1:8000> | Backend FastAPI, phục vụ cùng giao diện |
| <http://127.0.0.1:8000/docs> | OpenAPI / Swagger UI |
| <http://127.0.0.1:8000/api/health> | Trạng thái server và model OCR |

Lần build đầu mất vài phút vì cài dependency. Dừng hệ thống:

```bash
podman-compose down
```

SQLite, ảnh upload và crop nằm trong `outputs/` trên host nên `down` không làm mất
dữ liệu. Chỉ bind vào `127.0.0.1`, không mở ra mạng LAN.

> Dùng Docker cũng được với cùng file compose: thay `podman-compose` bằng
> `docker compose`.

## Các cách demo

### 1. Demo trên web (nhanh nhất)

Mở <http://127.0.0.1:8080>, sau đó:

1. **Ảnh đơn**: chọn ảnh biển số, bấm nhận diện. Kết quả hiện chuỗi đọc được,
   độ tin cậy, box, crop và các ký tự đã tách.
2. **Nhiều biển trong một ảnh**: bật checkbox **Ảnh có nhiều biển số** rồi upload.
   Ảnh mẫu: [`demo/multi_plate_collage_input.jpg`](demo/multi_plate_collage_input.jpg)
   — collage 4 ảnh, tìm đủ 8/8 box nhưng chất lượng đọc không đồng đều.
3. **Video**: upload `.mp4/.avi/.mov/.mkv/.webm`. Mặc định lấy mẫu mỗi 5 frame và
   voting trên 20 quan sát; mỗi frame đã xử lý đều được lưu lịch sử.
4. **Webcam**: bấm mở camera, cấp quyền trình duyệt, chụp từng khung hình.
   Webcam chỉ hoạt động với `localhost` hoặc `https`; nếu truy cập bằng IP LAN qua
   HTTP, trình duyệt sẽ chặn `getUserMedia`.
5. **Lịch sử / thống kê**: tìm kiếm, xem lại, sửa hoặc xoá bản ghi; kiểm tra số
   liệu tổng hợp.

Kết quả mẫu đã tạo sẵn (không cần chạy):

- [`demo/multi_plate_real_result.jpg`](demo/multi_plate_real_result.jpg) — ảnh thật
  2 biển với box, crop và chuỗi đọc được.
- [`demo/multi_plate_collage_result.jpg`](demo/multi_plate_collage_result.jpg) —
  collage 4 ảnh với box đánh số.
- [`demo/wp1_before_after.png`](demo/wp1_before_after.png) — minh hoạ WP1.
- [`demo/hog_character.png`](demo/hog_character.png) — minh hoạ đặc trưng HOG.

### 2. Demo bằng API

Upload một ảnh:

```bash
curl -s -F "file=@demo/multi_plate_collage_input.jpg" \
  http://127.0.0.1:8000/api/upload/image | python3 -m json.tool
```

Upload ảnh nhiều biển:

```bash
curl -s -F "file=@demo/multi_plate_collage_input.jpg" \
  -F "max_plates=10" \
  http://127.0.0.1:8000/api/upload/image/multi | python3 -m json.tool
```

Upload video (giữ nguyên `stride=5` mặc định):

```bash
curl -s -F "file=@duong-dan-video.mp4" -F "stride=5" \
  http://127.0.0.1:8000/api/upload/video | python3 -m json.tool
```

Các endpoint chính: `GET /api/health`, `POST /api/upload/image`,
`POST /api/upload/image/multi`, `POST /api/upload/video`,
`GET/POST/PATCH/DELETE /api/plates`, `GET /api/stats`.
Chi tiết hợp đồng và mã lỗi: [docs/api.md](docs/api.md).

### 3. Demo bằng CLI trong container

Ảnh mẫu đã có trong container tại `/app/demo`:

```bash
# Một biển mạnh nhất, chạy đủ WP1 → WP4
podman-compose exec backend python run_pipeline.py \
  /app/demo/multi_plate_collage_input.jpg

# Nhiều biển: ghi annotated.jpg, crop từng biển và result.json
podman-compose exec backend python scripts/demo_multi_plate.py \
  /app/demo/multi_plate_collage_input.jpg
```

Kết quả CLI nằm trên host tại `outputs/multi_plate/<tên-ảnh>/`. Muốn thử ảnh của
bạn, copy vào thư mục `demo/` (đang được mount read-only vào container):

```bash
cp anh-cua-ban.jpg demo/
podman-compose exec backend python scripts/demo_multi_plate.py \
  /app/demo/anh-cua-ban.jpg --max-plates 10
```

Chỉ chạy WP1:

```bash
podman-compose exec backend python run_wp1.py /app/demo/anh-cua-ban.jpg
```

## Chạy trực tiếp trên máy (không dùng container)

Cần Python 3.12. Dùng `requirements-lock.txt` để tái lập đúng phiên bản đã kiểm tra:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Hoặc dùng `.\run_local.ps1` trên Windows. Mở
<http://127.0.0.1:8000/> và <http://127.0.0.1:8000/docs>.

## Podman: cấu hình và vận hành

### Thành phần

```text
:8080  nginx (web/) ──/api/, /files/──> backend FastAPI :8000
                                        ├── giao diện web tại /
                                        ├── OpenAPI tại /docs
                                        └── SQLite + uploads trong outputs/
```

| Service | Vai trò | Cổng mặc định |
|---|---|---|
| `backend` | FastAPI, WP1–WP4, SQLite, giao diện dự phòng | `8000` |
| `frontend` | nginx phục vụ file tĩnh và reverse proxy | `8080` |

Dockerfile backend dùng `requirements-lock.txt` (Python 3.12). Image có sẵn model,
script demo và test. `docker-compose.yml` mount:

- `./outputs:/app/outputs:Z` — dữ liệu runtime và kết quả CLI (nhãn `:Z` cho SELinux).
- `./demo:/app/demo:ro,Z` — ảnh mẫu, chỉ đọc (nhãn `:Z` cho SELinux).

### Đổi cổng hoặc giới hạn upload

```bash
cp .env.example .env
# sửa ALPR_WEB_PORT, ALPR_API_PORT, ALPR_MAX_UPLOAD_MB
podman-compose up -d
```

Kiểm tra trạng thái và log:

```bash
podman-compose ps
podman-compose logs -f backend
curl -s http://127.0.0.1:8000/api/health | python3 -m json.tool
```

Sau khi sửa code, build lại:

```bash
podman-compose up --build -d
```

### Xử lý sự cố thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `podman-compose: command not found` | Cài `podman-compose` (Fedora: `sudo dnf install podman-compose`) |
| Cổng bận | Đổi `ALPR_WEB_PORT` / `ALPR_API_PORT` trong `.env` |
| Backend mãi không `healthy` | Xem `podman-compose logs backend`; thử `podman-compose build --no-cache` |
| `Permission denied` khi ghi `outputs/` | Kiểm tra SELinux; mount đã có `:Z`. Có thể `podman unshare chown -R 0:0 outputs` rồi chạy lại |
| Webcam không mở | Dùng `http://127.0.0.1:8080` hoặc HTTPS, không dùng IP LAN qua HTTP |
| Muốn reset toàn bộ dữ liệu | `podman-compose down` rồi xoá `outputs/runtime/` |

## Kiến trúc mã nguồn

```text
api/main.py              FastAPI, upload, CRUD, static files
src/pipeline_wp1.py      phát hiện biển, warp/deskew
src/pipeline_wp2.py      tách dòng và ký tự
src/pipeline_wp3.py      nhận diện ký tự bằng HOG/LBP + classifier
src/pipeline_wp4.py      sửa chuỗi, validate tỉnh/mẫu, lưu kết quả
src/multi_plate.py       lớp ứng dụng đọc nhiều biển trong một ảnh
src/service.py           ghép WP1–WP4, lưu SQLite và ảnh runtime
web/                     giao diện HTML/CSS/JS
models/                  artifact WP1 + OCR đã huấn luyện
scripts/                 demo, benchmark, đánh giá, huấn luyện
data/                    bảng mã tỉnh và dữ liệu hỗ trợ
reports/                 số đo, audit, chẩn đoán
docs/                    báo cáo đồ án, thuyết trình, hợp đồng API
```

Luồng xử lý chi tiết và hợp đồng giữa các tầng: [docs/api.md](docs/api.md).

## Kết quả hiện tại

Các số dưới đây là baseline, đo trên dữ liệu sẵn có — **không phải accuracy toàn
cảnh trên ảnh giao thông độc lập**.

| Hạng mục | Kết quả | Ghi chú |
|---|---:|---|
| WP1 độc lập | P 0,879 / R 0,721 / F1 0,792 | 169 ảnh, 172 box, IoU ≥ 0,5 |
| Bộ chọn vùng của ứng dụng | F1 0,829 | có thêm tín hiệu WP2–WP4 |
| OCR trên ký tự test | 96,53% | 36 lớp; accuracy ký tự, không phải nguyên biển |
| Chuỗi đúng trên 478 crop test | 69,46% | CER 9,36%; chưa đạt mục tiêu 75% |
| Multi-plate, box ≥1% diện tích | F1 0,727 | 23 ảnh / 47 box |
| Multi-plate, mọi box | F1 0,483 | recall thấp vì nhiều biển rất nhỏ |

Sau đợt sửa xử lý ảnh ngày 24/10/2026, đúng nguyên chuỗi trên 478 crop test tăng
48,74% → 69,46%; recall box ký tự tăng 76,79% → 92,57%. WP1 độc lập đã được
khôi phục, tách khỏi bộ chọn vùng có hỗ trợ OCR của ứng dụng.

Thời gian tham khảo: WP1 độc lập 179,7 ms/ảnh (P95 298,1 ms); bộ chọn vùng kèm
OCR 1.658,9 ms/ảnh (P95 4.776,9 ms), chưa gồm HTTP/ghi ảnh/SQLite. Chưa đạt mục
tiêu 1 giây cho toàn luồng.

Đọc thêm:

- [Tổng hợp tiến độ WP1–WP4](reports/implementation_status.md)
- [Đánh giá WP1](reports/wp1_evaluation.md) và
  [đối chiếu nhánh WP1](reports/wp1_branch_investigation.md)
- [WP2 segmentation](reports/wp2_evaluation.md)
- [So sánh classifier](reports/wp3_comparison.md),
  [ablation](reports/wp3_ablation.md),
  [đánh giá chuỗi/CER](reports/wp3_sequence_evaluation.md)
- [Chẩn đoán multi-plate](reports/multi_plate_diagnosis.md)
- [Báo cáo đồ án](docs/bao_cao_do_an.md) và
  [kịch bản thuyết trình 20 phút](docs/thuyet_trinh_20p.md)

## Kiểm thử và tái lập

Chạy test local:

```bash
source .venv/bin/activate
python -m pytest -q
```

Chạy test trong container:

```bash
podman-compose exec backend python -m pytest -q
```

Benchmark WP1 và ứng dụng (cần dataset COCO local):

```bash
python scripts/benchmark_wp1.py --mode standalone --label WP1 \
  --output outputs/wp1.json
python scripts/benchmark_wp1.py --mode application --label app \
  --output outputs/application.json
```

Đánh giá trên nhãn COCO:

```bash
python evaluate_wp1.py "Vietnam License Plate.v2i.coco/test"
python scripts/diagnose_wp1_failures.py
```

Huấn luyện lại OCR (dataset ngoài repo, không cần cho demo):

```bash
python scripts/prepare_wp3_data.py data/external/winter2897/voc_plate_ocr_dataset.zip
python scripts/train_wp3.py
python scripts/evaluate_wp2_wp3.py
```

Dataset, runtime, ảnh người dùng và model thử nghiệm được gitignore; model cần cho
ứng dụng nằm trong Git. Xem [chính sách artifact](reports/artifact_policy.md) và
[danh sách model](models/README.md).

## Giới hạn đã biết

- Baseline phục vụ demo local, **chưa dùng cho production**: không có xác thực,
  phân quyền hay HTTPS; chỉ nên chạy trên máy cá nhân.
- Chưa có tập ảnh giao thông gốc kèm chuỗi thật độc lập để xác nhận mục tiêu
  end-to-end ≥70%.
- Multi-plate còn yếu với biển nhỏ hoặc ảnh đông xe; thứ hạng biển phụ chưa ổn định.
- Video chưa có nhãn OCR để đo accuracy; kết quả video mang tính kiểm tra chức năng.
- SQLite là mục tiêu local; PostgreSQL và hosting production chưa triển khai.
- Webcam cần secure context của trình duyệt (localhost hoặc HTTPS).

Kịch bản demo/thuyết trình chi tiết: [demo/README.md](demo/README.md).
