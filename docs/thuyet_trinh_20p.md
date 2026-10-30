# THIẾT KẾ THUYẾT TRÌNH 20 PHÚT — NHÓM 4 NGƯỜI

**Đề tài:** Nhận diện biển số xe Việt Nam bằng thị giác máy tính truyền thống
**Hình thức:** 18 slide chính + 5 slide dự phòng, demo trực tiếp
**Thời lượng:** 20:00 trình bày + 5–7 phút Q&A
**Người trình bày:** A (WP1), B (WP2), C (WP3), D (WP4 + demo + điều phối)

---

## 1. Nguyên tắc thiết kế

- **Một slide một ý.** Không slide nào có quá 6 dòng chữ hoặc quá 2 bảng.
- **Số phải to.** Con số quan trọng đặt 60–80 pt, không nằm trong đoạn văn.
- **Không đọc chữ trên slide.** Slide là điểm tựa; lời nói mới là nội dung.
- **Mỗi người sở hữu một con số.** A: 0,7923. B: 92,57%. C: 96,53%. D: 69,46%.
- **Nói đúng phạm vi.** Không nói "96,53% là độ chính xác biển số".
- **Màu:** nền trắng, chữ xanh đậm `#0F2A44`, nhấn cam `#E86A33`, xám `#6B7280`.
- **Font:** Inter hoặc Be Vietnam Pro; tiêu đề 32–36 pt, nội dung 20–24 pt.
- **Tỉ lệ:** 16:9. Logo trường góc trên phải, số trang góc dưới phải.
- **Handoff 5 giây:** người trước nói câu bắc cầu, người sau bắt đầu ngay.

---

## 2. Run sheet 20 phút

| Mốc | Thời lượng | Người | Nội dung | Slide |
|---|---:|---|---|---|
| 0:00–0:45 | 0:45 | D | Mở đầu, đội, agenda, hook | 1–2 |
| 0:45–5:15 | 4:30 | A | Bài toán, pipeline, WP1 | 3–6 |
| 5:15–8:30 | 3:15 | B | WP2 | 7–9 |
| 8:30–12:45 | 4:15 | C | WP3 | 10–12 |
| 12:45–15:15 | 2:30 | D | WP4 | 13–14 |
| 15:15–17:15 | 2:00 | D | Demo | 15 |
| 17:15–19:15 | 2:00 | D | Kết quả, hạn chế, hướng phát triển | 16–18 |
| 19:15–20:00 | 0:45 | D | Kết thúc, mời Q&A | 18 |

**Điểm kiểm tra giờ (bắt buộc):**

- 5:15 — A phải kết thúc WP1.
- 8:30 — B phải kết thúc WP2.
- 12:45 — C phải kết thúc WP3.
- 15:15 — D phải bắt đầu demo.
- 19:15 — D phải bắt đầu câu kết.

Nếu trễ quá 1 phút: bỏ slide 12 (chi tiết confusion), giữ nguyên demo.

---

## 3. Thiết kế slide chi tiết

### Slide 1 — Tiêu đề

**Nội dung:**

```text
NHẬN DIỆN BIỂN SỐ XE VIỆT NAM
Bằng thị giác máy tính truyền thống

Nhóm 4 — Lớp …
Thành viên: A, B, C, D
GVHD: …
```

**Hình:** ảnh `demo/multi_plate_real_result.jpg` mờ 20% làm nền.
**Người:** D. **Thời gian:** 0:00–0:15.

**Lời nói:**

> "Chào thầy/cô và các bạn. Nhóm em làm hệ thống nhận diện biển số xe Việt
> Nam bằng OpenCV và học máy truyền thống, chạy hoàn toàn trên CPU. Trong 20
> phút tới, bọn em sẽ đi qua bốn tầng của pipeline, chỉ ra tầng nào đang là
> nút thắt, và demo trực tiếp."

### Slide 2 — Vấn đề & mục tiêu

**Nội dung:** 3 con số lớn:

```text
4 tầng      →     58 test     →     1 mục tiêu
WP1–WP4          passed            end-to-end 70%
```

**Hình:** sơ đồ 4 khối pipeline thu nhỏ.
**Người:** D. **Thời gian:** 0:15–0:45.

