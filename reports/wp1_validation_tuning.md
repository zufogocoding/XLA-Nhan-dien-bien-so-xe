# Kiểm tra ngưỡng diện tích WP1 trên valid

Đã thử nới diện tích ứng viên để xem có khôi phục được biển rất nhỏ/lớn hay
không. Mẫu 250 ảnh được chọn ngẫu nhiên cố định từ `valid`, seed 2026;
IoU ≥ 0,5, tối đa một dự đoán mỗi ảnh. Không dùng test để chọn ngưỡng.

| Khoảng diện tích | Precision | Recall | F1 |
|---|---:|---:|---:|
| 0,005–0,30 (cũ) | 0,9298 | 0,7626 | 0,8379 |
| 0,002–0,60 | 0,8745 | 0,7518 | 0,8085 |
| 0,001–0,90 | 0,8642 | 0,7554 | 0,8061 |

Giữ nguyên giá trị mặc định vì hai phương án nới làm F1 giảm. Việc này chưa
giải quyết được mục tiêu Recall ≥ 0,80 trên test. Script cho phép thử nghiệm
ngưỡng qua tham số nhưng không tự thay mặc định production. Thời gian khi
screening không dùng làm latency benchmark vì có huấn luyện model chạy đồng thời.

Raw metrics: [wp1_validation_area_screen.json](wp1_validation_area_screen.json).
