# Server AI AIO

Central AI server providing LLM inference, image detection (YOLO), and agentic chat — all orchestrated via Docker Compose.

---

## Architecture

```
┌──────────────┐     ┌──────────────────┐
│   Client     │────▶│  py_api :8080    │
│              │     │  (FastAPI)       │
│              │────▶│                  │
│              │     │  /yolo/detect    │────┐
│              │     │  /agent/chat     │    │
│              │     │  /user/*         │    │
└──────────────┘     └──────────────────┘    │
                                            │
  py_api integrates with:                   │
  • Triton Inference Server (YOLO)          │
  • MongoDB (session / user store)          │
  • vLLM / LiteLLM (LLM proxy)             │
  • ByteHouse / ClickHouse (DWH queries)    │
  • GrowX MCP (UA data)                     │
  • Falcon Data MCP (docs)                  │
  • MLflow (experiment tracking)            │
                                             │
  ┌─────────────┐    ┌──────────────────────┐
  │ Triton      │◀───│ vLLM (:8000)         │
  │ (:8000-2)   │    │ Qwen3.6-35B-A3B-FP8  │
  │ YOLO models │    │                      │
  └─────────────┘    └──────────────────────┘
                              │
                      ┌───────▼───────┐
                      │ LiteLLM      │
                      │ (:8000)       │
                      │ Unified API   │
                      └───────────────┘
```

### Services overview

| Service | Port(s) | Purpose |
|---|---|---|
| **py\_api** | 8080 | FastAPI application — YOLO detection, agent chat, user management |
| **go\_api** | 8090 | Go version of the API (currently commented out in docker-compose) |
| **postgres** | 5432 | PGAdmin for metadata; backend for LiteLLM |
| **pgadmin** | 8068 | PostgreSQL GUI |
| **redis** | 6379 | Cache / session store |
| **qdrant** | 6333 | Vector store |
| **mongo** | 27017 | LangGraph checkpointer + user persistence |
| **storage** | 9000/9001 | RustFS (S3-compatible object storage) |
| **triton** | 8000/8001/8002 | NVIDIA Triton Inference Server — runs YOLO det model |
| **laya** | 8000 | LLM serving via SystemLM (multilingual) |
| **vllm** | 8000 | LLM serving via vLLM — `Qwen3.6-35B-A3B-FP8` |
| **litellm** | 8000 | LiteLLM proxy — unified OpenAI-compatible API |

---

## Quick start

### Prerequisites

- Docker & Docker Compose v2
- NVIDIA GPU with CUDA 12+ (for `vllm`, `triton`, `laya`)
- At least 24 GB GPU memory for vLLM

### 1. Clone and configure

```bash
git clone <repo-url>
cd server-ai-aio

cp .env.example .env
# Edit .env — fill in passwords and external service URLs
```

