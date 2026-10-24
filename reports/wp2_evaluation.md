# Đánh giá WP2 – Tách dòng, tách ký tự và chuẩn hóa

WP2 nhận ảnh biển đã được WP1 cắt và chỉnh phối cảnh (`plate_normalized`), sau đó tách dòng, tách từng ký tự và chuẩn hóa về ảnh xám 32×32 nền đen, ký tự trắng. Đầu ra này là đầu vào trực tiếp của WP3.

## 1. Cách đánh giá

Tập dữ liệu công khai chỉ có box biển số, không có box ký tự. Vì vậy WP2 được đo theo hai hướng:

- **Benchmark tổng hợp có ground truth chính xác:** 100 biển cho mỗi mức `easy`, `typical`, `hard` (tổng 300 biển), seed `2026`, chia đều biển một dòng và hai dòng. Bộ sinh dùng font Noto Sans Condensed Bold (fallback DejaVu/Liberation/Arial), ba màu biển trắng/vàng/xanh, có xoay, phối cảnh, mờ, thay đổi sáng/tương phản và nhiễu. Box ký tự ground truth được căn theo đúng pixel sau biến đổi.
- **Kiểm tra ảnh thật:** 60 ảnh đầu tiên trong `test` có đúng một box nhãn. Chỉ các ảnh WP1 phát hiện đúng (IoU box biển ≥ 0,5) mới được đưa vào kiểm tra. Vì không có nhãn ký tự, phần này chỉ đo phân bố số ký tự, kiểu dòng, thời gian chạy và kiểm tra bằng mắt trên montage 20 mẫu. **Không dùng số liệu ảnh thật để tuyên bố độ chính xác ký tự.**

Cách ghép box: mỗi box dự đoán được ghép một-một với box ground truth có IoU lớn nhất, ngưỡng 0,5; mỗi box chỉ dùng một lần. Các chỉ số:

| Chỉ số | Định nghĩa |
|---|---|
| Precision / Recall / F1 | Theo TP/FP/FN của box ký tự |
| Segmentation accuracy | Recall của box ký tự (TP / (TP + FN)) |
| Exact-plate accuracy | Tất cả ký tự ground truth đều được ghép và không có box thừa |
| Line separation accuracy | `line_type` dự đoán trùng ground truth |
| Output size consistency | Mọi patch là `uint8` kích thước 32×32 |
| Glyph height ±5% | Tỷ lệ patch có chiều cao phần mực nằm trong ±5% quanh trung vị |

## 2. Kết quả benchmark tổng hợp

| Mức | TP / FP / FN | Precision | Recall | F1 | Segmentation accuracy | Exact-plate | Line separation | 32×32 | Cao ±5% | Thời gian |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Easy | 804 / 0 / 0 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 1,000 | 3,07 ms |
| Typical | 804 / 1 / 0 | 0,999 | 1,000 | 0,999 | 1,000 | 0,990 | 1,000 | 1,000 | 1,000 | 2,99 ms |
| Hard | 800 / 4 / 4 | 0,995 | 0,995 | 0,995 | 0,995 | 0,960 | 1,000 | 1,000 | 1,000 | 3,01 ms |

Mục tiêu brief và kết quả:

| Mục tiêu | Kết quả | Kết luận |
|---|---:|---|
| Segmentation accuracy ≥ 0,90 | 0,995 – 1,000 | Đạt |
| Line separation ≥ 0,95 | 1,000 | Đạt |
| Kích thước ký tự nhất quán ±5% | 100% patch | Đạt |
| Ảnh ra 32×32, trắng trên đen | 100% patch | Đạt |

Chi tiết theo kiểu dòng:

| Mức | 1 dòng (TP/FP/FN) | 2 dòng (TP/FP/FN) | Line accuracy 1 dòng | Line accuracy 2 dòng |
|---|---:|---:|---:|---:|
| Easy | 400 / 0 / 0 | 404 / 0 / 0 | 50/50 | 50/50 |
| Typical | 400 / 1 / 0 | 404 / 0 / 0 | 50/50 | 50/50 |
| Hard | 398 / 2 / 2 | 402 / 2 / 2 | 50/50 | 50/50 |

Chiều cao phần mực sau chuẩn hóa trung bình 21,97 – 21,99 px, độ lệch chuẩn 0,08 – 0,18 px. Toàn bộ 300 biển cho ra đúng 32×32; các sai khác còn lại chỉ là box thừa/thiếu hoặc IoU dưới ngưỡng, không có lỗi kích thước đầu ra.

Thời gian trên chỉ tính WP2, khi ảnh biển đã được cắt sẵn. Trung vị khoảng 3,0 ms/biển. Chi phí đầu-cuối chủ yếu nằm ở WP1 (trung bình 157,6 ms/ảnh trong báo cáo WP1).

## 3. Phân tích lỗi trên benchmark

