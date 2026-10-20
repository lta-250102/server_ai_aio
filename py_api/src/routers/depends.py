from fastapi import Request
from services import get_triton_client as get_cached_triton_client


async def get_triton_client(request: Request):
    """
    Dependency lấy pool từ app.state, mượn 1 client và tự động trả lại
    sau khi endpoint xử lý xong request.
    """
    # return request.app.state.triton_client.get_client()
    return get_cached_triton_client()