See [Environment variables](#environment-variables) below for a full list.

### 2. Start infrastructure

```bash
# All services
docker compose up -d

# Only data layer (no GPU services)
docker compose up -d postgres redis mongo qdrant storage pgadmin
```

### 3. Start LLM backends (requires GPU)

```bash
docker compose up -d vllm laya litellm triton
```

### 4. Start the API

```bash
docker compose up -d py_api
# or the Go API
# docker compose up -d go_api
```

### 5. Verify

```bash
curl http://localhost:8080/health
# → {"status": "healthy", "checks": {"triton": ..., "mongodb": ..., ...}}
```

### Stop everything

```bash
docker compose down
```

---

## API reference

Base URL: `http://localhost:8080`

### Health check

```
GET /health
```

Parallel health checks for Triton, MongoDB, ClickHouse, and LLM.

### YOLO Detection

```
POST /yolo/detect
Content-Type: multipart/form-data

image: <binary JPEG/PNG>
```

**Response:** `image/jpeg` — the original image with bounding boxes drawn.

**Query parameters:** (none; all config via environment)

### Agent Chat

```
POST /agent/chat
Headers:
  x-growx-mcp-personal-key: <your personal key>
Content-Type: application/json

{
  "thread_id": "uuid-here",
  "messages": [
    {"role": "user", "content": "Show me ROAS for game X last week"}
  ],
  "stream": false
}
```

**Response (non-stream):** JSON with the agent's final message.

**Response (stream):** SSE events (`data: <JSON>\n\n`) with LangGraph v2 events.

### Agent Threads

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/agent/threads?skip=0&limit=50` | List threads for authenticated user |
| `GET` | `/agent/threads/{thread_id}` | Get full message history |
| `PATCH` | `/agent/threads/rename/{thread_id}?new_name=...` | Rename a thread |
| `DELETE` | `/agent/threads/{thread_id}` | Delete a thread |

### User Management (Admin)

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/user/create` | Create a user (body: `user_name`, `user_email`, `games`) |
| `GET` | `/user/list` | List all users |
| `GET` | `/user/get/{user_id}` | Get user by ID |
| `PATCH` | `/user/update/{user_id}` | Partial-update a user |
| `DELETE` | `/user/delete/{user_id}` | Delete a user |

---

## Environment variables

Copy `.env.example` → `.env` and configure. Key variables:

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | — | PostgreSQL password |
| `PGADMIN_DEFAULT_EMAIL` | — | PGAdmin login |
| `PGADMIN_DEFAULT_PASSWORD` | — | PGAdmin password |
| `REDIS_PASSWORD` | — | Redis auth |
| `MONGO_INITDB_ROOT_USERNAME` | — | MongoDB root username |
| `MONGO_INITDB_ROOT_PASSWORD` | — | MongoDB root password |
| `RUSTFS_ACCESS_KEY` | — | Storage S3 access key |
| `RUSTFS_SECRET_KEY` | — | Storage S3 secret key |
| `RUSTFS_REGION` | `us-east-1` | Storage region |
| `HF_TOKEN` | — | HuggingFace token (for LLM models) |
| `LLM_URL` | — | vLLM endpoint URL |
| `LLM_API_KEY` | — | vLLM API key |
| `TRITON_HOST` | `localhost` | Triton Inference Server host |
| `TRITON_POOL_SIZE` | `8` | gRPC connection pool size |
| `MONGO_CONNECTION_STRING` | — | Full MongoDB connection string |
| `MONGO_DB_NAME` | `aio_ai` | Database name |
| `GROWX_MCP_SERVER` | — | GrowX MCP server URL |
| `GROWX_MCP_TOKEN` | — | GrowX MCP auth token |
| `BYTEHOUSE_KEY` | — | ByteHouse API key |
| `BYTEHOUSE_URL` | — | ByteHouse ClickHouse URL |
| `FALCON_DATA_MCP` | — | Falcon Data MCP server URL |
| `FALCON_DATA_MCP_TOKEN` | — | Falcon Data MCP token |
| `MLFLOW_TRACKING_URI` | — | MLflow tracking server |
| `MLFLOW_TRACKING_USERNAME` | — | MLflow username |
| `MLFLOW_TRACKING_PASSWORD` | — | MLflow password |
| `MLFLOW_WORKSPACE` | `aio_ai` | MLflow workspace |

---

## Project structure

```
.
├── docker-compose.yml        # Full orchestration
├── .env.example              # Environment variable reference
├── .env                      # Local overrides (gitignored)
├── py_api/                   # Python API (FastAPI)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py           # App entrypoint + lifespan
│       ├── config.py         # Env-var loading
│       ├── utils.py          # Helpers (logging, serialization)
│       ├── routers/
│       │   ├── health.py     # GET /health
│       │   ├── yolo.py       # POST /yolo/detect
│       │   ├── agent.py      # Chat + thread endpoints
│       │   ├── user.py       # User CRUD
│       │   └── depends.py    # FastAPI dependency injection
│       ├── agents/
│       │   ├── __init__.py   # Agent factory (LangGraph/DeepAgents)
│       │   ├── ua_agent.py   # UA specialist prompt + state
│       │   └── tools.py      # MCP tools + ClickHouse query tool
│       ├── services/
│       │   ├── triton.py     # Triton gRPC pool
│       │   └── image_detection.py  # YOLO pre/post-processing
│       ├── models/
│       │   ├── dto.py        # Request/response schemas (Pydantic)
│       │   ├── entity.py     # DB entity models
│       │   └── domain.py     # Domain types (Game, UserContext)
│       └── db/
│           └── user.py       # MongoDB user operations
├── go_api/                   # Go API (gin + OpenCV)
│   ├── Dockerfile
│   ├── main.go
│   ├── controllers/yolo.go
│   └── services/triton.go
├── triton/                   # Triton model serving
│   ├── Dockerfile
│   └── models/
│       ├── yolo_det/         # YOLO detection model (ONNX)
│       └── yolo_seg/         # YOLO segmentation model (ONNX)
├── llm/
│   ├── litellm_config.yml    # LiteLLM model config
│   └── bench.sh              # Benchmark script
├── db/                       # Persistent data volumes
│   ├── postgres_data/
│   ├── mongo_data/
│   ├── qdrant_data/
│   └── storage_data/
├── locust_test/              # Load testing (Locust)
│   └── locustfile.py
└── draft.ipynb               # Development notebook
```

---

## Development

### Local Python API

```bash
cd py_api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Start dev server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

### Local Go API

```bash
cd go_api
docker build -t go_api .
docker run -p 8090:8090 go_api
```

### YOLO model export

Model files are checked in at the root:

| File | Format | Size |
|---|---|---|
| `yolo26n.pt` | PyTorch | 5.3 MB |
| `yolo26n.onnx` | ONNX | 9.5 MB |
| `yolo26n.engine` | TensorRT | 12.9 MB |

Triton loads the ONNX model from `triton/models/yolo_det/1/model.onnx`.

### MLflow

Track experiments by setting `MLFLOW_TRACKING_URI` in `.env`:

```python
import mlflow
mlflow.set_tracking_uri(os.environ["MLFLOW_TRACKING_URI"])
mlflow.set_tracking_uri(f"http://123.31.41.83:5005/")
```

---

## Agent details

The project uses **LangGraph** + **DeepAgents** for the chat agent system. Currently one agent is configured:

### UA Agent (User Acquisition)

A gaming-industry specialist that analyzes cost, ROAS, CPI, and retention data.

**Data sources:**
1. **GrowX MCP** — primary, via HTTP tools (`ua_list_apps`, `ua_list_campaigns`, etc.)
2. **ClickHouse / ByteHouse** — direct SQL queries with row-level security
3. **Falcon Data MCP** — documentation tools loaded at startup

**Usage:**

```bash
curl -X POST http://localhost:8080/agent/chat \
  -H "x-growx-mcp-personal-key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "abc-123",
    "messages": [{"role": "user", "content": "Analyze ROAS for Air Force 4"}],
    "stream": true
  }'
```

---

## Load testing

Located in `locust_test/`:

```bash
cd locust_test
pip install locust
locust -f locustfile.py --host http://localhost:8080
# Open http://localhost:8089
```

---

## GPU requirements

| Service | GPUs needed | Min. VRAM |
|---|---|---|
| `vllm` | 1 | ~16 GB |
| `triton` | 1 | ~2 GB |
| `laya` | 1 | ~2 GB |

All GPU services use `runtime: nvidia` and `count: all` in docker-compose. Adjust the `deploy.resources` sections as needed.