**Lời nói:**

> "Bài toán có hai phần: tìm biển ở đâu, và đọc trên biển có gì. Bọn em chia
> thành bốn giai đoạn độc lập, mỗi giai đoạn có hợp đồng riêng và có thể đo
> riêng. Mục tiêu cuối là đọc đúng nguyên biển, nhưng điểm quan trọng của đồ
> án là: bọn em đo được **tầng nào đang làm sai**, thay vì chỉ báo một con số
> tổng."

### Slide 3 — Pipeline 4 tầng

**Nội dung:** sơ đồ ngang:

```text
Ảnh → [WP1: phát hiện] → [WP2: tách ký tự] → [WP3: phân loại] → [WP4: hậu xử lý]
        box, crop         32×32, thứ tự        chuỗi thô          biển hợp lệ
```

**Hình:** 4 icon minh họa, mũi tên lớn.
**Người:** A. **Thời gian:** 0:45–1:00.

**Lời nói:**

> "Em phụ trách WP1. Trước khi vào chi tiết, em chốt luồng: WP1 trả box và
> crop biển; WP2 trả danh sách ký tự 32×32 đúng thứ tự; WP3 trả chuỗi thô và
> confidence; WP4 kiểm tra mẫu, mã tỉnh và lưu database. Bốn tầng không gọi
> ngược lên nhau."

### Slide 4 — WP1: tiền xử lý & sinh ứng viên

**Nội dung:** 3 nhánh song song:

```text
Canny + morphology  ─┐
Black-hat / Sobel   ─┼→  contour  →  lọc hình học  →  ứng viên
HSV color masks     ─┘
```

**Hình:** `demo/wp1_before_after.png` (phần trái: ảnh gốc + box).
**Người:** A. **Thời gian:** 1:00–2:15.

**Lời nói:**

> "WP1 không dùng một phép duy nhất. Bọn em chạy ba nguồn song song: Canny để
> bắt cạnh, black-hat để bắt viền tối trên nền sáng, và HSV để bắt màu biển.
> Mỗi nguồn cho contour, sau đó lọc theo diện tích, tỉ lệ, độ đặc. Lý do phải
> ba nguồn: biển trắng trên xe trắng rất khó bắt chỉ bằng cạnh; biển tối trên
> xe tối lại khó bắt bằng màu. Ba nguồn bù nhau."

**Câu chuyển:** "Sau khi có ứng viên, WP1 cần xếp hạng."

### Slide 5 — WP1: scoring & HOG/SVM re-ranker

**Nội dung:** công thức rút gọn + 2 tầng:

```text
Tầng 1: score = 0,23·shape + 0,18·edge + 0,19·size + 0,13·color
              + 0,08·rect + 0,10·char + 0,05·color_boost + 0,07·glyph
Tầng 2: final = 0,4·heuristic + 0,6·P_SVM     (gate P ≥ 0,35)
```

**Hình:** ảnh HOG `demo/hog_character.png` bên phải, thu nhỏ.
**Người:** A. **Thời gian:** 2:15–3:15.

**Lời nói:**

> "Tầng một là heuristic tám thành phần, trong đó shape và size nặng nhất.
> Tầng hai là HOG 64×32, 756 chiều, cộng sáu thống kê crop, đưa vào SVM đã
> hiệu chuẩn. Điểm cuối là trung bình có trọng số 0,4–0,6. Điểm này **không
> phải xác suất** — nó chỉ để xếp hạng. Nếu file model thiếu, hệ thống tự
> quay về heuristic, không sập."

### Slide 6 — WP1: kết quả & chẩn đoán

**Nội dung:** bảng 3 dòng + 1 con số lớn:

```text
TP/FP/FN = 124 / 17 / 48
P = 0,8794   R = 0,7209   F1 = 0,7923

44/48 FN  →  không có proposal đúng trong top 10
36/44     →  IoU tốt nhất < 0,10
```

**Hình:** biểu đồ cột P/R/F1; biểu đồ tròn 44/48.
**Người:** A. **Thời gian:** 3:15–5:15.

**Lời nói:**

