"""Router dependencies.

Centralises all ``Depends``-based FastAPI dependencies so that router
handler functions stay focused on HTTP concerns.
"""

import logging

import tritonclient.grpc.aio as grpcclient
from fastapi import Depends, Header, HTTPException, Request
from pymongo import MongoClient
from langgraph.graph.state import CompiledStateGraph

from config import MONGO_DB_NAME
from db import get_user
from models.entity import User
from services import get_triton_client as get_cached_triton_client

logger = logging.getLogger("pyapi")


async def get_triton_client(request: Request) -> grpcclient.InferenceServerClient:
    """Obtain a Triton gRPC client from the application pool.

    borrows one client from ``app.state.triton_client`` and automatically
    returns it to the pool after the endpoint finishes processing.
    """
    return request.app.state.triton_client.get_client() # pool
    # return get_cached_triton_client() # singleton

async def get_mongo_client(request: Request):
    """Return the shared MongoDB client."""
    return request.app.state.mongo_client


async def get_current_user(
    x_user_id: str = Header(...),
    mongo_client: MongoClient = Depends(get_mongo_client),
) -> User:
    """Validate ``user_id`` from the request header and return the user.

    Raises ``401`` when the user does not exist.
    """
    users_collection = mongo_client[MONGO_DB_NAME]["users"]
    user = get_user(x_user_id, users_collection)
    if not user:
        logger.warning("user_auth_failed", extra={"user_id": x_user_id})
        raise HTTPException(status_code=401, detail="Invalid or missing user_id")
    return user


def get_metadata_from_user(user: User) -> dict:
    """Build a metadata dict from a :class:`~models.entity.User`."""
    return {
        "user_id": user.id,
        "user_name": user.user_name,
        "user_email": user.user_email,
        "n_games": len(user.games),
    }


async def get_ai_agent(
    x_agent_name: str = Header(...),
    request: Request = ...,
) -> CompiledStateGraph:
    """Return the agent identified by the ``x-agent-name`` header."""
    if x_agent_name not in request.app.state.agents:
        logger.warning("agent_not_found", extra={"agent_name": x_agent_name})
        raise HTTPException(status_code=400, detail=f"Unknown agent: {x_agent_name}")
    return request.app.state.agents[x_agent_name]
