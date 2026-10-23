"""User management endpoints.

All handlers delegate to :mod:`db.user` for persistence so that this
module stays focused on HTTP concerns (request validation, status codes).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from pymongo import MongoClient

from config import MONGO_DB_NAME
from db import get_user, create_user, check_user_exists, update_user, list_users, delete_user
from models.dto import UpdateUserRequest, UserCreateRequest
from models.entity import User
from routers.depends import get_mongo_client

logger = logging.getLogger("pyapi")

router = APIRouter(prefix="/user", tags=["admin", "users"])


@router.post("/create")
async def create_user_endpoint(
    body: UserCreateRequest,
    mongo_client: MongoClient = Depends(get_mongo_client),
) -> dict:
    """Create a new user.  Returns 409 if *user_email* already exists."""
    logger.info("user_create_start", extra={"email": body.user_email})
    users_collection = mongo_client[MONGO_DB_NAME]["users"]
    if check_user_exists(body.user_email, users_collection):
        logger.warning("user_create_duplicate", extra={"email": body.user_email})
        raise HTTPException(status_code=409, detail="Email already exists")
    user = User(
        user_name=body.user_name,
        user_email=body.user_email,
        games=body.games,
    )
    result = create_user(user, users_collection)
    logger.info("user_create_success", extra={"user_id": result.id})
    return result.model_dump()


@router.get("/list")
async def list_users_endpoint(
    mongo_client: MongoClient = Depends(get_mongo_client),
) -> list[dict]:
    """List all users."""
    logger.info("user_list_start")
    try:
        users_collection = mongo_client[MONGO_DB_NAME]["users"]
        users = [u.model_dump() for u in list_users(users_collection)]
        logger.info("user_list_success", extra={"count": len(users)})
        return users
    except Exception as exc:
        logger.error("user_list_error", extra={"error": str(exc)}, exc_info=True)
        raise


@router.get("/get/{user_id}")
async def get_user_endpoint(
    user_id: str,
    mongo_client: MongoClient = Depends(get_mongo_client),
) -> dict:
    """Get a user by ID.  Returns 404 when not found."""
    logger.info("user_get_start", extra={"user_id": user_id})
    try:
        users_collection = mongo_client[MONGO_DB_NAME]["users"]
        user = get_user(user_id, users_collection)
        if not user:
            logger.warning("user_not_found", extra={"user_id": user_id})
            raise HTTPException(status_code=404, detail="Not found")
        logger.info("user_get_success", extra={"user_id": user_id})
        return user.model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("user_get_error", extra={"user_id": user_id, "error": str(exc)}, exc_info=True)
        raise


@router.patch("/update/{user_id}")
async def update_user_endpoint(
    user_id: str,
    body: UpdateUserRequest,
    mongo_client: MongoClient = Depends(get_mongo_client),
) -> dict:
    """Partial-update a user.  Returns 404 when not found."""
    logger.info("user_update_start", extra={"user_id": user_id})
    try:
        users_collection = mongo_client[MONGO_DB_NAME]["users"]
        user = update_user(
            user_id,
            body.model_dump(exclude_none=True),
            users_collection,
        )
        if not user:
            logger.warning("user_not_found", extra={"user_id": user_id})
            raise HTTPException(status_code=404, detail="Not found")
        logger.info("user_update_success", extra={"user_id": user_id})
        return {"ok": True}
    except ValidationError as exc:
        logger.error("user_update_validation_error", extra={"user_id": user_id, "error": str(exc)})
        raise HTTPException(status_code=400, detail="")
    except Exception as exc:
        logger.error("user_update_error", extra={"user_id": user_id, "error": str(exc)}, exc_info=True)
        raise


@router.delete("/delete/{user_id}")
async def delete_user_endpoint(
    user_id: str,
    mongo_client: MongoClient = Depends(get_mongo_client),
) -> dict:
    """Delete a user by ID.  Returns 404 when not found."""
    logger.info("user_delete_start", extra={"user_id": user_id})
    try:
        users_collection = mongo_client[MONGO_DB_NAME]["users"]
        if not delete_user(user_id, users_collection):
            logger.warning("user_not_found", extra={"user_id": user_id})
            raise HTTPException(status_code=404, detail="Not found")
        logger.info("user_delete_success", extra={"user_id": user_id})
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("user_delete_error", extra={"user_id": user_id, "error": str(exc)}, exc_info=True)
        raise