> "Đây là kết quả thật: precision đạt, recall và F1 chưa đạt. Nhưng điều quan
> trọng hơn là chẩn đoán. Bọn em thử trả top-10 thay vì top-1: chỉ thêm 4 TP
> nhưng thêm 109 FP, F1 giảm còn 0,60. Nghĩa là proposal đúng không hề bị xếp
> sau — nó **không tồn tại**. 44 trong 48 FN không có bất kỳ proposal đúng nào
> trong top 10; 36 trường hợp IoU tốt nhất dưới 0,10. Vì vậy sửa threshold
> không cứu được; phải sửa bộ sinh ứng viên. Đây là kết luận định lượng lớn
> nhất của nhóm."

**Câu chuyển:** "Box đã có, giờ tách ký tự bên trong."

### Slide 7 — WP2: vì sao một ngưỡng không đủ

**Nội dung:** 4 phương án nhị phân:

```text
Otsu  |  CLAHE+Otsu  |  Adaptive 31  |  Adaptive 51
```

**Hình:** 4 ảnh nhị phân nhỏ cùng một biển, khác ngưỡng.
**Người:** B. **Thời gian:** 5:15–6:15.

**Lời nói:**

> "WP2 nhận crop biển từ WP1. Vấn đề đầu tiên là nhị phân hóa: Otsu tốt khi
> sáng đều, nhưng trên biển có bóng đổ hoặc nét nhạt, Otsu làm mất chữ. Vì
> vậy bọn em không chọn một ngưỡng. Bọn em sinh bốn phương án, rồi để bước
> sau chọn phương án có ký tự hợp lý nhất. Đây là điểm thiết kế chính của
> WP2: biến một quyết định khó thành bài toán xếp hạng."

### Slide 8 — WP2: tách dòng & tách ký tự

**Nội dung:** projection profile:

```text
P_row(y) = Σ B(x,y)   →  tìm "thung lũng" giữa hai dòng
P_col(x) = Σ B(x,y)   →  tách ký tự
```

**Hình:** biểu đồ projection ngang có 2 đỉnh, đường cắt ở giữa.
**Người:** B. **Thời gian:** 6:15–7:15.

**Lời nói:**

> "Tách dòng dùng projection ngang: cộng số pixel foreground theo từng hàng.
> Hai dòng cho hai đỉnh, giữa là thung lũng. Bọn em chỉ cắt khi thung lũng ở
> giữa và hai bên có đủ foreground, để tránh cắt nhầm một dòng thành hai.
> Tách ký tự cũng dùng projection dọc, kết hợp connected components. Với ký
> tự dính, bọn em tách bằng erosion có kiểm soát; với nét đứt, ghép mảnh theo
> độ chồng trục x — nhưng không chèn ký tự giả."

### Slide 9 — WP2: chuẩn hóa & kết quả

**Nội dung:** 3 số lớn:

```text
Recall box ký tự   92,57%
Precision box      97,15%
Đúng số dòng       94,98%
```

**Hình:** một ký tự 32×32 trước/sau chuẩn hóa.
**Người:** B. **Thời gian:** 7:15–8:30.

**Lời nói:**

> "Ký tự được chuẩn hóa về 32×32, giữ tỉ lệ, padding 2 pixel, căn giữa. Không
> kéo giãn vì HOG rất nhạy với biến dạng hình học. Kết quả: recall 92,57%,
> precision 97,15%, đúng số dòng 94,98%. Con số 94,98% **không được làm tròn**
> thành 95% — mục tiêu là 95% và bọn em vẫn dưới. Đây là ví dụ cho nguyên tắc
> báo cáo trung thực của nhóm."

**Câu chuyển:** "Ký tự đã sạch, giờ phân loại."

### Slide 10 — WP3: HOG + LBP

**Nội dung:** hai nhánh đặc trưng:

```text
32×32 → HOG: 4×4 cell, 9 bin, 3×3 block → 324 chiều
      → LBP: 8 láng giềng, uniform, 10 bin → 10 chiều
      → concat = 334 chiều → SVM RBF (C=10)
```

**Hình:** `demo/hog_character.png` — gradient, cell, histogram.
**Người:** C. **Thời gian:** 8:30–9:45.

