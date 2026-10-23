"""Thread management and chat endpoints for the AI agent."""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.base import CheckpointTuple
from langgraph.graph.state import CompiledStateGraph

from models.dto import ChatRequest, ListThreadsResponse, Message, ThreadDTO
from models.entity import User
from routers.depends import get_ai_agent, get_current_user, get_metadata_from_user
from utils import make_serializable

logger = logging.getLogger("pyapi")

router = APIRouter(prefix="/agent", tags=["agent"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _verify_thread_ownership(
    config: dict[str, Any],
    agent: CompiledStateGraph,
    user: User,
) -> None:
    """Raise ``404``/``403`` when *user* lacks access to *thread*."""
    snapshot = await agent.aget_state(config=config)

    if snapshot.created_at is None:
        logger.warning("thread_not_found", extra={"user_id": user.id})
        raise HTTPException(status_code=404, detail="Thread not found!")

    thread_user_id = snapshot.metadata.get("user_id")
    if thread_user_id != user.id:
        logger.warning("thread_access_denied", extra={"user_id": user.id})
        raise HTTPException(status_code=403, detail="Not authorized")


# ---------------------------------------------------------------------------
# Threads CRUD
# ---------------------------------------------------------------------------

@router.get("/threads", response_model=ListThreadsResponse)
async def list_threads(
    user: User = Depends(get_current_user),
    agent: CompiledStateGraph = Depends(get_ai_agent),
    skip: int = 0,
    limit: int = 50,
):
    """List all threads for the authenticated user, sorted newest first."""
    logger.info("list_threads_start", extra={"user_id": user.id, "skip": skip, "limit": limit})
    try:
        user_id = user.id
        user_checkpoints: list[CheckpointTuple] = list(
            agent.checkpointer.list(config=None, filter={"user_id": user_id})
        )

        # Keep only the latest checkpoint per thread
        thread_latest: dict[str, CheckpointTuple] = {}
        for checkpoint_tuple in user_checkpoints:
            thread_id = checkpoint_tuple.config["configurable"]["thread_id"]
            ts = checkpoint_tuple.checkpoint["ts"]
            if thread_id not in thread_latest or ts > thread_latest[thread_id].checkpoint["ts"]:
                thread_latest[thread_id] = checkpoint_tuple

        # Get unique configs (latest checkpoint per thread)
        user_checkpoints: list[CheckpointTuple] = list(thread_latest.values())
        user_checkpoints.sort(key=lambda x: x.checkpoint["ts"], reverse=True)
        total = len(user_checkpoints)
        items = [
            ThreadDTO(
                thread_id=checkpoint.config["configurable"]["thread_id"],
                thread_name=agent.get_state(config=checkpoint.config).values.get("thread_name"),
                updated_at=checkpoint.checkpoint["ts"]
            )
            for checkpoint in user_checkpoints[skip : skip + limit]
        ]
        logger.info("list_threads_success", extra={"user_id": user_id, "total": total})
        return ListThreadsResponse(total=total, items=items)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("list_threads_error", extra={"user_id": user.id, "error": str(exc)}, exc_info=True)
        raise


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    user: User = Depends(get_current_user),
    agent: CompiledStateGraph = Depends(get_ai_agent),
):
    """Retrieve the full message history for a single thread."""
    logger.info("get_thread_start", extra={"user_id": user.id, "thread_id": thread_id})
    try:
        config = {
            "configurable": {"thread_id": thread_id},
            "metadata": get_metadata_from_user(user),
        }
        await _verify_thread_ownership(config, agent, user)

        snapshot = await agent.aget_state(config=config)
        history = snapshot.values.get("messages", [])
        logger.info("get_thread_success", extra={"user_id": user.id, "thread_id": thread_id, "msg_count": len(history)})
        return history
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_thread_error", extra={"user_id": user.id, "thread_id": thread_id, "error": str(exc)}, exc_info=True)
        raise


@router.patch("/threads/rename/{thread_id}")
async def rename_thread(
    thread_id: str,
    new_name: str,
    user: User = Depends(get_current_user),
    agent: CompiledStateGraph = Depends(get_ai_agent),
):
    """Rename a thread to *new_name*."""
    logger.info("rename_thread_start", extra={"user_id": user.id, "thread_id": thread_id})
    try:
        config = {
            "configurable": {"thread_id": thread_id},
            "metadata": get_metadata_from_user(user),
        }
        await _verify_thread_ownership(config, agent, user)

        agent.update_state(config=config, values={"thread_name": new_name})
        logger.info("rename_thread_success", extra={"user_id": user.id, "thread_id": thread_id})
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("rename_thread_error", extra={"user_id": user.id, "thread_id": thread_id, "error": str(exc)}, exc_info=True)
        raise


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    user: User = Depends(get_current_user),
    agent: CompiledStateGraph = Depends(get_ai_agent),
):
    """Delete a thread.  Returns ``{"ok": True}`` on success."""
    logger.info("delete_thread_start", extra={"user_id": user.id, "thread_id": thread_id})
    try:
        config = {
            "configurable": {"thread_id": thread_id},
            "metadata": get_metadata_from_user(user),
        }
        await _verify_thread_ownership(config, agent, user)

        await agent.checkpointer.adelete_thread(thread_id=thread_id)
        logger.info("delete_thread_success", extra={"user_id": user.id, "thread_id": thread_id})
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("delete_thread_error", extra={"user_id": user.id, "thread_id": thread_id, "error": str(exc)}, exc_info=True)
        raise


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@router.post("/chat")
async def chat(
    request: Request,
    req: ChatRequest,
    user: User = Depends(get_current_user),
    x_growx_mcp_personal_key: str = Header(...),
    agent: CompiledStateGraph = Depends(get_ai_agent),
):
    """Send messages to the AI agent and return its response.

    Supports both streaming (SSE) and non-streaming modes.
    """
    logger.info(
        "chat_start",
        extra={
            "user_name": user.user_name,
            "thread_id": req.thread_id,
            "msg_count": len(req.messages),
            "stream": req.stream,
        },
    )
    try:
        context = agent.context_schema(
            user_id=user.id,
            games=user.games,
            growx_mcp_personal_key=x_growx_mcp_personal_key,
        )
        config = {
            "configurable": {"thread_id": req.thread_id},
            "metadata": get_metadata_from_user(user),
        }
        state_snapshot = await agent.aget_state(config=config)

        if state_snapshot.created_at is not None and user.id != state_snapshot.metadata.get("user_id"):
            logger.warning("thread_access_denied", extra={"user_id": user.id, "thread_id": req.thread_id})
            raise HTTPException(status_code=403, detail="Not authorized to chat in this thread")

        thread_name = (
            req.messages[-1].content
            if state_snapshot.created_at is None
            else state_snapshot.values.get("thread_name")
        )
        input = {
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "thread_name": thread_name,
        }
        if state_snapshot.created_at is not None and state_snapshot.metadata.get("user_id") != user.id:
            logger.warning("chat_access_denied", extra={"user_id": user.id, "thread_id": req.thread_id})
            raise HTTPException(status_code=403, detail="Not authorized to get this thread")

        # --- Stream mode (SSE) ---
        if req.stream:
            async def event_generator():
                events: asyncio.Queue[Any] = asyncio.Queue()
                stream_done = object()
                disconnected = object()

                async def consume_events():
                    try:
                        async for event in agent.astream_events(
                            input,
                            config=config,
                            context=context,
                            version="v2",
                        ):
                            await events.put(event)
                    finally:
                        await events.put(stream_done)

                async def wait_for_disconnect():
                    while not await request.is_disconnected():
                        await asyncio.sleep(1)
                    await events.put(disconnected)

                stream_task = asyncio.create_task(consume_events())
                disconnect_task = asyncio.create_task(wait_for_disconnect())
                try:
                    while True:
                        event = await events.get()
                        if event is disconnected or event is stream_done:
                            break

                        serializable_event = make_serializable(event)
                        yield f"data: {json.dumps(serializable_event)}\n\n"
                except Exception as exc:
                    logger.error(
                        "chat_stream_error",
                        extra={"user_id": user.id, "thread_id": req.thread_id, "error": str(exc)},
                        exc_info=True,
                    )
                    yield f"data: {json.dumps({'error': str(exc)})}\n\n"
                    raise exc
                finally:
                    for task in (stream_task, disconnect_task):
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(
                        stream_task,
                        disconnect_task,
                        return_exceptions=True,
                    )

            logger.info("chat_stream_start", extra={"user_name": user.user_name, "thread_id": req.thread_id})
            return StreamingResponse(event_generator(), media_type="text/event-stream")

        # --- Non-stream mode ---
        response = await agent.ainvoke(input, config=config, context=context)
        logger.info("chat_success", extra={"user_name": user.user_name, "thread_id": req.thread_id})
        return response
    except HTTPException as err:
        logger.warning(
            "chat_http_error",
            extra={"user_id": user.id, "thread_id": req.thread_id, "status_code": err.status_code, "detail": err.detail},
        )
        raise
    except Exception as exc:
        logger.error(
            "chat_crash",
            extra={"user_id": user.id, "thread_id": req.thread_id, "error": str(exc)},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(exc))
