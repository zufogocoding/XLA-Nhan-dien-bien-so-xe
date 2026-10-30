# Vì sao điểm benchmark thấp — chẩn đoán có số liệu

Cập nhật: 30/10/2026. Báo cáo này tách bốn loại "điểm" thường bị gộp:
box WP1 độc lập, box của bộ chọn vùng ứng dụng, chuỗi OCR trên crop, và
accuracy toàn cảnh. Chỉ số thấp ở lớp nào có nguyên nhân khác nhau; không
dùng chỉ số của lớp này để kết luận lớp khác.

Tái lập chẩn đoán box:

```bash
python scripts/diagnose_wp1_failures.py
```

Kết quả lưu tại [wp1_failure_diagnosis.json](wp1_failure_diagnosis.json).

## Kết luận ngắn

1. **Nút thắt của WP1 là sinh ứng viên, không phải xếp hạng.** Trong 48 FN
   của top-1, có **44 box không có bất kỳ proposal đúng nào trong top 10**.
   Với 36/44 box này, IoU tốt nhất với mọi proposal vẫn dưới 0,10 — detector
   gần như không nhìn thấy biển, nên đổi threshold xếp hạng không cứu được.
2. **Giới hạn diện tích 30% là lỗi thật nhưng chỉ giải thích tối đa 4 FN.**
   9 box ground truth chiếm trên 30% ảnh đều bị bỏ; nới cap lên 1,0 cứu được
   4/9. Đây là lỗi ảnh chụp cận cảnh, không phải nguyên nhân chính của F1 thấp.
3. **Trả cả top 10 là đánh đổi rất tệ.** Top 10 đổi thêm 4 TP nhưng thêm 109
   FP: precision 0,879 → 0,504, F1 0,792 → 0,601. Vì vậy top-1 là lựa chọn
   đúng cho hợp đồng một biển; ảnh nhiều biển cần một lớp chọn/lọc riêng.
4. **Category 2 khó hơn category 1.** Recall top-1 là 74/95 = 0,779 cho
   category 1 và 50/77 = 0,649 cho category 2. Chênh lệch nhất quán với nhóm
   biển hai dòng/xe máy, nhưng nguồn COCO không định nghĩa category, nên chỉ
   ghi là tương quan.
5. **Điểm chuỗi 69,46% không phải classifier hỏng.** Accuracy ký tự trên crop
   nhãn là 96,53%; với biển 9 ký tự, nếu lỗi độc lập thì trần lý thuyết là
   `0,9653^9 ≈ 72,8%`. Đo được 69,46% nằm sát trần đó. Muốn đạt 75% cho chuỗi
   9 ký tự cần khoảng 96,84% mỗi ký tự, trước cả lỗi tách dòng.
6. **Chưa có bằng chứng accuracy toàn cảnh 70%.** COCO chỉ có nhãn box, không
   có nhãn chuỗi; 96,53% và 69,46% đo trên hai tập crop khác nhau. Không được
   ghép chúng thành accuracy WP1→WP4.

## 1. WP1 độc lập: 124/17/48, F1 0,7923

Đo trên 169 ảnh / 172 box test, IoU ≥ 0,5, tối đa một box mỗi ảnh:

| Phạm vi | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Top-1 WP1 độc lập | 124 | 17 | 48 | 0,8794 | 0,7209 | 0,7923 |
| Trả cả top-10 proposal | 128 | 126 | 44 | 0,5039 | 0,7442 | 0,6009 |

Top-10 chỉ thêm 4 TP. Nghĩa là **44 trong 48 FN không có proposal đúng trong
top 10**; bài toán không phải "proposal đúng bị xếp sau". Phân bố IoU tốt nhất
của 44 box bị bỏ:

| IoU tốt nhất với mọi proposal top-10 | Số box |
|---|---:|
| < 0,10 | 36 |
| 0,10–0,30 | 2 |
| 0,30–0,50 | 6 |

36 box gần như không chồng lấn. Đây là lỗi của bộ sinh contour/mask (Canny,
black-hat/Sobel, HSV, morphology) trên ảnh khó: biển quá nhỏ, quá mờ, dính
thân xe, hoặc bị cắt bởi khung. Xếp hạng lại không thể tạo ra box chưa tồn tại.

### Giới hạn diện tích 30%

`find_candidates()` mặc định `max_area_fraction=0.30`. Trong test có 9 ảnh,
mỗi ảnh đúng 1 box chiếm trên 30% diện tích:

| Điều kiện | Box lớn bắt được |
|---|---:|
| Cap mặc định 0,30 | 0/9 |
| Nới cap lên 1,0 | 4/9 |

