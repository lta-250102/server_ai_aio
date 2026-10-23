"""Application configuration loaded from environment variables.

Centralizes every environment variable so that business code never calls
``os.getenv`` directly.  This makes the project easier to audit and to
override in tests.
"""

import os

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
TRITON_HOST: str = os.getenv("TRITON_HOST", "localhost")
TRITON_PORT: str = os.getenv("TRITON_PORT", "8001")
TRITON_POOL_SIZE: int = int(os.getenv("TRITON_POOL_SIZE", "8"))
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------
MONGO_CONNECTION_STRING: str = os.getenv(
    "MONGO_CONNECTION_STRING", "mongodb://localhost:27017/"
)
MONGO_DB_NAME: str = os.getenv("MONGO_DB_NAME", "aio_ai")

# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
LLM_URL: str = os.getenv("LLM_URL", "")
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")

# ---------------------------------------------------------------------------
# MCP / External services
# ---------------------------------------------------------------------------
GROWX_MCP_SERVER: str = os.getenv(
    "GROWX_MCP_SERVER",
    "https://growx-dev.falcongames.com/grow-x/api/v1/mcp",
)
GROWX_MCP_TOKEN: str = os.getenv("GROWX_MCP_TOKEN", "")

FALCON_DATA_MCP_SERVER: str = os.getenv(
    "FALCON_DATA_MCP_SERVER",
    "https://dwh-access.data4game.com/mcp",
)
FALCON_DATA_MCP_TOKEN: str = os.getenv("FALCON_DATA_MCP_TOKEN", "")

BYTEHOUSE_URL: str = os.getenv(
    "BYTEHOUSE_URL",
    f"clickhouse://bytehouse:{os.getenv('BYTEHOUSE_KEY', '')}@gateway.aws-us-east-1.bytehouse.cloud:19000/?secure=true&max_execution_time=60",
)
