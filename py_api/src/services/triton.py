import random
import logging
from typing import Any
import tritonclient.grpc.aio as grpcclient
import os
from functools import lru_cache


logger = logging.getLogger("pyapi")
TRITON_HOST = os.environ.get("TRITON_HOST", "localhost")

class TritonClient:
    def __init__(self, url: str = f"{TRITON_HOST}:8001", pool_size: int = 8):
        self.url = url
        self.pool_size = pool_size
        self._clients: list[grpcclient.InferenceServerClient] = []

    async def init(self):
        """Khởi tạo cố định N gRPC Channels dài hạn."""
        for _ in range(self.pool_size):
            # Mỗi client ở đây tương ứng với 1 TCP/HTTP2 Connection riêng biệt
            client = grpcclient.InferenceServerClient(url=self.url)
            self._clients.append(client)
        logger.info("triton_pool_initialized", extra={"pool_size": self.pool_size, "url": self.url})

    async def get_health(self) -> dict:
        """Return a health-check dict for this Triton pool.

        Checks the first pool client (all clients share the same gRPC
        connection / model metadata) against every model we expect to serve.
        """
        health: dict[str, Any] = {"status": "healthy", "models": {}}
        client = self._clients[0] if self._clients else None
        for model_name in ["yolo_det"]:
            try:
                ready = await client.is_model_ready(model_name)
                health["models"][model_name] = "ready" if ready else "not_ready"
                if not ready:
                    health["status"] = "unhealthy"
            except Exception as e:
                health["status"] = "unhealthy"
                health["models"][model_name] = f"error: {e}"
        return health

    def get_client(self) -> grpcclient.InferenceServerClient:
        """
        Lấy ngẫu nhiên 1 client từ Pool (KHÔNG LOCK, KHÔNG WAIT).
        Hàng trăm request có thể lấy CÙNG 1 CLIENT này để gọi async_infer song song (Multiplexing).
        """
        return random.choice(self._clients)

    async def close(self):
        """Đóng toàn bộ các kết nối khi shutdown app."""
        logger.info("triton_pool_closed", extra={"pool_size": self.pool_size})
        for client in self._clients:
            await client.close()

# use this if singleton insteaded of pool
@lru_cache(maxsize=1)
def get_triton_client(url: str = f"{TRITON_HOST}:8001"):
    return grpcclient.InferenceServerClient(url=url)
