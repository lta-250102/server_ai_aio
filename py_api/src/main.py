"""FastAPI application entry point.

Initialises the Triton model pool, MongoDB connection, AI agents and MCP
document loader on startup; shuts them down cleanly on exit.
"""

import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pymongo import MongoClient
from langgraph.graph.state import CompiledStateGraph
from agents import agent_map, init_agent, load_dwh_docs_mcp
from config import (
    LOG_LEVEL,
    MONGO_CONNECTION_STRING,
    TRITON_POOL_SIZE,
)
from routers import agent_router, health_router, user_router, yolo_router
from services import TritonClient
from utils import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """One-time startup and shutdown logic for the application."""
    # -- logging ----------------------------------------------------------------
    setup_logging(os.getenv("LOG_LEVEL", LOG_LEVEL))

    # -- Triton pool ------------------------------------------------------------
    app.state.triton_client = TritonClient(pool_size=TRITON_POOL_SIZE)
    await app.state.triton_client.init()

    # -- MongoDB ----------------------------------------------------------------
    app.state.mongo_client = MongoClient(
        MONGO_CONNECTION_STRING,
        maxPoolSize=50,
        minPoolSize=5,
        maxIdleTimeMS=30000,
    )

    # -- agents & MCP docs ------------------------------------------------------
    await load_dwh_docs_mcp()
    agents: dict[str, CompiledStateGraph] = {}
    for name in agent_map:
        agents[name] = await init_agent(name, app.state.mongo_client)
    app.state.agents = agents

    yield

    # -- shutdown ---------------------------------------------------------------
    await app.state.triton_client.close()
    app.state.mongo_client.close()


app = FastAPI(lifespan=lifespan)
app.include_router(yolo_router)
app.include_router(agent_router)
app.include_router(user_router)
app.include_router(health_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