- **Typical – 1 false positive:** một mảnh khung dọc sát biên phải bị tính thành ký tự thứ 9. Đây là lỗi còn lại của bước lọc khung, không phải lỗi tách dòng.
- **Hard – 4 lỗi, mỗi biển lệch đúng 1 ký tự:** cả bốn trường hợp đều liên quan đến chữ số `1` dưới góc nghiêng/ phối cảnh mạnh. Số box dự đoán vẫn bằng số box ground truth (8/8 hoặc 9/9), nhưng box của `1` lệch vài pixel nên IoU xuống dưới 0,5. Không có lỗi đếm ký tự ở mức hard.
- Không có biển nào bị tách sai số dòng: 300/300 trường hợp đúng `1_line`/`2_line`.

Các lỗi còn lại chủ yếu là biên (edge case) của lọc khung và độ nhạy vị trí của ký tự hẹp, không phải lỗi cấu trúc của pipeline.

## 4. Kiểm tra trên ảnh thật

Trong 60 ảnh có một box nhãn, WP1 phát hiện đúng 41 ảnh (68,3%). Đây là ảnh thật đã qua WP1, không phải ảnh crop thô. Kết quả WP2 trên 41 ảnh:

| Số ký tự | 1 | 2 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Số biển | 1 | 2 | 1 | 1 | 7 | 25 | 2 | 2 |

- 25/41 biển (61,0%) cho ra 8 ký tự.
- 37/41 biển (90,2%) nằm trong khoảng hợp lý 6–10 ký tự; 34/41 (82,9%) nằm trong khoảng 7–9.
- 23 biển một dòng, 18 biển hai dòng.
- Phương pháp nhị phân được chọn: Otsu 28, adaptive 9, central 4.
- Thời gian WP2: trung bình 5,92 ms, trung vị 3,84 ms/biển.

Montage kiểm tra bằng mắt: [demo/wp2_real_audit.png](../demo/wp2_real_audit.png). Nhìn chung biển một dòng và hai dòng được tách đúng số ký tự, box bám sát glyph, ảnh 32×32 giữ được nét chữ.

### Hạn chế của kiểm tra ảnh thật

1. **Ba trường hợp 1–2 ký tự** là ảnh WP1 cắt quá chặt/zoom vào một phần biển, không phải lỗi nhị phân của WP2. Ví dụ `Tgmt_0741`, `Tgmt_0622`, `Tgmt_0750`.
2. **Mảnh khung sát biên vẫn có thể bị đếm là ký tự.** `Tgmt_0579` thực tế có 7 ký tự nhưng trả 8 do mảnh khung bên phải; `Tgmt_0629` có 8 ký tự nhưng trả 9 do mảnh khung bên trái.
3. **Số ký tự đúng không đồng nghĩa nội dung đúng.** `Tgmt_0675` trả đúng 8 box nhưng box cuối là chữ `1` bị dính/cắt cùng mảnh khung, nên patch 32×32 thứ 8 không còn nguyên dạng.
4. Không có nhãn ký tự trên ảnh thật, nên các số 90,2% và 82,9% chỉ là **độ hợp lý của số ký tự**, không phải độ chính xác nhận dạng. Không thể suy ra accuracy ký tự từ các số này.
5. 19/60 ảnh còn lại WP1 không phát hiện hoặc phát hiện sai box. Vì vậy độ chính xác đầu-cuối vẫn bị giới hạn bởi WP1; WP1 chưa đạt mục tiêu recall/F1.

## 5. Kết luận

WP2 đạt các mục tiêu kỹ thuật trên benchmark tổng hợp có ground truth: segmentation 0,995–1,000, tách dòng 1,000, kích thước 32×32 và chiều cao ký tự nhất quán 100%, thời gian khoảng 3 ms/biển. Đầu ra đúng định dạng để bàn giao cho WP3.

Trên ảnh thật, pipeline cho kết quả hợp lý về số ký tự và hình thức, nhưng chưa thể kết luận độ chính xác ký tự do thiếu nhãn. Hai điểm cần xử lý ở vòng sau: lọc mảnh khung sát biên và cải thiện chất lượng crop của WP1. Không nên tuyên bố toàn pipeline đã hoàn thành khi WP1 còn dưới mục tiêu recall.

## 6. Tái lập

```powershell
# Benchmark tổng hợp + audit ảnh thật, xuất JSON ra màn hình
.\.venv\Scripts\python.exe evaluate_wp2.py --count 100 --seed 2026 `
  --real-split 'Vietnam License Plate.v2i.coco\test' --real-limit 60 `
  --audit-output demo\wp2_real_audit.png

# Chỉ benchmark tổng hợp (không truyền --real-split)
.\.venv\Scripts\python.exe evaluate_wp2.py --count 100 --seed 2026

# Sinh lại bộ ảnh tổng hợp (không commit dataset)
.\.venv\Scripts\python.exe scripts\make_synthetic_wp2.py --count 150 --seed 42 `
  --output data\synthetic_wp2 --showcase demo\wp2_synthetic.png

# Demo trên một biển thật đã qua WP1
.\.venv\Scripts\python.exe -m demo.make_wp2_demo

# Kiểm thử
.\.venv\Scripts\python.exe -m pytest -q
```

Trên Linux/macOS, thay `.\.venv\Scripts\python.exe` bằng `python` (hoặc `.venv/bin/python`).
