# Đánh giá WP2 sau sửa xử lý ảnh

478 ảnh crop test, 3.834 ký tự có box nhãn; ký tự đầu ra luôn 32×32.

| Bộ chọn phương án nhị phân | Recall box tại IoU ≥0,5 | Precision box | Đúng số dòng |
|---|---:|---:|---:|
| Hình học OpenCV | 0.9178 | 0.8806 | 0.9372 |
| Hình học + HOG/SVM hiện có, dùng trong API | 0.9257 | 0.9715 | 0.9498 |

API khớp 3549/3834 box, có 104 box thừa. Recall tách
chữ vượt 90%. Số dòng 94,979% vẫn dưới 95%, không làm tròn để kết luận đạt.
Nhãn dòng suy từ hình học box, chưa có nhãn dòng độc lập. Nguồn có cả biển
ngoài Việt Nam; không đánh giá WP1 trên các ảnh crop này.

Otsu, CLAHE+Otsu và adaptive Gaussian tạo các phương án; morphology xử lý
viền/nét đứt theo từng phương án. HOG/SVM hỗ trợ chọn phương án, không chèn
thêm ký tự. [Giải thích và trước/sau](image_processing_fix.md),
[dữ liệu đầy đủ](image_processing_test.json), [baseline](image_processing_before_test.json).
