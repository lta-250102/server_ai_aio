from fastapi import APIRouter, Request
from typing import Dict, Any
import os
import logging

logger = logging.getLogger("pyapi")


router = APIRouter(tags=["health"])


@router.get("/health", response_model=Dict[str, Any])
async def health_check(request: Request):
    """Global health check for the entire application.

    Checks all critical dependencies and returns their status.

    **Response:**
    - `status`: "healthy" if all checks pass, "degraded" if some fail
    - `checks`: individual status for each dependency

    **Example:**
    ```json
    {
      "status": "degraded",
      "checks": {
        "triton": {"status": "healthy", "models": {"yolo_det": "ready", "yolo_seg": "ready"}},
        "mongodb": {"status": "healthy"},
        "clickhouse": {"status": "unhealthy", "error": "connection timeout"},
        "llm": {"status": "unhealthy", "error": "503 Service Unavailable"}
      }
    }
    ```
    """
    health = {"status": "healthy", "checks": {}}
    all_healthy = True

    # --- Triton check (delegate to TritonClient.get_health) ---
    try:
        triton_client = request.app.state.triton_client
        triton_health = await triton_client.get_health()
        if triton_health["status"] != "healthy":
            all_healthy = False
    except Exception as e:
        triton_health = {"status": "unhealthy", "error": str(e)}
        all_healthy = False
    health["checks"]["triton"] = triton_health

    # --- MongoDB check ---
    mongo_health: Dict[str, Any] = {"status": "healthy"}
    try:
        mongo_client = request.app.state.mongo_client
        # Ping MongoDB to verify connection
        mongo_client.admin.command("ping")
    except Exception as e:
        mongo_health["status"] = "unhealthy"
        mongo_health["error"] = str(e)
        all_healthy = False

    health["checks"]["mongodb"] = mongo_health

    # --- ClickHouse check ---
    ch_health: Dict[str, Any] = {"status": "healthy"}
    try:
        from clickhouse_driver import Client

        ch_client = Client.from_url(
            f"clickhouse://bytehouse:{os.getenv('BYTEHOUSE_KEY')}@gateway.aws-us-east-1.bytehouse.cloud:19000/?secure=true"
        )
        ch_client.execute("SELECT 1")
    except Exception as e:
        ch_health["status"] = "unhealthy"
        ch_health["error"] = str(e)
        all_healthy = False

    health["checks"]["clickhouse"] = ch_health

    # --- LLM check (lightweight model list, non-blocking) ---
    llm_health: Dict[str, Any] = {"status": "healthy"}
    try:
        llm_url = os.getenv("LLM_URL")
        llm_key = os.getenv("LLM_API_KEY")
        if not llm_url or not llm_key:
            llm_health["status"] = "unhealthy"
            llm_health["error"] = "LLM_URL or LLM_API_KEY not configured"
            all_healthy = False
        else:
            import httpx

            with httpx.Client(verify=True, timeout=5) as client:
                resp = client.get(
                    f"{llm_url}/models",
                    headers={"Authorization": f"Bearer {llm_key}"},
                )
                if resp.status_code != 200:
                    llm_health["status"] = "unhealthy"
                    llm_health["error"] = f"{resp.status_code} {resp.text[:200]}"
                    all_healthy = False
    except Exception as e:
        llm_health["status"] = "unhealthy"
        llm_health["error"] = str(e)
        all_healthy = False

    health["checks"]["llm"] = llm_health

    # Set overall status
    if not all_healthy:
        health["status"] = "degraded"
        logger.warning("health_check_degraded", extra={"status": "degraded", "checks": health["checks"]})

    return health
