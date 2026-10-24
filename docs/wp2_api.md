# API WP2 – Tách dòng, tách ký tự và chuẩn hóa

Module chính: `src/pipeline_wp2.py`. WP2 nhận **ảnh biển đã được WP1 chuẩn hóa** (`plate_normalized`), không nhận ảnh xe thô hoặc box COCO chưa cắt.

## 1. Hàm công khai

```python
from src.pipeline_wp2 import segment_plate, segment_plate_file

result = segment_plate(plate_bgr, size=32)
result = segment_plate_file("outputs/plate_normalized.png", size=32)
```

| Hàm | Đầu vào | Ghi chú |
|---|---|---|
| `segment_plate(plate_image, size=32)` | `np.ndarray` BGR, BGRA hoặc xám | Ảnh biển đã cắt; không cần chỉnh phối cảnh lại |
| `segment_plate_file(path, size=32)` | Đường dẫn ảnh | Đọc bằng `np.fromfile` + `cv2.imdecode`, hỗ trợ đường dẫn Unicode |

Đầu vào phải không rỗng và có cạnh nhỏ nhất (sau khi chuyển xám) ít nhất 12 px; nếu không, hàm ném `ValueError`. `size` phải ≥ 8 (mặc định 32).

## 2. Kết quả trả về

`segment_plate` trả về `dict`:

| Khóa | Kiểu | Ý nghĩa |
|---|---|---|
| `characters` | `list[np.ndarray]` | Ảnh xám `size×size`, `uint8`, **nền đen – ký tự trắng**, đúng thứ tự đọc |
| `positions` | `list[tuple[int, int, int, int]]` | Box `(x, y, w, h)` của từng ký tự **theo tọa độ ảnh đầu vào** |
| `line_type` | `str` | `"1_line"` hoặc `"2_line"` |
| `num_chars` | `int` | Số ký tự, bằng `len(characters)` |
| `char_binary` | `list[np.ndarray]` | Mask nhị phân `size×size` (0/255) tương ứng từng ký tự |
| `line_boxes` | `list[tuple[int, int, int, int]]` | Dải dòng `(0, y, width, height)` theo tọa độ ảnh đầu vào |
| `line_indices` | `list[int]` | Dòng của từng ký tự: `0` là dòng trên, `1` là dòng dưới |
| `binary` | `np.ndarray` | Ảnh nhị phân sạch, `uint8` 0/255, cùng kích thước ảnh đầu vào |
| `normalized_size` | `int` | Kích thước cạnh của `characters` (mặc định 32) |
| `binarization` | `str` | Phương pháp được chọn: `"otsu"`, `"adaptive"` hoặc `"central"` |

Thứ tự:

- Các dòng từ trên xuống dưới.
- Trong mỗi dòng, ký tự từ trái sang phải.
- `characters[i]`, `positions[i]`, `char_binary[i]`, `line_indices[i]` cùng chỉ một ký tự.
- Với biển hai dòng, toàn bộ ký tự dòng 0 đứng trước toàn bộ ký tự dòng 1; không sắp xếp lại theo trục y toàn ảnh.

Khi không tìm thấy ký tự, hàm trả `characters=[]`, `positions=[]`, `line_type="1_line"`, `num_chars=0`; `binary` vẫn là ảnh nhị phân đã làm sạch.

## 3. Chuẩn hóa ký tự

Mỗi box được cắt từ ảnh xám đã tăng cường CLAHE và mask nhị phân tương ứng, sau đó:

1. Cắt sát phần mực (tight bounding box).
2. Đảo màu nếu cần để ký tự sáng hơn nền.
3. Chuẩn hóa tương phản theo percentile 2–98, giữ viền anti-alias quanh nét.
4. Scale theo chiều cao để phần glyph chiếm khoảng 78% vùng dùng được, giữ tỷ lệ khung hình.
5. Căn giữa trên canvas vuông `size×size`, nền đen.

Vì vậy `characters` luôn trắng trên đen, bất kể biển trắng/xanh/vàng. `char_binary` là mask nhị phân sạch dùng khi cần kiểm tra hình dạng hoặc huấn luyện mô hình nhị phân.

## 4. Cách chọn ngưỡng nhị phân

Pipeline thử tối đa ba phương pháp:

