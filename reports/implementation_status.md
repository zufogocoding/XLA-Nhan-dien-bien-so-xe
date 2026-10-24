# Tiến độ WP1–WP4

Cập nhật: 24/10/2026. Bản local đã tích hợp bốn giai đoạn và có artifact
baseline. Chưa hoàn thành toàn bộ tiêu chí nghiệm thu về độ chính xác.

Đã sửa nhận diện theo hướng xử lý ảnh ở đợt tiếp theo cùng ngày. Kết quả
hiện hành: [báo cáo sửa lỗi](image_processing_fix.md). Đã sửa thêm lỗi thay
đổi mặc định WP1; [điều tra chéo nhánh](wp1_branch_investigation.md) phân
biệt rõ WP1 độc lập và bộ chọn vùng có hỗ trợ OCR của ứng dụng.

## Các lựa chọn người dùng đã chốt

- Ký tự 32×32; giao diện HTML + JavaScript; chạy Python local với SQLite.
- Bảng mã đăng ký hiện hành thay danh sách 63 tỉnh cũ trong brief.
- OCR/video winter2897 đã duyệt; huấn luyện baseline dù O/Q/W ít mẫu,
  ghi rõ giới hạn. Không huấn luyện lại model WP1 đã có.
- Dừng sửa Docker Desktop, tiếp tục local; không reset/đổi tên runtime Docker.

## Kết quả theo tiêu chí

| Hạng mục | Kết quả kiểm chứng | Trạng thái |
|---|---|---|
| WP1 độc lập Precision / Recall / F1 | 0,8794 / 0,7209 / 0,7923 trên 169 ảnh, 172 box; khớp nhánh WP1 | Precision đạt; Recall/F1 chưa đạt |
| WP1 thời gian | Trung bình 179,7 ms; P95 298,1 ms, gồm decode và warp/deskew | Trung bình dưới 200 ms; một số ảnh vượt |
| Bộ chọn vùng của ứng dụng | 0,8571 / 0,8023 / 0,8288, dùng WP2–WP4 hỗ trợ | Đạt ba ngưỡng box trong phạm vi ứng dụng; không thay kết quả WP1 độc lập |
| WP2 tách ký tự | Recall/precision 92,57%/97,15% khi HOG/SVM chọn ngưỡng; thuần hình học 91,78%/88,06% | Recall đạt 90%; cần kiểm soát box thừa |
| WP2 số dòng | 94,979% trên 478 ảnh; nhãn suy từ hình học box | Vẫn dưới 95%; thiếu nhãn dòng độc lập |
| WP2 chuẩn hóa | Mọi ký tự 32×32, giữ tỷ lệ và căn giữa | Đã triển khai, có kiểm thử |
| WP3 accuracy ký tự | SVM+HOG+LBP 96,53% trên 3.834 ký tự test cắt theo nhãn | Đạt 85% trong phạm vi này; O/Q/W không có test |
| WP3 chuỗi / CER / WER | 69,46% / 0,0936 / 0,3054 với luồng chọn ngưỡng mới | CER đạt; chuỗi và WER chưa đạt |
| WP3 latency ký tự | Trung bình 4,647 ms, gồm feature + classifier, 100 crop | Đạt 100 ms trong phép đo local |
| WP4 accuracy toàn luồng | Thiếu ảnh giao thông gốc kèm chuỗi thật độc lập | Chưa xác nhận mục tiêu 70% |
| WP4 latency ảnh | Riêng chọn vùng/OCR đã trung bình 1.658,9 ms, chưa gồm HTTP/ghi ảnh/SQLite | Chưa đạt 1 giây; baseline 176,9 ms không đại diện mã mới |
| WP4 database | Đã lưu đủ các ảnh kiểm tra mới; baseline lưu 169/169 ảnh và 52/52 frame | Đạt trong các lần kiểm tra chức năng |
| Web/API local | Upload ảnh/video, kết quả, lịch sử, tìm kiếm, CRUD, thống kê | Đã chạy và kiểm tra |
| Webcam | Có nút mở camera/cấp quyền, gửi từng ảnh chụp | Có mã; chưa kiểm tra camera vật lý |
| Video demo | MP4 260 frame từ kết quả inference thật | Chưa có bài quay OBS đầy đủ web/webcam |
| Docker | Có Dockerfile backend/frontend, nginx, compose; config hợp lệ | Chưa build; dừng theo yêu cầu người dùng |

Các tập đánh giá WP1 và WP2–WP3 khác nhau, không ghép các chỉ số thành
accuracy toàn luồng. `recognized` chỉ nói đúng mẫu/mã được hỗ trợ; điểm OCR
không phải xác suất đúng cả biển.

## Những gì đã làm

### WP1

Giữ detector và model hiện có, bổ sung dependency đúng phiên bản, xử lý thiếu
joblib tùy chọn, sửa chuẩn hóa góc deskew với OpenCV hiện tại và thêm đầu vào
mảng ảnh cho video. Đánh giá lại toàn test, kiểm thử hồi quy hình học. Nới
ngưỡng diện tích trên valid làm F1 giảm nên giữ cấu hình cũ. Xem
[WP1](wp1_evaluation.md), [tuning](wp1_validation_tuning.md), [latency](baseline_local_latency.json).

### WP2

