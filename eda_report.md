# WP1: Khảo sát dataset

Nguồn: [Vietnam License Plate, Roboflow Universe](https://universe.roboflow.com/vietnam-license/vietnam-license-plate-hjswj), bản v2, giấy phép CC BY 4.0. Dữ liệu trong thư mục `Vietnam License Plate.v2i.coco/` đã có sẵn trong project. File `_annotations.coco.json` là nhãn để đánh giá; thuật toán phát hiện không đọc file này khi dự đoán.

| Tập | Ảnh | Box | Nhãn `1` | Nhãn `2` | Ảnh có >1 box |
|---|---:|---:|---:|---:|---:|
| train | 3.132 | 3.583 | 1.065 | 2.518 | 300 |
| valid | 1.233 | 1.401 | 451 | 950 | 118 |
| test | 169 | 172 | 95 | 77 | 3 |
| Tổng | 4.534 | 5.156 | 1.611 | 3.545 | 421 |

Tất cả ảnh đã được Roboflow kéo giãn về 640×640. Không có ảnh thiếu box. Danh sách category trong JSON là `plate`, `0`, `1`, nhưng box thực tế chỉ dùng ID 1 và 2. Qua các ảnh mẫu, ID 1 có vẻ là biển một dòng và ID 2 có vẻ là biển hai dòng; **đây chỉ là suy luận**, cần xác nhận trước khi dùng làm nhãn xe máy/ô tô. Không có nhãn chính thức cho sáng/tối, mờ, nghiêng hay loại xe. Việc kéo giãn ảnh có thể làm thay đổi tỷ lệ khung biển so với ảnh gốc.

Tập test nhỏ và tỷ lệ nhãn khác train/valid, nên kết quả tổng thể cần đi kèm kết quả theo loại biển. Không dùng test để chỉnh tham số. Ưu tiên tiếp theo: kiểm tra thủ công ý nghĩa hai category, xác định một tập con xe máy đáng tin cậy, rồi đánh giá riêng trên tập con đó.
