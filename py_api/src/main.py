from fastapi import FastAPI
import uvicorn
from routers import yolo_router, agent_router, user_router
from contextlib import asynccontextmanager
from services import TritonClient
from pymongo import MongoClient
import os


TRITON_POOL_SIZE = int(os.environ.get("TRITON_POOL_SIZE", "8"))
MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING", "mongodb://localhost:27017/")

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.triton_client = TritonClient(pool_size=TRITON_POOL_SIZE)
    await app.state.triton_client.init()
    app.state.mongo_client = MongoClient(
        MONGO_CONNECTION_STRING,
        maxPoolSize=50,
        minPoolSize=5,
        maxIdleTimeMS=30000,
    )
    yield
    await app.state.triton_client.close()
    app.state.mongo_client.close()


app = FastAPI(lifespan=lifespan)
app.include_router(yolo_router)
app.include_router(agent_router)
app.include_router(user_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")