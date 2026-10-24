# Kiểm tra bản local WP4

**Kiểm tra chéo nhánh tiếp theo:** 53 kiểm thử đạt. Đã tách WP1 độc lập khỏi
bộ chọn vùng có OCR và tối ưu ghép mảnh đứt. Xem
[phạm vi và benchmark hiện tại](wp1_branch_investigation.md). Các phép đo
chức năng/latency bên dưới lưu lịch sử trước sửa, không phải mã hiện tại.

**Đợt sửa xử lý ảnh tiếp theo cùng ngày:** 51 kiểm thử đạt; 6 ảnh người dùng
đã đi qua API mới và có ảnh trung gian. 5 ảnh rõ đọc đúng khi đối chiếu thủ
công; ảnh bong/mờ còn báo cần kiểm tra. [Báo cáo mới](image_processing_fix.md).
Các số latency/video bên dưới là baseline trước sửa. Luồng mới thử nhiều
ngưỡng/vùng, chưa xác nhận đạt 1 giây; không dùng 176,9 ms cũ cho mã hiện tại.

Ngày 24/10/2026. Model service: `wp3-svm_hog_lbp-5a21413aa546`;
WP2: `wp2-0.2-polarity-component-lines-128`.

## Chức năng

API thật trên localhost đã nhận ảnh, trả chuỗi `59Y1-602.71` khớp ảnh mẫu,
có box/crop/chín ký tự, định dạng, mã địa phương và metadata. Đã kiểm tra
các URL ảnh nguồn/crop/ký tự trả HTTP 200, xem lại kết quả từ lịch sử trong
trình duyệt. Kết quả ảnh: `local_image_smoke_test.json` (tạo local, không đưa lên Git), giao diện: `local_web_demo.png` (tạo local, không đưa lên Git).

Video winter2897 `test_1.mp4` đọc đủ 260 frame, lấy mẫu 52 frame, có box
ở 30 frame, lưu đủ 52 kết quả vào SQLite. Trong đó: 18 `recognized`,
9 `needs_review`, 22 `no_plate`, 3 `segmentation_empty`; không có
`processing_error`. Response chứa 50 bản ghi cuối, DB chứa đủ 52.
`recognized` chỉ có nghĩa đúng mẫu/mã hỗ trợ; chưa đối chiếu nhãn OCR video.
Tóm tắt: `local_video_smoke_summary.json` (tạo local, không đưa lên Git), response: `local_video_smoke_test.json` (tạo local, không đưa lên Git).

Pytest kiểm tra CRUD, đọc bản ghi, thống kê, upload ảnh hỏng/đuôi không hỗ
trợ, thiếu model và file tĩnh. Có kiểm thử riêng cho regex, tám cặp nhầm,
mã đăng ký, SQLite và voting. Tổng bộ kiểm thử: 46 passed, một cảnh báo
deprecation của TestClient/httpx.

Webcam có nút mở/cấp quyền qua trình duyệt và gửi từng ảnh chụp. Chưa kiểm
tra camera vật lý; chưa có stream tự động hoặc theo dõi nhiều xe. Voting
một biển mạnh nhất/frame, cửa sổ 20 quan sát; xe đổi ở cùng vị trí có thể
làm lẫn kết quả.

## Latency và lưu kết quả

Đo trên 169 ảnh COCO test trong tiến trình local đã làm nóng model, runtime
riêng. Toàn pipeline gồm đọc ảnh, WP1–WP4, ghi crop/ký tự và SQLite, chưa
gồm HTTP/upload. Tập này không có nhãn nội dung nên không dùng các trạng
thái để tính accuracy.

| Phạm vi | Trung bình | Trung vị | P95 | Lớn nhất |
|---|---:|---:|---:|---:|
| WP1 đầy đủ | 165,9 ms | 164,3 ms | 254,8 ms | 327,7 ms |
| WP1→WP4 và lưu kết quả | 176,9 ms | 177,6 ms | 282,5 ms | 377,5 ms |

SQLite lưu 169/169 kết quả: 76 đúng mẫu/mã, 57 cần kiểm tra, 28 không tìm
thấy biển, 8 không tách được ký tự. Latency ≤1 giây đạt trong lần đo này,
gồm cả ảnh không đọc được chuỗi; không bảo đảm mọi thiết bị/kích thước ảnh.
Chi tiết: [local_latency.json](baseline_local_latency.json). Tái lập:
`.\.venv\Scripts\python.exe scripts\benchmark_local.py`.

## Tiêu chí còn thiếu

Accuracy end-to-end ≥70% chưa xác nhận: COCO của project chỉ có nhãn box;
OCR công khai là ảnh crop từ nguồn khác. Độ đúng chuỗi WP2+WP3 trên 478
crop test là 48,74%, chưa đạt WP3; không dùng 96,53% trên ký tự cắt theo
GT làm accuracy toàn biển.

Đã xuất video inference có chú thích: `../demo/video_demo.mp4` (tạo local, không đưa lên Git), giải mã đủ
260 frame ở 1200×600/27 fps. Chưa quay đầy đủ giới thiệu → upload ảnh →
upload video → webcam → dashboard bằng OBS/biên tập theo WP4.

Dockerfile, nginx và compose có sẵn; config đã kiểm tra, chưa build thành
công do Docker Desktop lỗi. Người dùng yêu cầu dừng sửa Docker. Mục tiêu
hiện tại local/SQLite; chưa có PostgreSQL/hosting production.
