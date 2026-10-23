"""Triton model serving integration.

Provides a pre-sized connection pool for the Triton Inference Server
and a simple singleton helper for non-pooled use.
"""

import logging
import random
from typing import Any

import tritonclient.grpc.aio as grpcclient
from functools import lru_cache

from config import TRITON_HOST

logger = logging.getLogger("pyapi")


class TritonClient:
    """Manage a pool of gRPC connections to Triton.

    Each connection in the pool is a long-lived HTTP/2 channel that can
    be multiplexed across concurrent requests.
    """

    def __init__(self, url: str = f"{TRITON_HOST}:8001", pool_size: int = 8):
        self.url: str = url
        self.pool_size: int = pool_size
        self._clients: list[grpcclient.InferenceServerClient] = []

    async def init(self):
        """Create *N* persistent gRPC channels."""
        for _ in range(self.pool_size):
            client = grpcclient.InferenceServerClient(url=self.url)
            self._clients.append(client)
        logger.info("triton_pool_initialized", extra={"pool_size": self.pool_size, "url": self.url})

    async def get_health(self):
        """Return a health-check dict for this pool.

        Checks the first pool client (all clients share the same gRPC
        connection / model metadata) against every model we expect.
        """
        health: dict[str, Any] = {"status": "healthy", "models": {}}
        client = self._clients[0] if self._clients else None
        for model_name in ["yolo_det"]:
            try:
                ready = await client.is_model_ready(model_name)
                health["models"][model_name] = "ready" if ready else "not_ready"
                if not ready:
                    health["status"] = "unhealthy"
            except Exception as exc:
                health["status"] = "unhealthy"
                health["models"][model_name] = f"error: {exc}"
        return health

    def get_client(self) -> grpcclient.InferenceServerClient:
        """Return a random client from the pool.

        Hundreds of requests can share the same client to call
        ``async_infer`` concurrently (connection multiplexing).
        """
        return random.choice(self._clients)

    async def close(self):
        """Close all gRPC channels during application shutdown."""
        logger.info("triton_pool_closed", extra={"pool_size": self.pool_size})
        for client in self._clients:
            await client.close()


@lru_cache(maxsize=1)
def get_triton_client(url: str = f"{TRITON_HOST}:8001") -> grpcclient.InferenceServerClient:
    """Return a singleton Triton client (use instead of the pool for simple cases)."""
    return grpcclient.InferenceServerClient(url=url)