Có đủ Otsu/adaptive, tách dòng, ba cách tìm ký tự, lọc nhiễu, tách ký tự dính,
sửa nét đứt tùy chọn, chuẩn hóa và augmentation. So sánh hai cực tính và nhóm
tâm thành phần để xử lý dòng nghiêng. Chiều cao xử lý 128 px chọn từ valid;
tọa độ output trở về ảnh đầu vào, ký tự vẫn 32×32. Không chèn ký tự giả để đủ
độ dài chuỗi. Đã chạy 478 ảnh test, hơn yêu cầu 100 ảnh. Xem [WP2](wp2_evaluation.md).

### WP3

Audit/import 3.188 ảnh, 25.781 ký tự, 36 lớp; chia 2.232/478/478 ảnh
train/valid/test theo nhóm SHA256 ảnh nguồn. Bảng phông chữ chỉ ở train.
O=4, Q=2, W=4 mẫu, toàn bộ ở train; không có test độc lập các lớp này.
Không có nhãn danh tính xe nên không bảo đảm loại trùng xe giữa các ảnh khác
nhau. Nguồn có cả biển ngoài Việt Nam.

Huấn luyện xong SVM+HOG, SVM+LBP, SVM+HOG+LBP, kNN và RF; grid search
GroupKFold trên train, chọn theo valid. Có manifest, per-class metrics,
confusion matrix, so sánh, ablation, robustness mô phỏng, CER/WER và API.
HOG 32×32 có 324 chiều, LBP rời rạc 3×3 có 10 chiều, kết hợp 334 chiều;
ghi rõ khác thông số ước lượng trong brief. Đánh giá ngược sáng/chói/che
khuất tự nhiên còn thiếu ảnh có nhãn độc lập.

### WP4

Có ba mẫu regex, sửa tám cặp nhầm theo vị trí, tra mã đăng ký có nguồn,
voting 20 quan sát với reset khi box nhảy vị trí. Lưu chuỗi gốc, thay thế,
model/segmentation version, điểm từng ký tự và lỗi. SQLite CRUD, FastAPI,
giao diện đầy đủ cho luồng local. Loại xe giữ unknown nếu chưa phân biệt
được ô tô/xe máy từ chuỗi; không suy diễn từ category 1/2 của COCO.

Ảnh smoke test đọc đúng 59Y1-602.71, có crop và chín ký tự. Video nguồn có
260 frame; xử lý 52 frame, phát hiện box ở 30 frame, lưu đủ cả các trường
hợp không tìm thấy biển/không tách được ký tự. Đây là kiểm tra chức năng,
không phải nhãn đúng video.

Xem [API](../docs/api.md), [WP4](wp4_evaluation.md), ảnh giao diện: `local_web_demo.png` (tạo local, không đưa lên Git),
video demo: `../demo/video_demo.mp4` (tạo local, không đưa lên Git), [kịch bản demo](../demo/README.md).

## Kiểm chứng và tái lập

- 53 kiểm thử pytest đạt; một cảnh báo deprecation từ TestClient/httpx.
- node --check web/app.js và git diff --check đạt.
- API thật nạp đúng SVM+HOG+LBP, WP2 phiên bản
  wp2-0.4-multithreshold-frame-aware; URL ảnh/crop/ký tự/ảnh trung gian truy cập được.
- Sau khi khôi phục WP1, server local đã chạy lại; upload qua HTTP đọc đúng
  59Y1-602.71 và 30G-699.46, lưu/xem lại bản ghi và truy cập đủ ảnh trung gian.
- Benchmark đối chứng xác nhận 169/169 box WP1 khớp nhánh gốc; 169/169 box
  và chuỗi OCR của ứng dụng không đổi sau tối ưu ghép mảnh đứt. Xem
  [kiểm tra tương đương](wp1_audit_checks.json).
- MP4 giải mã đủ 260 frame, 1200×600, 27 fps.
- CLI WP1→WP4 chạy đúng ảnh mẫu và xuất JSON UTF-8 qua redirect trên Windows;
  đã sửa lỗi encoding cp1252 khi kết quả chứa tên địa phương tiếng Việt.
- requirements-lock.txt lưu môi trường đã chạy. Dữ liệu tải về/runtime
  gitignore. Không cần chạy lại chuẩn bị dữ liệu/huấn luyện để dùng local.

Chạy: `.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000`,
rồi mở http://127.0.0.1:8000/. Xem [README](../README.md).

## Phần còn cần dữ liệu/kiểm chứng

1. Nâng tiếp chất lượng đọc chuỗi, tách dòng và tối ưu tốc độ; WP1 độc lập
   còn thiếu Recall/F1. Bộ chọn vùng có OCR đạt ngưỡng box ở phạm vi ứng dụng.
2. Tập ảnh giao thông kèm chuỗi biển thật độc lập để đo WP1→WP4; thêm mẫu
   O/Q/W và ảnh điều kiện khó có nhãn; nhãn loại xe/dòng chính thức nếu cần
   kết luận riêng theo nhóm.
3. Người dùng thử camera vật lý và quay bài demo web/webcam đầy đủ.
4. Docker build để lại theo yêu cầu dừng sửa Docker. PostgreSQL chỉ cần khi
   người dùng đổi mục tiêu sang production.

Docker Model Runner hiện vẫn tạm tắt theo lần cho phép trước. Cấu hình gốc:
`%APPDATA%/Docker/settings-store.json.codex-backup-20261024-880cd934`.
Không thay đổi thêm Docker sau yêu cầu dừng.
