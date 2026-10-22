# py_api — AI Gateway Service

## Mục đích

`py_api` là một **FastAPI AI Gateway** cung cấp 3 mặt hàng chính:

| Mặt hàng | Mô tả |
|----------|-------|
| **YOLO Object Detection** | Upload ảnh → trả về ảnh có bounding boxes (inference qua NVIDIA Triton) |
| **UA Agent (Chat)** | Conversational AI phân tích User Acquisition (ROAS, CPI, Retention, …) backed bởi LangGraph + DeepAgents |
| **User Management** | CRUD admin API quản lý user, game assignment, authentication |

## Kiến trúc tổng thể

```
┌──────────┐          ┌──────────────────────────────────────────┐
│  Client  │─────────►│         py_api (FastAPI)                  │
│          │ POST     │                                          │
│          │─────────►│  ┌─────────────┐  ┌──────────────────┐  │
│          │ POST     │  │ /yolo/detect │  │ /agent/chat      │  │
│          │ POST     │  │ (Image JPG)  │  │ (Conversational) │  │
│          │─────────►│  └─────┬────────┘  └────────┬─────────┘  │
└──────────┘          │        │                    │             │
                      │        │                    │             │
                      ▼        ▼                    ▼             │
              ┌─────────────┐  ┌──────────┐    ┌──────────┐      │
              │ Triton      │  │ MongoDB  │    │ ClickHouse│     │
              │ gRPC Pool   │  │ (Users + │    │ /ByteHouse│     │
              │ (N=8 conn)  │  │  Threads)│    │ DWH)      │     │
              └─────────────┘  └──────────┘    └──────────┘      │
                                                       ▲         │
                      ┌─────────────┐                   │         │
                      │ GrowX MCP   │───────────────────┘         │
                      │ HTTP JSON   │  (Agent tools)              │
                      └─────────────┘                             │
                      └──────────────────────────────────────────┘
```

## Cấu trúc thư mục

```
py_api/
├── Dockerfile
├── requirements.txt
└── src/
    ├── main.py                    # Entry point, lifespan, app init
    ├── utils.py                   # Structured logging, serializables
    ├── agents/
    │   ├── __init__.py            # Agent registry (agent_map), init_agent()
    │   ├── tools.py               # LangChain tools: UA + SQL + MCP
    │   ├── ua_agent.py            # UA Agent: system prompt, state, context schema
    │   └── skills/ua_agent/
    │       ├── appsflyer-data/    # Appsflyer DWH skill + case studies
    │       ├── bigdata/           # Bigdata DWH skill + case studies
    │       └── growx-mcp/         # GrowX MCP skill + case studies
    ├── db/
    │   ├── __init__.py             # Re-export
    │   └── user.py                 # MongoDB user CRUD helpers
    ├── models/
    │   ├── domain.py               # Shared domain models (Game, UserContext)
    │   ├── dto.py                  # Request/Response Pydantic schemas
    │   └── entity.py               # MongoDB entity models (User)
    ├── routers/
    │   ├── __init__.py             # Router mounts
    │   ├── depends.py              # FastAPI dependencies (user, agent, triton)
    │   ├── agent.py                # UA Agent chat & thread endpoints
    │   ├── health.py               # Multi-dependency health check
    │   ├── user.py                 # User CRUD admin endpoints
    │   └── yolo.py                 # YOLO object detection endpoint
    └── services/
        ├── __init__.py             # Re-export
        ├── triton.py               # Triton gRPC client pool
        └── image_detection.py      # YOLO pipeline: letterbox → infer → draw
```

## Luồng xử lý

### 1. YOLO Object Detection

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
    │  ── _letterbox() ──► resize + pad 640x640, giữ tỷ lệ, normalize
    │  ── TritonClient.get_client() ──► random multiplex vào pool
    │  ── client.infer(model="yolo_det") ──► gRPC async
    │  ── _draw_boxes() ──► scale tọa độ + vẽ bbox + label (conf >= 0.25)
    │
    ▼
Response (image/jpeg)
```

### 2. UA Agent Chat

```
Client (POST /agent/chat)
    │  Headers: x-user-id, x-agent-name
    │  Body: { thread_id, messages, stream }
    │
    ▼
