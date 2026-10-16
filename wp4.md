# WP4 – HẬU XỬ LÝ & DEPLOYMENT

## 1. MỤC TIÊU
Từ chuỗi ký tự thô → biển số hợp lệ → lưu database → demo web.

## 2. INPUT
- Chuỗi ký tự thô từ WP3
- Ảnh biển số từ WP1
- Metadata từ WP1, WP2, WP3

## 3. OUTPUT
- Biển số hợp lệ (đã qua post-processing)
- Database records
- Web demo
- Video demo

## 4. INTERFACE
INPUT: {
"raw_text": "51F12345",
"confidences": [...],
"image_path": "path/to/image.jpg",
"plate_crop": np.ndarray,
"timestamp": "2026-10-13 10:30:00"
}
OUTPUT: {
"plate_text": "51F-123.45",
"is_valid": True,
"province": "TP.HCM",
"vehicle_type": "car",
"confidence": 0.92
}

text

## 5. CÔNG VIỆC CHI TIẾT

### 5.1. Regex format biển VN
- [ ] Ô tô 5 số: `^\d{2}[A-Z]-?\d{3}\.?\d{2}$`
- [ ] Ô tô 4 số: `^\d{2}[A-Z]-?\d{4}$`
- [ ] Xe máy: `^\d{2}[A-Z]\d?-?\d{3}\.?\d{2}$`
- [ ] Output: `src/regex_validator.py`

### 5.2. Fix ký tự dễ nhầm
- [ ] `0 ↔ O`: nếu vị trí là số → 0, nếu là chữ → O
- [ ] `1 ↔ I`: tương tự
- [ ] `5 ↔ S`: tương tự
- [ ] `8 ↔ B`: tương tự
- [ ] `2 ↔ Z`: tương tự
- [ ] `4 ↔ A`: tương tự
- [ ] `6 ↔ G`: tương tự
- [ ] `7 ↔ T`: tương tự
- [ ] Output: `src/confusion_fixer.py`

### 5.3. Validate mã tỉnh
- [ ] Load danh sách 63 tỉnh: `data/provinces.csv`
- [ ] Kiểm tra 2 số đầu có trong danh sách
- [ ] Output: `src/province_validator.py`

### 5.4. Voting video
- [ ] Thu thập kết quả qua N frame (N=10–30)
- [ ] Voting: chọn chuỗi xuất hiện nhiều nhất
- [ ] Output: `src/video_voting.py`

### 5.5. Database
- [ ] Schema:
  ```sql
  CREATE TABLE plates (
      id INTEGER PRIMARY KEY,
      plate_text VARCHAR(20),
      confidence FLOAT,
      image_path VARCHAR(255),
      crop_path VARCHAR(255),
      timestamp DATETIME,
      vehicle_type VARCHAR(20),
      line_type VARCHAR(10),
      province VARCHAR(50),
      raw_text VARCHAR(20),
      model_version VARCHAR(20)
  );
□ SQLite cho dev, PostgreSQL cho prod
□ API CRUD: Create, Read, Update, Delete
□ Output: src/database.py, src/models.py
5.6. Web Demo
□ Backend: FastAPI
□ POST /api/upload/image
□ POST /api/upload/video
□ GET /api/plates
□ GET /api/plates/{id}
□ GET /api/stats
□ Frontend: HTML + JS (hoặc React)
□ Trang upload
□ Trang kết quả
□ Trang lịch sử
□ Trang thống kê
□ Output: web/, api/
5.7. Video Demo
□ Kịch bản: giới thiệu → upload ảnh → upload video → webcam → dashboard
□ Quay bằng OBS
□ Edit bằng DaVinci Resolve/CapCut
□ Output: demo/video_demo.mp4
5.8. Docker Deployment
□ Dockerfile cho backend
□ Dockerfile cho frontend
□ docker-compose.yml
□ Output: Dockerfile, docker-compose.yml
6. LÝ THUYẾT CẦN NẮM
Regex: pattern matching, capture groups

FastAPI: routing, request/response, async

SQLite/PostgreSQL: schema, query, index

REST API: CRUD, status codes

Docker: image, container, volume, network

HTML/CSS/JS: DOM, fetch API

7. TIÊU CHÍ ĐÁNH GIÁ
Metric	Target
End-to-end accuracy	≥ 0.70
Latency (ảnh)	≤ 1s
Web demo	Chạy được
Database	Lưu 100% kết quả
8. DEPENDENCIES
Phụ thuộc WP1, WP2, WP3

Là lớp cuối của pipeline

9. CẤU TRÚC CODE
text
src/
├── regex_validator.py
├── confusion_fixer.py
├── province_validator.py
├── video_voting.py
├── database.py
├── models.py
└── pipeline_wp4.py
api/
├── main.py
├── routes/
│   ├── upload.py
│   ├── plates.py
│   └── stats.py
web/
├── index.html
├── app.js
└── style.css
data/
└── provinces.csv
demo/
└── video_demo.mp4
tests/
├── test_regex.py
├── test_database.py
└── test_api.py
10. TÀI LIỆU THAM KHẢO
Thông tư 79/2024/TT-BCA: Quy chuẩn biển số

FastAPI Docs: fastapi.tiangolo.com

SQLite Docs: sqlite.org

Docker Docs: docs.docker.com

11. CHECKLIST HOÀN THÀNH
□ Regex hoạt động đúng cho 3 format
□ Fix được 8 cặp ký tự dễ nhầm
□ Validate được 63 tỉnh
□ Database lưu được 100% kết quả
□ Web demo upload ảnh chạy được
□ Web demo upload video chạy được
□ Video demo hoàn chỉnh
□ Docker build thành công
text


