# Sửa nhận diện bằng xử lý ảnh — 24/10/2026

## Lỗi đã tìm thấy

Cập nhật kiểm tra chéo nhánh: đã khôi phục mặc định WP1 độc lập sau một lỗi
tích hợp. Các bảng sau lưu kết quả lịch sử của đợt sửa ảnh. F1 box ứng dụng
hiện đo lại là 82,88%; số cũ 84,08% chưa tái lập được và không đại diện mã
hiện hành. Cả hai đều dùng WP2–WP4 hỗ trợ. WP1 độc lập F1 79,23%. Xem
[điều tra và benchmark kiểm soát](wp1_branch_investigation.md).

Ảnh BMW bị cắt nhầm logo BMW trên khung; ảnh Mercedes bị cắt nhầm đồ vật
phía sau xe. Kernel nối cạnh cố định quá nhỏ với chữ lớn trên ảnh thật;
chỉ lấy ứng viên đầu tiên khiến OCR không được đọc biển thật.

Ở ảnh xe máy, mảnh viền dọc cao làm tăng chiều cao dòng, khiến bộ lọc loại
cả năm số phía dưới. Viền dính chữ còn tạo box trùng. Otsu toàn cục làm mất
nét E nhạt trong ảnh xe đỏ. Ảnh biển mờ/bong nét mất nhiều thông tin hơn.

Ảnh trước/sau: `image_processing_before_after.jpg` (tạo local, không đưa lên Git).

## Kỹ thuật sử dụng

Giữ nguyên tất cả model đã huấn luyện, gồm SVM+HOG+LBP. Tập trung sửa OpenCV:

1. Connected components ở nhiều ngưỡng; nhóm chữ có chiều cao tương tự,
   thẳng hàng, khoảng cách hợp lý để tìm thêm vùng biển khi contour bị nối
   với thân xe. Ước lượng góc bằng minAreaRect, chỉnh phối cảnh bằng warp.
2. So sánh nhiều vùng ứng viên, có kiểm tra bằng ký tự bên trong.
3. So sánh Otsu, CLAHE+Otsu, adaptive Gaussian 31×31/51×51. Ảnh lớn có thêm
   phương án nội suy cubic để giữ nét nhạt.
4. Morphological opening theo hướng để gỡ viền gần mép. Giữ cả phương án
   không lọc viền vì morphology mạnh có thể phá chữ. Ghép mảnh đứt theo độ
   chồng trục x sau khi tách dòng, trong một phương án riêng.
5. Nhóm dòng theo thành phần có chiều cao điển hình, loại viền quá cao
   trước khi tính khoảng dòng; hỗ trợ glyph rộng trên biển bị ép phối cảnh.
6. HOG/SVM hỗ trợ chọn ảnh nhị phân theo log-confidence, độ đều chiều cao,
   số box và mảnh sát mép. Không chèn ký tự để đủ độ dài. Regex/mã đăng ký
   chỉ là một tín hiệu chọn vùng trong API.
7. Giữ chuỗi gốc, báo cần kiểm tra khi điểm ký tự thấp. Parser hỗ trợ thêm
   sê-ri hai chữ như 29AC, giữ chuỗi đã đúng mẫu trước khi sửa nhầm.

Ảnh ký tự vẫn 32×32. Giao diện có **Xem các bước xử lý ảnh**: ảnh xám,
ảnh nhị phân đã chọn, box và thứ tự ký tự.
Ảnh giao diện đã kiểm tra: `image_processing_web.png` (tạo local, không đưa lên Git).

## Kết quả

Chọn cấu hình trên 478 ảnh valid: đọc đúng chuỗi 50,00% → 73,85%. Sau khi
chốt cấu hình, đo 478 crop test / 3.834 ký tự, không đổi model hoặc split:

| Chỉ số | Trước sửa | Sau sửa |
|---|---:|---:|
| Recall box ký tự, IoU ≥0,5 | 76,79% | 92,57% |
| Precision box ký tự | 92,81% | 97,15% |
| Đúng số dòng, nhãn suy từ box | 91,84% | 94,98% |
| Đúng nguyên chuỗi | 48,74% | 69,46% |
| CER | 23,37% | 9,36% |
| WER, một biển là một token | 51,26% | 30,54% |

