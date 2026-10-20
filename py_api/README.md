# py_api — Tổng quan

## Mục đích

`py_api` là một **FastAPI service** đóng vai trò gateway giữa client và **NVIDIA Triton Inference Server**, chuyên thực hiện **object detection** (YOLO) trên ảnh upload.

## Cấu trúc thư mục

```
py_api/
├── Dockerfile
├── requirements.txt
├── yolo26n.onnx
└── src/
    ├── main.py              # Entry point, lifespan, router registration
    ├── routers/
    │   ├── __init__.py
    │   ├── depends.py       # Dependency injection cho TritonClient pool
    │   └── yolo.py          # API endpoints
    └── services/
        ├── __init__.py
        ├── triton.py         # TritonClient pool + cached singleton
        └── image_detection.py # Tiền xử lý ảnh, inference, vẽ kết quả
```

## Luồng xử lý

```
Client (POST /yolo/detect)
    │
    ▼
UploadFile (multipart/form-data)
    │
    ▼
routers/yolo.py:detect()
    │  ── đọc bytes ──► cv2.imdecode()
    │
    ▼
services/image_detection.py:detect_image()
    │  ── _letterbox() ──► resize + pad 640×640, normalize
    │  ── client.infer(model="yolo_det") ──► gRPC async
    │  ── _draw_boxes() ──► scale tọa độ + vẽ rectangle + label
    │
    ▼
Response (image/jpeg)
```

## API Endpoints

| Method | Path | Mô tả |
|--------|------|-------|
| `GET`  | `/yolo/health` | Kiểm tra trạng thái model `yolo_det` và `yolo_seg` trên Triton |
| `POST` | `/yolo/detect` | Nhận ảnh upload → trả về ảnh có bounding boxes |

### POST /yolo/detect

**Request:**
- `Content-Type`: `multipart/form-data`
- Field `image`: file ảnh (bất kỳ định dạng nào OpenCV hỗ trợ)

**Response:**
- `Content-Type`: `image/jpeg`
- Body: ảnh JPEG đã vẽ bounding boxes

### GET /yolo/health

**Response:**
```json
{
  "yolo_det": "healthy",
  "yolo_seg": "healthy"
}
```

## Thành phần chính

### 1. `main.py` — Application Entry Point

- Khởi tạo **TritonClient pool** (8 connections mặc định) qua `lifespan`
- Pool được tạo khi app khởi động, đóng khi app tắt
- Chạy trên port **8080**

### 2. `routers/yolo.py` — API Routes

- Prefix `/yolo`
- Sử dụng FastAPI `Depends` để inject TritonClient từ pool
- Endpoint `detect` đọc file upload, gọi service, trả về JPEG

### 3. `services/triton.py` — Triton Client Pool

- **`TritonClient`**: Pool cố định N gRPC clients (default 8)
  - Mỗi client = 1 TCP/HTTP2 connection riêng
  - `get_client()`: chọn ngẫu nhiên 1 client (không lock, không wait)
  - Nhiều request có thể **multiplex** trên cùng 1 client
- **`get_triton_client()`**: cached singleton (lru_cache) cho dependency injection

### 4. `services/image_detection.py` — Inference Pipeline

| Hàm | Mô tả |
|-----|-------|
| `_letterbox()` | Resize + pad ảnh về 640×640, giữ tỷ lệ, normalize [0,1] |
| `detect_image()` | Gọi Triton gRPC async với model `yolo_det` |
| `_draw_boxes()` | Scale tọa độ về ảnh gốc, vẽ rectangle + label, confidence ≥ 0.25 |

- **Classes**: 80 COCO classes (person, car, dog, ...)
- **Confidence threshold**: 0.25
- **Input/Output**: numpy RGB array (không dùng PIL)

## Cấu hình

| Environment Variable | Default | Mô tả |
|---------------------|---------|-------|
| `TRITON_POOL_SIZE` | `8` | Số lượng gRPC connections trong pool |
| `TRITON_HOST` | `localhost` | Địa chỉ Triton Inference Server |

## Dependencies

| Package | Version | Mục đích |
|---------|---------|----------|
| `fastapi` | 0.143.2 | Web framework |
| `uvicorn` | 0.54.0 | ASGI server |
| `tritonclient[all]` | 2.73.0 | gRPC client cho Triton |
| `opencv-python-headless` | 5.0.0.93 | Tiền/xử lý ảnh (không GUI) |
| `Pillow` | 13.0.0 | Hỗ trợ ảnh |
| `python-multipart` | 0.0.32 | Parse multipart/form-data |

## Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./src .
CMD ["python", "main.py"]
```

## Cách chạy

```bash
# Local
pip install -r requirements.txt
python src/main.py

# Docker
docker build -t py_api .
docker run -p 8080:8080 -e TRITON_HOST=your-triton-host py_api
```

## Kiến trúc pool

```
┌──────────────────────────────────────────┐
│           TritonClient Pool (N=8)         │
│  ┌──────┐ ┌──────┐       ┌──────┐        │
│  │Conn 1│ │Conn 2│  ...  │Conn N│        │
│  └──────┘ └──────┘       └──────┘        │
│     ▲         ▲               ▲           │
│     │         │               │           │
│     └── random.choice() ──────┘           │
│       (không lock, multiplexing)          │
└──────────────────────────────────────────┘
         │ gRPC async_infer
         ▼
┌──────────────────────────────────────────┐
│     Triton Inference Server               │
│     ┌────────────┐  ┌────────────┐       │
│     │ yolo_det   │  │ yolo_seg   │       │
│     └────────────┘  └────────────┘       │
└──────────────────────────────────────────┘
```
