# Nguồn dữ liệu đã được người dùng duyệt

## Detection có sẵn trong repository

Vietnam License Plate v2, Roboflow, COCO; nguồn và giấy phép CC BY 4.0 được
ghi trong README.dataset.txt của bộ có sẵn. Không thay dữ liệu hoặc nhãn gốc.

## OCR và video bổ sung

Người dùng đã duyệt nguồn winter2897 và sau kiểm tra đã chấp thuận huấn luyện
baseline có ghi rõ giới hạn lớp hiếm.

- [Tài liệu nguồn](https://github.com/winter2897/Real-time-Auto-License-Plate-Recognition-with-Jetson-Nano/blob/main/doc/dataset.md).
- [VOC OCR archive](https://drive.google.com/file/d/1-k-8H1owJnijj_1ymGJFxs0UYjfAvogg/view).
- [Thư mục video Việt Nam](https://drive.google.com/drive/folders/1XXpHaRq5VPIR7lQoOEg9X76LbZDzFals).
- [Video test_1.mp4 đã dùng](https://drive.google.com/file/d/1kMQkv-AEwq2XXKmK84FqoWlVuSadfnfp/view).

Ngày tải 24/10/2026. Archive OCR: 125.372.612 bytes,
SHA256 `b63a42fe095e8fb13837f2beb74971d37a5bf94bb09b6adde537551ccd4cab35`.
Video: 2.169.631 bytes,
SHA256 `fe3297021a2c5f13419401465893dc663860cbb5c321550d10aeab2390cd2f15`.

Giữ attribution nguồn ở đây và tại `data/external/winter2897/download.json`.
Trang nguồn chưa cung cấp tuyên bố giấy phép riêng rõ ràng cho các dữ liệu
Drive đã tải; việc người dùng duyệt sử dụng baseline không thay thế xác minh
quyền tái phân phối. Dữ liệu tải ngoài và các crop dẫn xuất đã được gitignore.

Audit OCR: 3.188 ảnh và 25.781 ký tự; đủ 36 nhãn nhưng O/Q/W chỉ có 4/2/4 mẫu.
Ảnh `0.jpg` là bảng phông chữ, chỉ dùng train. Không có nhãn quốc gia hoặc
identity/capture-group đáng tin cậy cho từng ảnh; split theo SHA256 ảnh nguồn
chỉ bảo đảm không trùng ảnh chính xác giữa các tập, chưa loại hết ảnh gần trùng.
Xem `wp3_dataset_audit.json` và `wp3_data_preparation.json`.

Video test không có chuỗi biển số gán nhãn theo từng frame; báo cáo video
chỉ xác nhận xử lý/tích hợp, không suy ra accuracy từ số kết quả đúng định dạng.