Vậy cap gây ra tối đa 4/48 FN (8,3% recall). 5 box còn lại vẫn trượt khi nới
cap, nên không thể quy toàn bộ cho ngưỡng. Hướng đúng là tách một nhánh
close-up hoặc cho phép cap lớn hơn có kiểm soát, rồi đo lại trên valid; không
hạ cap mù quáng vì sẽ tăng FP trên ảnh thường.

### Theo category

| Category | Số box | TP top-1 | FN top-1 | Recall top-1 |
|---|---:|---:|---:|---:|
| 1 | 95 | 74 | 21 | 0,779 |
| 2 | 77 | 50 | 27 | 0,649 |

17 FP không gắn được với category nào nếu không có box khớp; vì vậy không
tính precision/F1 riêng cho từng category một cách tùy ý. Nếu quy toàn bộ 17
FP cho category 2 như giả định xấu nhất, precision category 2 là
`50/67 = 0,746`; con số này là **precision**, không phải F1. COCO không giải
thích category 1/2, nên chỉ kết luận category 2 đang yếu hơn.

### Bộ chọn vùng của ứng dụng

Bộ chọn vùng dùng WP2–WP4 để kiểm tra nhiều proposal, không phải WP1 độc lập:

| Phạm vi | TP | FP | FN | Precision | Recall | F1 | Trung bình |
|---|---:|---:|---:|---:|---:|---:|---:|
| WP1 độc lập top-1 | 124 | 17 | 48 | 0,8794 | 0,7209 | 0,7923 | 179,7 ms |
| Bộ chọn vùng ứng dụng | 138 | 23 | 34 | 0,8571 | 0,8023 | 0,8288 | 1.658,9 ms |

Bộ chọn vùng đạt cả ba ngưỡng box của ứng dụng, nhưng đổi 14 TP lấy 6 FP và
tăng thời gian khoảng 9 lần. Đây là **điểm box của ứng dụng**, không chứng
minh WP1 độc lập đã đạt Recall/F1. Nó cũng chưa đo chuỗi đúng.

## 2. Vì sao chuỗi OCR còn 69,46%

Trên 478 crop test có nhãn, cùng model SVM+HOG+LBP:

| Chỉ số | Kết quả | Mục tiêu |
|---|---:|---:|
| Đúng nguyên chuỗi | 0,6946 | ≥ 0,75 |
| CER | 0,0936 | ≤ 0,15 |
| WER (một biển = một token) | 0,3054 | ≤ 0,20 |
| Accuracy ký tự trên 3.834 ký tự cắt theo nhãn | 0,9653 | ≥ 0,85 |

Điểm mấu chốt: 96,53% là accuracy **từng ký tự** trên crop đã cắt đúng, còn
69,46% là **cả chuỗi** sau tách dòng và ghép chuỗi. Với 9 ký tự:

```text
0,9653^9 ≈ 0,728
```

Ngay cả khi lỗi từng ký tự độc lập và không có lỗi tách/ghép, trần chuỗi chỉ
khoảng 72,8%; đo được 69,46% là sát trần. Để đạt 75% cho 9 ký tự cần
`0,75^(1/9) ≈ 0,9684`, tức khoảng 96,84% mỗi ký tự. Với biển 8 ký tự, trần
hiện tại là `0,9653^8 ≈ 75,4%`, vừa đủ mục tiêu. Vì vậy:

- Sửa classifier theo hướng "tăng vài phần trăm accuracy ký tự" chỉ đem lại
  cải thiện nhỏ nếu không xử lý tách dòng và cặp ký tự nhầm.
- WER ở đây dùng **một biển = một token**, nên về mặt toán học nó đúng bằng
  `1 − đúng nguyên chuỗi = 0,3054`. Đây không phải phép đo độc lập; mục tiêu
  WER ≤ 0,20 tương đương đúng chuỗi ≥ 80%, khắt khe hơn mục tiêu 75%. Muốn
  đạt WER phải giảm hẳn tỉ lệ biển sai, không chỉ giảm số ký tự sai.
- Không được báo 96,53% như accuracy đọc biển. Báo cáo WP3 đã ghi rõ đây là
  accuracy ký tự trên crop nhãn.

Các lỗi còn lại tập trung ở biển hai dòng, ký tự dính/đứt nét, cặp dễ nhầm
(O/Q, 8/B, 0/D), và ảnh mờ. Phần xử lý ảnh ngày 24/10 đã nâng chuỗi từ 48,74%
lên 69,46% và CER từ 23,37% xuống 9,36%, nên hướng cải thiện đúng là tiếp tục
sửa segmentation/line grouping, không phải thay model ngay.

## 3. Ảnh nhiều biển: số đo và giới hạn

Lớp `src/multi_plate.py` là lớp ứng dụng, không thay hợp đồng `detect_plate()`
một biển. Nó lấy proposal WP1 (thêm tile cho ảnh lớn), chạy WP2–WP4 cho từng
vùng, lọc theo confidence/định dạng và khử trùng lặp.

