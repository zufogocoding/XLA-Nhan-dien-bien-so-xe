# Đánh giá WP1 hiện tại

**Kiểm tra chéo nhánh ngày 24/10/2026:** WP1 độc lập hiện khớp từng box với
`wp1/fix-char-density-deskew` (`ed80c5e`), F1 0,7923. Đã sửa lỗi tích hợp
tự chạy WP2 và chọn lại vùng khiến F1 từng giảm xuống 0,6967.
Xem [điều tra, nguyên nhân và các phép đo đối chứng](wp1_branch_investigation.md).

Ứng dụng có bộ chọn vùng riêng, dùng segmentation và HOG/SVM từ WP2–WP4:
TP/FP/FN 138/23/34, Precision 0,8571, Recall 0,8023, F1 0,8288 trong phép
đo kiểm soát hiện tại. Số 0,8408 trước đó được giữ làm lịch sử và chưa tái
lập được; xem [JSON hiện tại](wp1_application_selector.json).
Đây là độ đúng box của ứng dụng, không phải kết quả WP1 độc lập hay OCR
nguyên biển. [Báo cáo xử lý ảnh](image_processing_fix.md).

Thuật toán dùng CLAHE và bilateral, tạo vùng ứng viên từ Canny, black-hat/Sobel và mặt nạ màu HSV, nối vùng bằng morphology, tìm contour và xếp hạng theo hình dạng, diện tích, mật độ cạnh, màu. HOG+SVM trong `models/wp1_svm.pkl` lọc và xếp hạng lại ứng viên. Không sử dụng box nhãn trong lúc dự đoán.

Đo trên toàn bộ `test` (169 ảnh, 172 box), mỗi ảnh chỉ xuất 1 box mạnh nhất. Một dự đoán đúng khi IoU với box nhãn đạt ít nhất 0,5; mỗi box nhãn chỉ được ghép một lần.

| Chỉ số | Kết quả | Mục tiêu brief |
|---|---:|---:|
| TP / FP / FN | 124 / 17 / 48 | — |
| Precision | 0,879 | ≥ 0,85 |
| Recall | 0,721 | ≥ 0,80 |
| F1 | 0,792 | ≥ 0,82 |
| Thời gian WP1 đầy đủ trung bình | 179,7 ms/ảnh | ≤ 200 ms/ảnh |

Phép đo mới chạy tuần tự, OpenCV một thread, Python 3.12.14,
`scikit-learn==1.8.0`, giữ nguyên model và nhãn. Sau một ảnh làm nóng,
thời gian gồm đọc/giải mã ảnh, phát hiện, warp/deskew: trung bình 179,7 ms,
trung vị 177,9 ms, P95 298,1 ms, lớn nhất 356,3 ms. Đạt 200 ms nếu xét
trung bình; không phải mọi ảnh đều dưới 200 ms.
Chi tiết từng ảnh, SHA256 dữ liệu/model/mã và môi trường:
[wp1_restored_standalone.json](wp1_restored_standalone.json).

Phép đo detector riêng 145,8 ms trước đó được giữ tại
[wp1_current_evaluation.json](wp1_current_evaluation.json). Phép đo local
cũ 165,9 ms WP1 / 176,9 ms toàn luồng tại
[baseline_local_latency.json](baseline_local_latency.json) chỉ là lịch sử;
không dùng thời gian khác phạm vi để suy luận tốc độ ứng dụng hiện tại.

Bảng đếm tương ứng cho bài toán phát hiện tại IoU ≥ 0,5:

| | Có box dự đoán ghép đúng | Không có box dự đoán ghép đúng |
|---|---:|---:|
| Biển số thật | TP = 124 | FN = 48 |
| Vùng dự đoán không ghép được với biển thật | FP = 17 | TN không xác định |

Không báo cáo TN hoặc accuracy phân loại từ bảng này vì bài toán phát hiện
không định nghĩa số lượng vùng nền âm tính.

Kết quả này **chưa đạt mục tiêu độ chính xác**. Tập test có ảnh nhiều biển, trong khi interface hiện chỉ trả một biển. Nhiều false positive là logo, đèn hoặc chi tiết thân xe có màu sáng và cạnh mạnh; một số biển bị contour tách thành vùng ký tự nhỏ. `confidence` trong API là điểm xếp hạng heuristic, chưa được hiệu chuẩn thành xác suất.

Trên 76 ảnh test có category ID `2` (77 box), Precision = 0,513, Recall = 0,506 và F1 = 0,510. Qua ảnh mẫu, category này có vẻ chủ yếu là biển hai dòng/xe máy, nhưng nguồn không giải thích chính thức ý nghĩa category, nên chưa gọi đây là chỉ số riêng cho xe máy.

Có thể tái lập bằng:

```powershell
.\.venv\Scripts\python.exe evaluate_wp1.py 'Vietnam License Plate.v2i.coco\test'
.\.venv\Scripts\python.exe scripts\benchmark_wp1.py --mode standalone --label WP1 --output outputs\wp1.json
.\.venv\Scripts\python.exe scripts\benchmark_wp1.py --mode application --label app --output outputs\application.json
```

Hướng cải thiện: kiểm tra nhãn `1`/`2`, tối ưu bằng `valid`, bổ sung đặc trưng phân biệt biển với logo (mật độ nét ký tự, khung chữ nhật, độ tương phản trong vùng), xử lý nhiều biển và đánh giá riêng xe máy. Chỉ kết luận đạt yêu cầu sau khi kiểm tra lại trên tập test độc lập.