Bảng này dùng OpenCV cùng HOG/SVM chọn phương án nhị phân. Nếu chỉ chọn
bằng hình học OpenCV: recall box 91,78%, precision 88,06%, số dòng 93,72%;
đọc chuỗi qua phương án đó là 48,54%. Tăng recall tách chữ cần đi kèm kiểm
soát box thừa. Các số trên không phải accuracy OCR ảnh giao thông toàn cảnh.

Trên COCO test 169 ảnh / 172 box, bộ chọn vùng thực tế của API tại IoU ≥0,5:

| Chỉ số | Detector baseline | Bộ chọn vùng mới |
|---|---:|---:|
| TP / FP / FN | 124 / 17 / 48 | 140 / 21 / 32 |
| Precision | 87,94% | 86,96% |
| Recall | 72,09% | 81,40% |
| F1 | 79,23% | 84,08% |

Ba ngưỡng độ chính xác box đạt với bộ chọn vùng của ứng dụng trong phép
đo này; không kết luận WP1 độc lập đạt. Có thêm bốn FP; precision giảm nhẹ
nhưng vẫn trên 85%. COCO không có nhãn nội dung biển.

## Sáu ảnh người dùng gửi

Đối chiếu thủ công để sửa lỗi phát triển, không phải benchmark độc lập:
5 ảnh đọc được 30F-222.22, 29AC-886.88, 30G-699.46, 30E-736.70,
30G-307.98. Ảnh Mercedes vẫn báo cần kiểm tra vì có ký tự điểm thấp.
Ảnh mờ/bong nét còn thiếu hoặc sai số; không có bản chép nhãn chắc chắn
và không kết luận đã sửa đúng ảnh này. Chi tiết: `image_processing_user_cases.json` (tạo local, không đưa lên Git).

## Giới hạn và tái lập

Đúng chuỗi 69,46% còn dưới 75%; WER còn trên 20%. Số dòng 94,979% còn dưới
95%, không làm tròn để tuyên bố đạt. Nhãn dòng suy từ box; OCR có cả biển
ngoài Việt Nam. Chưa có ảnh giao thông kèm chuỗi thật để đo toàn luồng 70%.

Thử nhiều phương án làm tăng thời gian. Trong phép đo 169 ảnh có công việc
nền đồng thời, trung bình khoảng 1.096 ms/ảnh, P95 2.962 ms, gồm đọc ảnh,
chọn vùng và OCR, chưa gồm HTTP/SQLite. Chưa xác nhận đạt 1 giây WP4 hoặc
200 ms WP1 với luồng mới. Accuracy ký tự GT 96,53% của model giữ nguyên;
không dùng nó thay cho accuracy cả biển. Đợt này có 51 kiểm thử đạt; sau
sửa hợp đồng WP1 và tối ưu ghép mảnh đứt, tổng bộ kiểm thử là 53 đạt.
Số latency ở đoạn này là lịch sử; phép đo kiểm soát hiện tại nằm trong
[báo cáo chéo nhánh](wp1_branch_investigation.md).

Sau khi khởi động lại server với mã cuối, API đã đọc đúng lại ảnh BMW và
ảnh xe máy 59Y1-602.71 vốn chạy tốt trước đây. Clip 20 frame từ video đã
duyệt xử lý 4 frame lấy mẫu và lưu đủ 4/4, không có processing_error.
Kiểm tra tích hợp cuối: `image_processing_final_smoke.json` (tạo local, không đưa lên Git). Server nền
thay phiên local cũ; lịch sử/ảnh đã có được giữ nguyên.

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_image_fix.py --split valid --reader --output outputs\recheck_valid.json
.\.venv\Scripts\python.exe scripts\evaluate_image_fix.py --split test --reader --output outputs\recheck_test.json
.\.venv\Scripts\python.exe scripts\evaluate_fullscene_image_fix.py
```

Kết quả gốc: [valid](image_processing_valid.json), [test](image_processing_test.json),
[chọn thuần hình học](image_processing_geometry_test.json),
[toàn cảnh COCO](image_processing_fullscene.json).
