from fastapi import FastAPI
import uvicorn
from routers import yolo_router
from contextlib import asynccontextmanager
from services import TritonClient
import os


TRITON_POOL_SIZE = int(os.environ.get("TRITON_POOL_SIZE", "8"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.triton_client = TritonClient(pool_size=TRITON_POOL_SIZE)
    await app.state.triton_client.init()
    yield
    await app.state.triton_client.close()


app = FastAPI(lifespan=lifespan)
app.include_router(yolo_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")