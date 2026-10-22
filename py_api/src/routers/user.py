import logging
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import ValidationError
from db import get_user, create_user, check_user_exists, update_user, list_users, delete_user
from models.dto import UpdateUserRequest, UserCreateRequest
from models.entity import User
from .depends import get_mongo_client
from pymongo import MongoClient

logger = logging.getLogger("pyapi")


router = APIRouter(prefix="/user", tags=["admin", "users"])

@router.post("/create")
async def create(body: UserCreateRequest, mongo_client: MongoClient = Depends(get_mongo_client)):
    """Create a new user.

    **Input:**
    - `body`: UserCreate — `user_name` (str), `user_email` (str), `games` (list[str])

    **Output:** User object with `id` (str) added.

    **Example:**
    ```json
    POST /api/v1/users
    {"user_name": "John", "user_email": "john@example.com", "games": ["game1"]}
    ```
    """
    logger.info("user_create_start", extra={"email": body.user_email})
    if check_user_exists(body.user_email, mongo_client):
        logger.warning("user_create_duplicate", extra={"email": body.user_email})
        raise HTTPException(409, "Email already exists")
    user = User(user_name=body.user_name, user_email=body.user_email, games=body.games)
    result = create_user(user, mongo_client)
    logger.info("user_create_success", extra={"user_id": result.id})
    return result.model_dump()


@router.get("/list")
async def endpoint_list_users(mongo_client: MongoClient = Depends(get_mongo_client)):
    """List all users.

    **Input:** None.

    **Output:** List of user objects (without `_id`).

    **Example:**
    ```json
    GET /api/v1/users
    [{"id": "64f...", "user_name": "John", "user_email": "john@example.com", "games": ["game1"]}]
    ```
    """
    logger.info("user_list_start")
    try:
        users = [u.model_dump() for u in list_users(mongo_client)]
        logger.info("user_list_success", extra={"count": len(users)})
        return users
    except Exception as e:
        logger.error("user_list_error", extra={"error": str(e)}, exc_info=True)
        raise


@router.get("/get/{id}")
async def endpoint_get_user(id: str, mongo_client: MongoClient = Depends(get_mongo_client)):
    """Get user by id.

    **Input:** `id` (str) — MongoDB ObjectId.

    **Output:** User object or 404.

    **Example:**
    ```json
    GET /api/v1/users/64f123abc456def789012
    {"id": "64f123abc456def789012", "user_name": "John", "user_email": "john@example.com", "games": ["game1"], "agents": ["ua_agent"]}
    ```
    """
    logger.info("user_get_start", extra={"user_id": id})
    try:
        user = get_user(id, mongo_client)
        if not user:
            logger.warning("user_not_found", extra={"user_id": id})
            raise HTTPException(404, "Not found")
        logger.info("user_get_success", extra={"user_id": id})
        return user.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("user_get_error", extra={"user_id": id, "error": str(e)}, exc_info=True)
        raise


@router.patch("/update/{id}")
async def update(id: str, body: UpdateUserRequest, mongo_client: MongoClient = Depends(get_mongo_client)):
    """Update user fields (partial update).

    **Input:**
    - `id` (str) — MongoDB ObjectId
    - `body` (dict) — any subset of `{user_name, user_email, games, agents}`

    **Output:** `{"ok": True}` or 404.

    **Example:**
    ```json
    PATCH /api/v1/users/64f123abc456def789012
    {"user_name": "Jane"}
    ```
    """
    logger.info("user_update_start", extra={"user_id": id})
    try:
        user = update_user(id, body.model_dump(exclude_none=True), mongo_client)
        if not user:
            logger.warning("user_not_found", extra={"user_id": id})
            raise HTTPException(404, "Not found")
        logger.info("user_update_success", extra={"user_id": id})
        return {"ok": True}
    except ValidationError as e:
        logger.error("user_update_validation_error", extra={"user_id": id, "error": str(e)})
        raise HTTPException(status_code=400, detail="")
    except Exception as e:
        logger.error("user_update_error", extra={"user_id": id, "error": str(e)}, exc_info=True)
        raise


@router.delete("/delete/{id}")
async def delete(id: str, mongo_client: MongoClient = Depends(get_mongo_client)):
    """Delete user by id.

    **Input:** `id` (str) — MongoDB ObjectId.

    **Output:** `{"ok": True}` or 404.

    **Example:**
    ```json
    DELETE /api/v1/users/64f123abc456def789012
    {"ok": true}
    ```
    """
    logger.info("user_delete_start", extra={"user_id": id})
    try:
        if not delete_user(id, mongo_client):
            logger.warning("user_not_found", extra={"user_id": id})
            raise HTTPException(404, "Not found")
        logger.info("user_delete_success", extra={"user_id": id})
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("user_delete_error", extra={"user_id": id, "error": str(e)}, exc_info=True)
        raise