**Lời nói:**

> "WP3 nhận ký tự 32×32. HOG chia thành 4×4 cell, mỗi cell 9 bin hướng, gom
> block 2×2 và chuẩn hóa L2-Hys, ra 324 chiều. HOG mô tả **hình dạng nét**.
> LBP so sánh 8 láng giềng với tâm, lấy histogram 10 bin, mô tả **kết cấu**.
> Ghép lại thành 334 chiều. SVM kernel RBF vì dữ liệu 36 lớp không tách tuyến
> tính."

### Slide 11 — WP3: so sánh model & chọn

**Nội dung:** bảng 5 dòng, tô đậm dòng được chọn:

| Model | Dim | Test acc | Macro F1 |
|---|---:|---:|---:|
| SVM+HOG | 324 | 0,9650 | 0,8434 |
| SVM+LBP | 10 | 0,3965 | 0,1088 |
| **SVM+HOG+LBP** | **334** | **0,9653** | **0,8484** |
| kNN | 324 | 0,9559 | 0,8095 |
| RF | 324 | 0,9562 | 0,8077 |

**Hình:** confusion matrix thu nhỏ bên phải.
**Người:** C. **Thời gian:** 9:45–11:00.

**Lời nói:**

> "Bọn em huấn luyện năm model và chọn theo **macro F1 trên valid**, không
> theo accuracy thô, vì 36 lớp mất cân bằng. LBP một mình chỉ 0,3965 — gần
> như vô dụng. Nhưng ghép HOG+LBP tăng nhẹ cả accuracy lẫn macro F1, nên bọn
> em giữ. Điểm cần nói: chênh lệch giữa các model rất nhỏ, nên đừng kỳ vọng
> đổi model sẽ cứu được chuỗi."

### Slide 12 — WP3: trần chuỗi & confusion

**Nội dung:** một công thức lớn:

```text
0,9653^9 ≈ 72,8%
```

kèm 3 dòng:

```text
Đúng nguyên chuỗi: 69,46%
CER: 9,36%
WER: 30,54%
```

**Hình:** confusion matrix; highlight O/0, I/1, 8/B.
**Người:** C. **Thời gian:** 11:00–12:45.

**Lời nói:**

> "Đây là slide quan trọng nhất của em. Accuracy từng ký tự là 96,53%, nhưng
> một biển có 9 ký tự. Nếu lỗi độc lập, trần lý thuyết là 0,9653 mũ 9, khoảng
> 72,8%. Bọn em đo được 69,46% — sát trần. Nghĩa là classifier **không hỏng**;
> giới hạn nằm ở kiến trúc chấm từng ký tự rời. Muốn đạt 75% phải có 96,84%
> mỗi ký tự, trước cả lỗi tách dòng. Vì vậy hướng đúng là sửa tách dòng và
> cặp nhầm, không phải đổi model."

**Câu chuyển:** "Chuỗi thô đã có, giờ làm cho nó hợp lệ."

### Slide 13 — WP4: regex, sửa nhầm, mã tỉnh

**Nội dung:** 3 bước:

```text
1. Chuẩn hóa: bỏ - . khoảng trắng
2. Sửa 8 cặp: O↔0, I↔1, S↔5, B↔8, Z↔2, A↔4, G↔6, T↔7
   — chỉ sửa nếu vị trí cho phép và chuỗi sau sửa khớp mẫu
3. Tra 2 số đầu trong bảng mã đăng ký
```

**Hình:** ví dụ `30G-699.46` với các bước.
**Người:** D. **Thời gian:** 12:45–14:00.

**Lời nói:**

> "WP4 không đoán bừa. Ba mẫu regex: ô tô 5 số, ô tô 4 số, xe máy. Tám cặp
> nhầm chỉ được sửa nếu vị trí cho phép — vị trí 2 là chữ, các vị trí số là
> số — và chuỗi sau sửa phải khớp một mẫu hợp lệ. Nếu không, giữ nguyên. Hai
> số đầu tra bảng mã đăng ký. Nếu chuỗi khớp cả ô tô và xe máy, loại xe giữ
> `unknown`, không đoán."

