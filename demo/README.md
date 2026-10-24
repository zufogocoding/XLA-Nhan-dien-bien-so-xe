# Demo local

Video sinh ra, ảnh giao diện và response smoke test là artifact local đã
gitignore; không đi kèm khi clone. Mã tạo demo và báo cáo benchmark được giữ
trong Git. Xem [chính sách artifact](../reports/artifact_policy.md).

`video_demo.mp4` được xuất từ kết quả API thật trên video winter2897 đã được
người dùng duyệt. Video gốc có 260 frame; API lấy mẫu mỗi 5 frame và lưu đủ
52 kết quả vào SQLite. Phần chú thích hiển thị kết quả của frame lấy mẫu gần
nhất, gồm box, chuỗi OCR, crop và voting nếu có. Không có nhãn OCR video để
đo độ chính xác. Video demo này chưa thay thế bài quay web/webcam đầy đủ
trong WP4.

Tạo lại sau khi upload video qua API và cập nhật báo cáo smoke test:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-demo.txt
.\.venv\Scripts\python.exe -m demo.make_video_demo
```

Ảnh giao diện bản local đã kiểm tra: `../reports/local_web_demo.png`.
Kết quả kiểm tra video xuất ra: `../reports/local_video_demo_validation.json`.

Kịch bản quay web theo WP4, khi người dùng sẵn sàng thử camera thật:

1. Giới thiệu bốn giai đoạn; nói rõ đây là baseline và số đo nguyên biển.
2. Upload ảnh; xem ảnh gốc, crop và các ký tự 32×32; đối chiếu chuỗi thật.
3. Upload video; xem kết quả lấy mẫu và các bản ghi trong lịch sử.
4. Bấm mở webcam, tự cấp quyền camera, chụp biển trong khung và đối chiếu.
5. Mở thống kê; sửa một kết quả sai và kiểm tra lịch sử sau khi tải lại trang.

Chưa quay bằng OBS/biên tập CapCut hoặc DaVinci; chưa kiểm tra webcam vật lý.
