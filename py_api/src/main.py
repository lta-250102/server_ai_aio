from fastapi import FastAPI
import uvicorn
from routers import yolo_router, agent_router, user_router, health_router
from contextlib import asynccontextmanager
from services import TritonClient
from agents import init_agent, agent_map, set_ch_client
from clickhouse_driver import Client as ChClient
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
    # ClickHouse pool — shared global instance, thread-safe
    ch_url = (
        f"clickhouse://bytehouse:{os.getenv('BYTEHOUSE_KEY')}@gateway.aws-us-east-1.bytehouse.cloud:19000/"
        f"?secure=true&max_execution_time=60"
        f"&use_query_pool=true&pool_size=10&pool_timeout=5"
    )
    ch_client = ChClient.from_url(ch_url)
    app.state.ch_client = ch_client
    set_ch_client(ch_client)
    # Pre-warm agents during startup (blocking I/O moved out of request path)
    app.state.agents = {}
    for name in agent_map:
        app.state.agents[name] = await init_agent(name, app.state.mongo_client)
    yield
    app.state.ch_client.disconnect()
    await app.state.triton_client.close()
    app.state.mongo_client.close()


app = FastAPI(lifespan=lifespan)
app.include_router(yolo_router)
app.include_router(agent_router)
app.include_router(user_router)
app.include_router(health_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")