### Slide 14 — Multi-plate: lớp ứng dụng

**Nội dung:** sơ đồ:

```text
Ảnh lớn → tile 1600px, overlap 20%
        → proposal WP1
        → WP2–WP4 cho từng vùng
        → lọc confidence + format
        → khử trùng lặp (IoU ≥ 0,55)
```

**Hình:** `demo/multi_plate_collage_result.jpg`.
**Người:** D. **Thời gian:** 14:00–15:15.

**Lời nói:**

> "Ảnh nhiều biển là một lớp ứng dụng, không phải thay đổi WP1. WP1 vẫn giữ
> hợp đồng một biển. Lớp này thêm tile cho ảnh lớn, chạy WP2–WP4 cho từng
> vùng, lọc theo confidence và định dạng, rồi khử trùng lặp. Trên valid, tập
> biển chính đạt F1 0,727; nhưng top-1 chỉ 0,523, nên thứ hạng biển phụ vẫn
> là hạn chế."

### Slide 15 — Demo trực tiếp

**Nội dung:** 3 bước, chữ lớn:

```text
1. Ảnh 2 biển  → 2/2 box, 2/2 chuỗi
2. Upload 1 ảnh → xem box, crop, ký tự
3. Bật "nhiều biển" → collage 8 box, 4 chuỗi
```

**Hình:** để trống — demo thật.
**Người:** D. **Thời gian:** 15:15–17:15.

**Lời nói:**

> "Bọn em demo trên giao diện thật. Đây là ảnh hai biển: hệ thống tìm đúng
> hai box và đọc đúng cả hai chuỗi. Tiếp theo là upload một ảnh mới, bật chế
> độ nhiều biển. Các bạn để ý: hệ thống tìm đủ 8 box trên collage, nhưng chỉ
> 4 chuỗi đúng định dạng. Đây chính là điều bọn em muốn chứng minh — **box
> tốt hơn OCR**, đúng với kết luận ở Chương V."

### Slide 16 — Kết quả tổng hợp

**Nội dung:** bảng 4 dòng, mỗi dòng một phạm vi:

| Phạm vi | Kết quả |
|---|---|
| WP1 độc lập | P 0,8794 / R 0,7209 / F1 0,7923 |
| Bộ chọn vùng ứng dụng | P 0,8571 / R 0,8023 / F1 0,8288 |
| OCR chuỗi | Exact 69,46% / CER 9,36% |
| Multi-plate prominent | F1 0,7273 |

**Hình:** 4 biểu đồ nhỏ, cùng thang đo.
**Người:** D. **Thời gian:** 17:15–18:15.

**Lời nói:**

> "Bốn con số này là bốn phạm vi khác nhau, không được cộng lại. WP1 độc lập
> F1 0,7923. Bộ chọn vùng ứng dụng 0,8288 nhưng chậm gấp chín lần và có OCR
> hỗ trợ. Chuỗi đúng 69,46%. Multi-plate prominent 0,7273. Bọn em không báo
> một con số tổng vì chưa có tập end-to-end có nhãn chuỗi."

### Slide 17 — Hạn chế & bài học

**Nội dung:** 3 cặp "tưởng vậy / hóa ra":

```text
Tưởng: threshold xếp hạng sai
Hóa ra: 44/48 FN không có proposal

Tưởng: classifier yếu
Hóa ra: trần 0,9653^9 ≈ 72,8%

Tưởng: multi-plate chỉ cần thêm box
Hóa ra: top-1 biển phụ chỉ F1 0,523
```

**Hình:** 3 icon.
**Người:** D. **Thời gian:** 18:15–19:00.

**Lời nói:**

> "Ba bài học. Một: nút thắt của WP1 là sinh proposal, không phải xếp hạng.
> Hai: classifier không yếu; kiến trúc chấm rời tạo trần 72,8%. Ba: multi-plate
> không chỉ là thêm box — thứ hạng biển phụ mới là vấn đề. Đây là lý do bọn em
> dành nhiều thời gian cho chẩn đoán thay vì chỉ chạy thêm model."

### Slide 18 — Hướng phát triển & kết thúc