Đo box trên valid, IoU ≥ 0,5, không có nhãn chuỗi:

| Tập | Ảnh | Box GT | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Valid, mọi box | 118 | 286 | 94 | 9 | 192 | 0,9126 | 0,3287 | 0,4833 |
| Valid, box ≥1% diện tích ảnh | 23 | 47 | 28 | 2 | 19 | 0,9333 | 0,5957 | 0,7273 |

Toàn bộ valid có rất nhiều biển nền nhỏ; chỉ cần một biển 20×10 px cũng thành
FN, nên recall 0,329 không có nghĩa "ứng dụng bỏ 2/3 biển chính". Khi lọc box
≥1% diện tích, F1 là 0,727. Top-1 trong tập prominent chỉ đạt 17/1/30
(P 0,944, R 0,362, F1 0,523): biển phụ vẫn thường được xếp sau biển chính.

Test chỉ có **3 ảnh / 6 box** nhiều biển, kết quả 3/0/3 (P 1,0, R 0,5,
F1 0,667). Đây là số báo cáo, **không dùng để chỉnh threshold**; valid mới là
tập chọn cấu hình.

### Demo thật

| Ảnh | Kích thước | Box tìm được | Chuỗi đúng định dạng | Thời gian |
|---|---|---:|---:|---:|
| `Dieu_0491...jpg` (2 biển thật, ảnh train) | 640×640 | 2/2 | 2/2: `59B-491.36`, `60B6-087.83` | 1.047 ms |
| Collage 4 ảnh thật | 1920×1920 | 8/8 | 4/8 | 3.430 ms |

Collage là 4 ảnh ghép, không phải cảnh giao thông tự nhiên; hai góc có cùng
biển `60-B6 087.83` trên hai xe khác nhau. Trong 8 chuỗi, 5 chuỗi đúng ký tự
(một chuỗi đúng số nhưng thiếu định dạng), 3 chuỗi sai. Cả hai ảnh demo lấy từ
train, chỉ dùng để kiểm tra chức năng, không dùng báo cáo accuracy. Kết quả cho
thấy box localization tốt hơn OCR chuỗi, đúng với kết luận ở trên.

Ảnh: [kết quả 2 biển](../demo/multi_plate_real_result.jpg),
[input collage](../demo/multi_plate_collage_input.jpg),
[kết quả collage](../demo/multi_plate_collage_result.jpg).

## 4. Thứ tự ưu tiên sửa

1. **Sinh proposal cho WP1** — mục tiêu trước mắt là kéo 44 box không có
   proposal nào vào top-10. Ưu tiên ảnh nhỏ/mờ/dính thân xe và nhánh close-up
   cho box >30%. Đo trên valid, không dùng test để chọn.
2. **Tách dòng và ghép chuỗi WP2** — vì trần chuỗi bị chặn bởi accuracy từng
   ký tự, cải thiện nhỏ ở classifier không đủ. Tập trung biển hai dòng, ký tự
   dính/đứt, cặp nhầm.
3. **Giữ top-1 cho hợp đồng một biển** — không trả top-10 trần, vì precision
   sụp còn 0,504. Ảnh nhiều biển dùng `recognize_plates()` với lọc confidence,
   định dạng và khử trùng lặp.
4. **Đo end-to-end bằng tập ảnh giao thông có nhãn chuỗi độc lập** — chỉ khi
   có tập này mới được kết luận mục tiêu 70%. COCO hiện tại không đủ.
5. **Hiệu chuẩn confidence/status** — `confidence` hiện là điểm heuristic,
   không phải xác suất; `recognized` chỉ nói đúng mẫu/mã, không nói đúng biển.

## 5. Phạm vi và tái lập

- Box: COCO test 169 ảnh / 172 box, IoU ≥ 0,5.
- Chuỗi: 478 crop test của split OCR riêng, 3.834 ký tự; không phải ảnh COCO.
- Multi-plate: valid 118 ảnh / 286 box; prominent 23 ảnh / 47 box.
- Không chỉnh threshold trên test. Các con số test chỉ để báo cáo.
- Lệnh tái lập:

```bash
python scripts/diagnose_wp1_failures.py
python scripts/evaluate_multi_plate.py --min-plate-area 0.01 --output reports/wp_multi_plate_evaluation_prominent.json
python scripts/evaluate_multi_plate.py --output reports/wp_multi_plate_evaluation.json
python scripts/demo_multi_plate.py "Vietnam License Plate.v2i.coco/train/Dieu_0491_png.rf.47bdb4078d48c84e888f77bfb3363123.jpg"
```

Xem thêm [WP1](wp1_evaluation.md), [điều tra nhánh](wp1_branch_investigation.md),
[chuỗi OCR](wp3_sequence_evaluation.md), [WP4](wp4_evaluation.md) và
[tiến độ](implementation_status.md).
