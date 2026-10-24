# Đánh giá chuỗi sau sửa xử lý ảnh

478 ảnh crop test có nhãn, cùng split và cùng model SVM+HOG+LBP.
Luồng mới dùng OpenCV và HOG/SVM chọn ảnh nhị phân, sau đó ghép chuỗi.

| Chỉ số | Trước sửa | Sau sửa | Mục tiêu |
|---|---:|---:|---:|
| Đúng nguyên chuỗi | 0,4874 | 0.6946 | ≥0,75 |
| CER | 0,2337 | 0.0936 | ≤0,15 |
| WER: một biển = một token | 0,5126 | 0.3054 | ≤0,20 |

CER đạt; độ đúng chuỗi và WER còn chưa đạt. Thứ tự GT suy từ box; bỏ dấu
chấm/gạch. WP1 và WP4 không nằm trong phép đo này, nguồn có biển ngoài Việt
Nam. Không dùng accuracy ký tự GT 96,53% làm accuracy cả biển.
[Giải thích xử lý ảnh](image_processing_fix.md), [kết quả gốc](image_processing_test.json).