routers/agent.py:chat()
    │  ── Depends(get_current_user) ──► validate user từ MongoDB
    │  ── Depends(get_ai_agent) ───────► load agent từ app.state.agents
    │  ── Agent.get_state() ───────────► restore conversation context
    │
    ├── Stream mode (stream=true)
    │    └─► agent.astream_events() ──► SSE text/event-stream
    │         ── make_serializable() ──► JSON-safe events
    │         ── request.is_disconnected() ──► auto-cleanup
    │
    └── Non-stream mode (stream=false)
         └─► agent.ainvoke() ──► full response dict
    │
    ▼
MongoDBSaver (checkpoint per thread, TTL 30 ngày)
```

## API Endpoints

### YOLO Detection

| Method | Path | Mô tả |
|--------|------|-------|
| `POST` | `/yolo/detect` | Upload ảnh → trả về ảnh có bounding boxes |

**POST /yolo/detect**

- **Input:** `multipart/form-data` field `image`
- **Output:** `image/jpeg` — ảnh đã vẽ bounding boxes (COCO 80 classes, conf >= 0.25)

### UA Agent (Chat & Threads)

| Method | Path | Mô tả |
|--------|------|-------|
| `GET` | `/agent/threads` | Danh sách threads của user (phân trang) |
| `GET` | `/agent/threads/{id}` | Lịch sử messages của thread |
| `PATCH` | `/agent/threads/rename/{id}` | Đổi tên thread |
| `DELETE` | `/agent/threads/{id}` | Xóa thread |
| `POST` | `/agent/chat` | Gửi tin nhắn, nhận phản hồi AI (stream / non-stream) |

**POST /agent/chat**

- **Headers:**
  - `x-user-id` (str) — MongoDB ObjectId của user
  - `x-agent-name` (str) — Tên agent (vd: `ua_agent`)
  - `x-growx-mcp-personal-key` (str) — Personal key cho GrowX MCP
- **Body:**
```json
{
  "thread_id": "abc123",
  "messages": [
    {"role": "user", "content": "Phân tích ROAS campaign A"}
  ],
  "stream": false
}
```
- **Output:** Dict phản hồi của agent (hoặc SSE stream nếu `stream=true`)

### User Management

| Method | Path | Mô tả |
|--------|------|-------|
| `POST` | `/user/create` | Tạo user mới |
| `GET` | `/user/list` | Danh sách tất cả user |
| `GET` | `/user/get/{id}` | Lấy thông tin user theo id |
| `PATCH` | `/user/update/{id}` | Cập nhật user (partial update) |
| `DELETE` | `/user/delete/{id}` | Xóa user |

### Health Check

| Method | Path | Mô tả |
|--------|------|-------|
| `GET` | `/health` | Kiểm tra tất cả dependencies (Triton, MongoDB, ClickHouse, LLM) |

**GET /health**

```json
{
  "status": "healthy",
  "checks": {
    "triton": {"status": "healthy", "models": {"yolo_det": "ready"}},
    "mongodb": {"status": "healthy"},
    "clickhouse": {"status": "healthy"},
    "llm": {"status": "healthy"}
  }
}
```

## Thành phần chi tiết

### 1. `main.py` — Application Lifecycle

| Yếu tố | Giá trị |
|--------|--------|
| Port | `8080` |
| Triton Pool | `TRITON_POOL_SIZE` (default: 8) |
| MongoDB | Connection pool (maxPoolSize=50, maxIdleTimeMS=30s) |
| Agents | Pre-load từ `agent_map` khi startup |
| Logging | Structured JSON (DEBUG/WARN/ERROR) + plain text (INFO) |

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(...)
    app.state.triton_client = TritonClient(pool_size=...)
    await app.state.triton_client.init()
    app.state.mongo_client = MongoClient(...)
    app.state.agents = {name: await init_agent(name, ...) for name in agent_map}
    yield
    await app.state.triton_client.close()
    app.state.mongo_client.close()
```

### 2. Triton Client Pool

Pool cố định N gRPC clients, **không lock, không wait**:

- Mỗi client = 1 TCP/HTTP2 connection riêng
- `get_client()`: `random.choice()` — nhiều request **multiplex** trên cùng 1 client
- Auto-close khi app shutdown
- Health check: kiểm tra model readiness

### 3. UA Agent (LangGraph + DeepAgents)

**Registry (`agent_map`):**