- `otsu`: Otsu toàn ảnh, phù hợp biển có độ sáng đều.
- `adaptive`: ngưỡng Gauss cục bộ, phù hợp ảnh sáng không đều hoặc biển bị bóng.
- `central`: Otsu chỉ trên vùng trung tâm, tránh thân xe sáng xung quanh làm lệch ngưỡng.

Mỗi kết quả được chấm bằng heuristic dựa trên số ký tự (ưu tiên 7–9), độ đồng đều chiều cao, hình học một/hai dòng và số box chạm biên. Nếu Otsu đạt điểm cao, pipeline dừng sớm; nếu không, thử các phương pháp còn lại và chọn điểm cao nhất. Điểm này **không phải xác suất** và không được trả ra API.

## 5. Ví dụ tích hợp WP1 → WP2 → WP3

```python
from src.pipeline_wp1 import detect_plate
from src.pipeline_wp2 import segment_plate

detection = detect_plate("car.jpg")
if detection is None:
    raise RuntimeError("WP1 không tìm thấy biển số")

wp2 = segment_plate(detection["plate_normalized"], size=32)

# WP3 nhận trực tiếp danh sách patch 32×32, không cần cắt lại.
for patch, box, line in zip(
    wp2["characters"], wp2["positions"], wp2["line_indices"]
):
    ...  # đưa patch vào bộ phân loại ký tự

if wp2["line_type"] == "2_line":
    top = [c for c, line in zip(wp2["characters"], wp2["line_indices"]) if line == 0]
    bottom = [c for c, line in zip(wp2["characters"], wp2["line_indices"]) if line == 1]
```

### Bàn giao cho WP3

- Dùng `characters` làm đầu vào trực tiếp; mỗi patch đã chuẩn hóa 32×32, trắng trên đen.
- **Không có ký tự phân cách `-` và `.`** trong đầu ra. WP3 cần dựng lại định dạng từ `line_type`, `line_indices`, `positions` và quy tắc biển số Việt Nam.
- `positions` cho biết vị trí thật trên ảnh biển, hữu ích khi cần phát hiện ký tự bị dính/cắt hoặc dựng lại khoảng trống.
- Số ký tự thường là 7–9; biển hai dòng thường 3–4 ký tự dòng trên và 4–5 ký tự dòng dưới.
- Không có confidence theo từng ký tự. Nếu cần, WP3 phải tự tính từ bộ phân loại hoặc từ khoảng cách giữa các box.
- Nếu `num_chars == 0`, không nên coi là biển hợp lệ; nên trả lỗi hoặc yêu cầu WP1 cắt lại.
- Cảnh báo: một số ảnh thật còn mảnh khung sát biên bị đếm thành ký tự. WP3 nên kiểm tra thêm số ký tự, hình dạng patch và xác suất phân loại thấp.

## 6. CLI

```powershell
# Ảnh xe: chạy WP1 rồi WP2
.\.venv\Scripts\python.exe run_wp2.py 'duong-dan-anh.jpg'

# Ảnh đã là biển cắt sẵn
.\.venv\Scripts\python.exe run_wp2.py 'duong-dan-bien.png' --plate

# Đổi thư mục ra và kích thước chuẩn hóa
.\.venv\Scripts\python.exe run_wp2.py 'duong-dan-anh.jpg' --output outputs --size 32
```

CLI ghi vào `outputs/` (hoặc `--output`):

| Tệp | Nội dung |
|---|---|
| `wp2_plate.png` | Ảnh biển đầu vào WP2 |
| `wp2_binary.png` | Ảnh nhị phân sạch |
| `wp2_characters.png` | Lưới ký tự 32×32 kèm số thứ tự |
| `wp2_result.json` | `line_type`, `num_chars`, `positions`, `line_indices`, `line_boxes`, `binarization`, `normalized_size`; thêm `wp1_bbox`, `wp1_angle` nếu chạy qua WP1 |

## 7. Kiểm thử và đánh giá

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe evaluate_wp2.py --count 100 --seed 2026 `
  --real-split 'Vietnam License Plate.v2i.coco\test' --real-limit 60
```

Xem thêm [báo cáo đánh giá WP2](../reports/wp2_evaluation.md) và [demo pipeline](../demo/wp2_pipeline.png).
