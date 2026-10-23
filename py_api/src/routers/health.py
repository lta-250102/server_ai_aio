import asyncio
import logging
import os
import httpx
from typing import Any, Dict
from clickhouse_driver import Client as ChClient
from fastapi import APIRouter, Request

logger = logging.getLogger("pyapi")

router = APIRouter(tags=["health"])


async def _check_triton(request: Request) -> tuple[str, Dict[str, Any]]:
    """Check Triton model readiness."""
    try:
        triton_client = request.app.state.triton_client
        health: dict[str, Any] = {"status": "healthy", "models": {}}
        client = triton_client._clients[0] if triton_client._clients else None
        if not client:
            return "unhealthy", {"status": "unhealthy", "error": "triton pool not initialized"}
        for model_name in ["yolo_det"]:
            ready = await client.is_model_ready(model_name)
            health["models"][model_name] = "ready" if ready else "not_ready"
            if not ready:
                health["status"] = "unhealthy"
                return "unhealthy", health
        return "healthy", health
    except Exception as e:
        return "unhealthy", {"status": "unhealthy", "error": str(e)}


async def _check_mongo(request: Request) -> tuple[str, Dict[str, Any]]:
    """Check MongoDB via sync pymongo in thread pool (run_in_executor)."""
    try:
        mongo = request.app.state.mongo_client
        # Sync pymongo ping runs in a thread — does not block the event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, mongo.admin.command, "ping")
        return "healthy", {"status": "healthy"}
    except Exception as e:
        return "unhealthy", {"status": "unhealthy", "error": str(e)}


async def _check_clickhouse(request: Request) -> tuple[str, Dict[str, Any]]:
    """Check ClickHouse via shared sync client in thread pool."""
    try:
        ch_client = ChClient.from_url(os.getenv("BYTEHOUSE_URL"))
        loop = asyncio.get_running_loop()
        # Execute sync execute() in executor
        await loop.run_in_executor(None, ch_client.execute, "SELECT 1 AS ok")
        return "healthy", {"status": "healthy"}
    except Exception as e:
        return "unhealthy", {"status": "unhealthy", "error": str(e)}


async def _check_llm() -> tuple[str, Dict[str, Any]]:
    """Check LLM endpoint via async HTTP (non-blocking)."""
    llm_url = os.getenv("LLM_URL")
    llm_key = os.getenv("LLM_API_KEY")
    if not llm_url or not llm_key:
        return "unhealthy", {"status": "unhealthy", "error": "LLM_URL or LLM_API_KEY not configured"}
    try:
        async with httpx.AsyncClient(verify=True, timeout=5) as client:
            resp = await client.get(
                f"{llm_url}/models",
                headers={"Authorization": f"Bearer {llm_key}"},
            )
            if resp.status_code != 200:
                return "unhealthy", {"status": "unhealthy", "error": f"{resp.status_code} {resp.text[:200]}"}
            return "healthy", {"status": "healthy"}
    except Exception as e:
        return "unhealthy", {"status": "unhealthy", "error": str(e)}


@router.get("/health", response_model=Dict[str, Any])
async def health_check(request: Request):
    """Parallel health check for all critical dependencies.

    Runs Triton, MongoDB, ClickHouse, and LLM checks concurrently via
    asyncio.gather() so total latency is ~max(checks), not ~sum(checks).
    """
    results = await asyncio.gather(
        _check_triton(request),
        _check_mongo(request),
        _check_clickhouse(request),
        _check_llm(),
    )

    health = {"status": "healthy", "checks": {}}
    all_healthy = True

    check_names = ("triton", "mongodb", "clickhouse", "llm")
    for name, (status, detail) in zip(check_names, results):
        health["checks"][name] = detail
        if status != "healthy":
            all_healthy = False

    if not all_healthy:
        health["status"] = "degraded"
        logger.warning("health_check_degraded", extra={"checks": health["checks"]})

    return health