```python
agent_map = {
    "ua_agent": {
        "system_prompt": ...,
        "model": ChatOpenAI(model="falcon-llm", ...),
        "tools": [...],
        "context_schema": Context,
        "state_schema": State,
    },
}
```

**Model:** Falcon LLM qua OpenAI-compatible endpoint (`LLM_URL`), enabled thinking mode, temperature=0.7, top_p=0.8, presence_penalty=1.5.

**State Schema:**
```python
class State(DeepAgentState):
    thread_name: str  # Auto-generated from last user message
```

**Context Schema:**
```python
class Context(UserContext):
    user_id: str
    games: list[Game]        # Games được phân bổ cho user
    growx_mcp_personal_key: str  # Per-user MCP key
```

**Memory:** LangGraph checkpoints lưu trên MongoDB (`MongoDBSaver`), TTL 30 ngày.

### 4. Tools (Agent Tools)

**GrowX MCP Tools** (HTTP JSON-RPC, không cần MCP dependency):

| Tool | Mô tả |
|------|-------|
| `ua_list_apps` | Danh sách game/app trong hệ thống |
| `ua_list_networks` | Danh sách ad networks |
| `ua_list_connectors` | Danh sách ad accounts |
| `ua_describe_metrics` | Metric dictionary (ROAS, CPI, retention, …) |
| `ua_list_campaigns` | Performance campaigns theo game/network/window |

**SQL Query Tool:**

| Tool | Mô tả |
|------|-------|
| `query_sql` | Query ClickHouse/ByteHouse, có access control theo games của user |

**DWH MCP Tools:**

- Load từ Falcon Data MCP server (`FALCON_DATA_MCP_SERVER`)
- Tự động register khi init module

**Access Control (query_sql):**
- Parse SQL bằng `sqlglot` để tìm game references (package name, UUID)
- Chỉ cho query data thuộc games được phân bổ cho user

### 5. YOLO Image Detection

| Thành phần | Chi tiết |
|------------|----------|
| Model | `yolo_det` trên Triton |
| Input size | 640x640 (letterbox giữ tỷ lệ) |
| Classes | 80 COCO classes |
| Confidence threshold | 0.25 |
| Processing | Pure numpy + OpenCV (không dùng PIL) |
| Output | RGB numpy array với bounding boxes |

### 6. User Management

- **Storage:** MongoDB
- **Auth:** `x-user-id` header (MongoDB ObjectId)
- **User model:** `{user_name, user_email, games: [Game]}`
- **Game model:** `{app_id, package_name, app_name, platform}`
- **Email validation:** Pydantic field validator
- **Thread ownership:** Mỗi thread gắn với user_id, access control khi đọc/ghi/xóa

## Data Flow — Agent Tools

```
UA Agent
    │
    ├──► GrowX MCP (HTTP JSON-RPC)
    │      GET https://growx-host/grow-x/api/v1/mcp
    │      Headers: Bearer {GROWX_MCP_TOKEN}, x-growx-mcp-personal-key
    │      Body: {jsonrpc, method: "tools/call", params: {name, arguments}}
    │
    ├──► ClickHouse / ByteHouse (SQL)
    │      ch_client.execute(sql)
    │      Access control: filter by user's games
    │
    └──► DWH MCP (FastMCP over Streamable HTTP)
           https://dwh-host/mcp
           Headers: Dev-Key: {FALCON_DATA_MCP_TOKEN}
```

## Cấu hình

| Environment Variable | Default | Mô tả |
|---------------------|---------|-------|
| `TRITON_POOL_SIZE` | `8` | Số gRPC connections trong pool |
| `TRITON_HOST` | `localhost` | Địa chỉ Triton Inference Server |
| `MONGO_CONNECTION_STRING` | `mongodb://localhost:27017/` | MongoDB connection string |
| `MONGO_DB_NAME` | `growx_agent` | DB chứa LangGraph checkpoints |
| `LLM_URL` | — | LLM endpoint (OpenAI-compatible) |
| `LLM_API_KEY` | — | LLM API key |
| `GROWX_MCP_SERVER` | — | GrowX MCP server URL |
| `GROWX_MCP_TOKEN` | — | GrowX MCP auth token |
| `FALCON_DATA_MCP_SERVER` | — | Falcon Data DWH MCP URL |
| `FALCON_DATA_MCP_TOKEN` | — | Falcon Data DWH MCP token |
| `BYTEHOUSE_KEY` | — | ByteHouse/ClickHouse auth key |
| `LOG_LEVEL` | `INFO` | Logging level |

