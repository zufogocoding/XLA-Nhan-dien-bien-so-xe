# Đánh giá WP1 hiện tại

Thuật toán dùng CLAHE và bilateral, tạo vùng ứng viên từ Canny, black-hat/Sobel và mặt nạ màu HSV, nối vùng bằng morphology, tìm contour và xếp hạng theo hình dạng, diện tích, mật độ cạnh, màu. Không sử dụng box nhãn trong lúc dự đoán.

Đo trên toàn bộ `test` (169 ảnh, 172 box), mỗi ảnh chỉ xuất 1 box mạnh nhất. Một dự đoán đúng khi IoU với box nhãn đạt ít nhất 0,5; mỗi box nhãn chỉ được ghép một lần.

| Chỉ số | Kết quả | Mục tiêu brief |
|---|---:|---:|
| TP / FP / FN | 92 / 77 / 80 | — |
| Precision | 0,544 | ≥ 0,85 |
| Recall | 0,535 | ≥ 0,80 |
| F1 | 0,540 | ≥ 0,82 |
| Thời gian trung bình | 21,1 ms/ảnh | ≤ 200 ms/ảnh |

Kết quả này **chưa đạt mục tiêu độ chính xác**. Tập test có ảnh nhiều biển, trong khi interface hiện chỉ trả một biển. Nhiều false positive là logo, đèn hoặc chi tiết thân xe có màu sáng và cạnh mạnh; một số biển bị contour tách thành vùng ký tự nhỏ. `confidence` trong API là điểm xếp hạng heuristic, chưa được hiệu chuẩn thành xác suất.

Trên 76 ảnh test có category ID `2` (77 box), Precision = 0,513, Recall = 0,506 và F1 = 0,510. Qua ảnh mẫu, category này có vẻ chủ yếu là biển hai dòng/xe máy, nhưng nguồn không giải thích chính thức ý nghĩa category, nên chưa gọi đây là chỉ số riêng cho xe máy.

Có thể tái lập bằng:

```powershell
.\.venv\Scripts\python.exe evaluate_wp1.py 'Vietnam License Plate.v2i.coco\test'
```

Hướng cải thiện: kiểm tra nhãn `1`/`2`, tối ưu bằng `valid`, bổ sung đặc trưng phân biệt biển với logo (mật độ nét ký tự, khung chữ nhật, độ tương phản trong vùng), xử lý nhiều biển và đánh giá riêng xe máy. Chỉ kết luận đạt yêu cầu sau khi kiểm tra lại trên tập test độc lập.