**Nội dung:** 4 ưu tiên + câu kết:

```text
1. Sửa sinh proposal WP1 (ưu tiên 1)
2. Tách dòng & ký tự dính
3. Tập ảnh giao thông có nhãn chuỗi
4. Hiệu chuẩn confidence, Docker, tracking
```

**Hình:** mũi tên tiến hóa 4 bước.
**Người:** D. **Thời gian:** 19:00–20:00.

**Lời nói:**

> "Hướng tiếp theo rõ ràng: sửa sinh proposal WP1 trước, vì đó là nút thắt đã
> đo. Sau đó là tách dòng, rồi thu thập tập ảnh giao thông có nhãn chuỗi để
> đo end-to-end. Bọn em không hứa 70% khi chưa có tập đó. Cảm ơn thầy/cô và
> các bạn — bọn em sẵn sàng nhận câu hỏi."

---

## 4. Kịch bản demo (2 phút)

### 4.1. Chuẩn bị trước 10 phút

- [ ] Chạy server: `uvicorn api.main:app --host 127.0.0.1 --port 8000`
- [ ] Mở sẵn 3 tab: `/`, `/docs`, ảnh kết quả `demo/multi_plate_real_result.jpg`
- [ ] Chuẩn bị 2 file upload: một biển đơn, một ảnh nhiều biển
- [ ] Tắt thông báo, ẩn bookmark bar, zoom trình duyệt 110%
- [ ] Mở sẵn terminal dự phòng với lệnh CLI
- [ ] Điện thoại quay màn hình dự phòng (backup)

### 4.2. Kịch bản chính

| Bước | Thời gian | Thao tác | Lời nói |
|---|---:|---|---|
| 1 | 0:00–0:30 | Mở tab kết quả 2 biển | "Đây là ảnh 2 biển thật, hệ thống tìm 2/2 box và đọc đúng `59B-491.36`, `60B6-087.83`." |
| 2 | 0:30–1:15 | Upload ảnh đơn, bấm nhận diện | "Bây giờ upload ảnh mới. Các bạn thấy box, crop, 9 ký tự và chuỗi đã định dạng." |
| 3 | 1:15–1:45 | Bật checkbox "Ảnh có nhiều biển", upload collage | "Bật chế độ nhiều biển. Hệ thống tìm 8/8 box, nhưng chỉ 4/8 chuỗi đúng — đây là hạn chế bọn em đã nói." |
| 4 | 1:45–2:00 | Mở chi tiết một bản ghi | "Mỗi bản ghi lưu ảnh gốc, crop, ký tự, threshold và trạng thái để kiểm tra lại." |

### 4.3. Phương án dự phòng

| Tình huống | Xử lý |
|---|---|
| Server không lên | Mở ảnh `demo/multi_plate_real_result.jpg` và `demo/multi_plate_collage_result.jpg` đã lưu |
| Upload lỗi | Chạy CLI: `python scripts/demo_multi_plate.py "demo/multi_plate_collage_input.jpg"` |
| Mạng/trình duyệt lỗi | Phát video quay sẵn hoặc mở `outputs/multi_plate/result.json` |
| Demo chậm quá 2 phút | Bỏ bước 4, chỉ nói "chi tiết nằm trong lịch sử" |

### 4.4. Câu chốt sau demo

> "Demo này không phải benchmark. Nó chỉ chứng minh pipeline chạy được và cho
> thấy đúng vấn đề: box tốt hơn chuỗi. Con số chính thức nằm trong báo cáo,
> đo trên tập test, không phải ảnh demo."

---

## 5. Phân công Q&A