## Dependencies

| Package | Version | Mục đích |
|---------|---------|----------|
| `fastapi` | 0.143.2 | Web framework |
| `uvicorn` | 0.54.0 | ASGI server |
| `tritonclient[all]` | 2.73.0 | gRPC client cho Triton Inference Server |
| `opencv-python-headless` | 5.0.0.93 | Image processing (no GUI) |
| `python-multipart` | 0.0.32 | Multipart form-data parsing |
| `pydantic` | 2.13.4 | Request/response validation |
| `langchain[mcp]` | 1.4.1 | Tool abstraction + MCP client |
| `langchain-openai` | 1.3.3 | LLM bridge (OpenAI-compatible) |
| `deepagents` | 0.6.12 | Deep agent framework (LangGraph-based) |
| `langgraph` | 1.2.11 | State machine / graph-based agents |
| `langgraph-checkpoint-mongodb` | 0.4.0 | MongoDB persistence for agent state |
| `langchain-core` | 1.6.3 | Core LangChain abstractions |
| `clickhouse-driver` | 0.2.10 | ClickHouse/ByteHouse query |
| `sqlglot` | 30.20.0 | SQL parsing for access control |
| `mlflow` | 3.14.0 | Experiment tracking |
| `pymongo` | — | MongoDB driver |
| `httpx` | — | HTTP client for MCP servers |

## Docker

```dockerfile
# Multi-stage build: builder → runtime (non-root)
FROM python:3.11-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*
COPY ./src .

RUN adduser --disabled-password --no-create-home appuser
USER appuser

HEALTHCHECK --interval=5m --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

CMD ["python", "main.py"]
```

## Cách chạy

```bash
# Local
pip install -r requirements.txt
python src/main.py

# Docker
docker build -t py_api .
docker run -p 8080:8080 \
  -e TRITON_HOST=your-triton-host \
  -e MONGO_CONNECTION_STRING=mongodb://mongo:27017/ \
  -e LLM_URL=https://llm-host/v1 \
  -e LLM_API_KEY=your-key \
  py_api
```

## Kiến trúc Pool — Multiplexing

```
┌──────────────────────────────────────────────────────┐
│           TritonClient Pool (N=8 connections)         │
│  ┌────────┐ ┌────────┐        ┌────────┐             │
│  │Conn  1 │ │Conn  2 │  ...   │Conn  N │             │
│  └────────┘ └────────┘        └────────┘             │
│       ▲         ▲                  ▲                  │
│       │         │                  │                  │
│       └── random.choice() ─────────┘                  │
│         (không lock — nhiều request dùng chung 1 conn) │
└──────────────────────────────────────────────────────┘
                │ gRPC async_infer (HTTP/2 multiplex)
                ▼
┌──────────────────────────────────────────────────────┐
│        Triton Inference Server                        │
│        Model: yolo_det                               │
└──────────────────────────────────────────────────────┘
```

## Luồng Stream (SSE)

```
Client                          py_api                       Agent
  │   POST /agent/chat              │                         │
  │   {stream: true}                │                         │
  │  ────────────────────────────►  │                         │
  │                                 │  astream_events()       │
  │                                 │  ─────────────────────►  │
  │                                 │                         │
  │   ◄─── text/event-stream ─────  │  event 1                │
  │       data: {node_a_start}      │                         │
  │   ◄─── text/event-stream ─────  │  event 2                │
  │       data: {node_b_start}      │                         │
  │   ...                           │  ...                    │
  │   ◄─── text/event-stream ─────  │  stream_done            │
  │       data: [DONE]              │                         │
  │                                 │                         │
  │  (auto-cancel nếu client disconnect)                       │
```

## Security

- **User Auth:** `x-user-id` header, validated against MongoDB
- **Thread Isolation:** Mỗi thread gắn với `user_id`, không cross-access
- **SQL Access Control:** Parse SQL AST bằng `sqlglot`, filter game references
- **Non-root Docker:** Chạy dưới `appuser`
- **Structured Logging:** JSON output cho debug/warn/error, plain text cho info flow
