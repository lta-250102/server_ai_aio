import random
import tritonclient.grpc.aio as grpcclient
import os
from functools import lru_cache


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

    def get_client(self) -> grpcclient.InferenceServerClient:
        """
        Lấy ngẫu nhiên 1 client từ Pool (KHÔNG LOCK, KHÔNG WAIT).
        Hàng trăm request có thể lấy CÙNG 1 CLIENT này để gọi async_infer song song (Multiplexing).
        """
        return random.choice(self._clients)

    async def close(self):
        """Đóng toàn bộ các kết nối khi shutdown app."""
        for client in self._clients:
            await client.close()


@lru_cache(maxsize=1)
def get_triton_client(url: str = f"{TRITON_HOST}:8001"):
    return grpcclient.InferenceServerClient(url=url)