import logging
from fastapi import Depends, HTTPException, Header, Request
from services import get_triton_client as get_cached_triton_client
import tritonclient.grpc.aio as grpcclient
from pymongo import MongoClient
from models.entity import User
from db import get_user
from langgraph.graph.state import CompiledStateGraph

logger = logging.getLogger("pyapi")


async def get_triton_client(request: Request) -> grpcclient.InferenceServerClient:
    """
    Dependency lấy pool từ app.state, mượn 1 client và tự động trả lại
    sau khi endpoint xử lý xong request.
    """
    return request.app.state.triton_client.get_client() # pool
    # return get_cached_triton_client() # singleton

async def get_mongo_client(request: Request) -> MongoClient:
    return request.app.state.mongo_client

async def get_current_user(x_user_id: str = Header(...), mongo_client: MongoClient = Depends(get_mongo_client)) -> User:
    """FastAPI dependency: validate user_id from header and return user."""
    user = get_user(x_user_id, mongo_client)
    if not user:
        logger.warning("user_auth_failed", extra={"user_id": x_user_id})
        raise HTTPException(status_code=401, detail="Invalid or missing user_id")
    return user

def get_metadata_from_user(user: User) -> dict:
    return {
        "user_id": user.id, 
        "user_name": user.user_name, 
        "user_email": user.user_email, 
        "n_games": len(user.games)
    }

async def get_ai_agent(x_agent_name: str = Header(...), request: Request = ...) -> CompiledStateGraph:
    if x_agent_name not in request.app.state.agents:
        logger.warning("agent_not_found", extra={"agent_name": x_agent_name})
        raise HTTPException(status_code=400, detail=f"Unknown agent: {x_agent_name}")
    return request.app.state.agents[x_agent_name]