| Câu hỏi dự kiến | Người trả lời | Ý chính |
|---|---|---|
| Sao không dùng YOLO/CRNN? | A | Mục tiêu học thuật, giải thích từng tầng; YOLO là hướng phát triển, nhưng nút thắt hiện tại là proposal nên YOLO giải quyết đúng chỗ |
| Sao F1 WP1 chỉ 0,79? | A | 44/48 FN không có proposal trong top 10; 36/44 IoU < 0,10; không phải threshold |
| Sao không trả top-10? | A | Thêm 4 TP nhưng 109 FP; F1 0,792 → 0,601 |
| 96,53% mà sao chuỗi 69,46%? | C | Trần `0,9653^9 ≈ 72,8%`; 69,46% sát trần |
| Sao chọn HOG+LBP? | C | Macro F1 valid cao nhất; LBP một mình 0,3965 nhưng bổ trợ kết cấu |
| Sao không dùng CNN? | C | Dữ liệu nhỏ, cần giải thích; CNN là hướng phát triển |
| Multi-plate F1 thấp? | D | Valid có nhiều biển nền rất nhỏ; prominent 0,727; top-1 0,523 |
| Latency 1,6 giây? | D | Bộ chọn vùng chạy OCR nhiều lần; WP1 riêng 179,7 ms |
| Sao không tune cho đẹp? | D | Chọn trên valid, test chỉ báo cáo |
| Docker chạy chưa? | D | Cấu hình có, build chưa xác nhận do môi trường |
| Xe máy có tốt không? | B | Category 2 recall 0,649 vs 0,779; chưa có nhãn loại xe chính thức |
| Confidence có phải xác suất? | A | Không; là điểm xếp hạng heuristic, chưa hiệu chuẩn |

---

## 6. Luyện tập

### 6.1. Ba buổi tập

| Buổi | Mục tiêu | Cách làm |
|---|---|---|
| 1 | Thuộc dòng chảy, không cần đúng giờ | Mỗi người nói phần mình, bấm giờ riêng |
| 2 | Đúng giờ, khớp handoff | Chạy liên tục 20 phút, có người bấm giờ và ra hiệu |
| 3 | Giống thật, có demo và Q&A | Có người lạ nghe, hỏi 5 câu bất kỳ |

### 6.2. Câu bắc cầu giữa các phần

- A → B: "Box đã có, giờ tách ký tự bên trong."
- B → C: "Ký tự đã sạch và đúng thứ tự, giờ phân loại."
- C → D: "Chuỗi thô đã có, giờ làm cho nó hợp lệ."
- D → demo: "Nói thì dài, bọn em demo luôn."

### 6.3. Nếu bị run

- Nhìn vào một người ở giữa lớp, không nhìn màn hình.
- Nói chậm hơn bình thường 10%.
- Câu đầu tiên của mỗi slide đã thuộc lòng; các câu sau tự nhiên.
- Quên số: mở slide dự phòng, đọc số, rồi nói tiếp.

### 6.4. Những câu tuyệt đối không nói

- "Độ chính xác của hệ thống là 96,53%." → Phải nói "accuracy ký tự".
- "WP1 đạt F1 0,8288." → Phải nói "bộ chọn vùng ứng dụng".
- "Hệ thống đạt 70% end-to-end." → Chưa có tập nhãn chuỗi.
- "Demo chứng minh độ chính xác." → Demo chỉ kiểm tra chức năng.
- "Top-10 tốt hơn vì tìm được nhiều hơn." → F1 giảm còn 0,601.

---

## 7. Slide dự phòng

| Mã | Nội dung | Dùng khi |
|---|---|---|
| B1 | Bảng top-1 vs top-10, oracle 44/48 | Bị hỏi sâu về WP1 |
| B2 | 4 phương án nhị phân + kết quả từng phương án | Bị hỏi WP2 |
| B3 | Confusion matrix đầy đủ 36 lớp | Bị hỏi cặp nhầm |
| B4 | Sơ đồ API + schema SQLite | Bị hỏi triển khai |
| B5 | Bảng multi-plate đầy đủ (mọi box/prominent/test) | Bị hỏi multi-plate |

---

## 8. Checklist cuối cùng

- [ ] 18 slide chính đã xuất PDF, có backup USB.
- [ ] Demo chạy được trên máy trình bày, không phụ thuộc mạng.
- [ ] Mỗi người thuộc ít nhất 3 con số của phần mình.
- [ ] Đã tập 3 buổi, buổi cuối đúng 20:00.
- [ ] Đã thống nhất ai trả lời câu hỏi nào.
- [ ] Đã chuẩn bị câu mở và câu kết.
- [ ] Đã kiểm tra âm thanh, ánh sáng, remote chuyển slide.
