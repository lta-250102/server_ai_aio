import json
from utils import make_serializable
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from .depends import get_current_user, get_metadata_from_user, get_ai_agent
from langgraph.checkpoint.base import CheckpointTuple
from models.entity import User
from models.dto import ListThreadsResponse, ChatRequest, ThreadDTO
from langgraph.graph.state import CompiledStateGraph
from fastapi.responses import StreamingResponse
import asyncio


router = APIRouter(prefix="/agent", tags=["agent"])


@router.get(path="/threads", response_model=ListThreadsResponse)
async def list_threads(
    user: User = Depends(get_current_user), 
    agent: CompiledStateGraph = Depends(get_ai_agent), 
    skip: int = 0, limit: int = 50, 
) -> ListThreadsResponse:
    """List all threads for a user.

    **Input:**
    - `x-user-id` (str) — Header: MongoDB ObjectId of the user
    - `skip` (int) — Number of threads to skip (default: 0)
    - `limit` (int) — Max threads to return (default: 50)

    **Output:** List of `[thread_id, thread_name]` pairs, sorted by most recent thread first.

    **Example:**
    ```json
    GET /api/v1/threads?skip=0&limit=10
    Headers: x-user-id: abc123
    [["64f123abc456def789012", "Phân tích ROAS campaign A"], ["64f123abc456def789013", "Daily UA report"]]
    ```
    """
    user_id = user.id
    checkpointer = agent.checkpointer
    user_checkpoints: list[CheckpointTuple] = list(checkpointer.list(config=None, filter={"user_id": user_id}))

    # Keep only the latest checkpoint for each thread
    thread_latest = {}
    for a in user_checkpoints:
        thread_id = a.config["configurable"]["thread_id"]
        ts = a.checkpoint["ts"]
        if thread_id not in thread_latest or ts > thread_latest[thread_id].checkpoint["ts"]:
            thread_latest[thread_id] = a

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
    return ListThreadsResponse(total=total, items=items)

@router.get(path="/threads/{id}")
async def get_thread(
    id: str, 
    user: User = Depends(get_current_user), 
    agent: CompiledStateGraph = Depends(get_ai_agent), 
):
    """Get thread history by id.

    **Input:**
    - `id` (str) — MongoDB ObjectId of the thread
    - `x-user-id` (str) — Header: MongoDB ObjectId of the user

    **Output:** List of messages or empty list.

    **Example:**
    ```json
    GET /api/v1/threads/64f123abc456def789012
    Headers: x-user-id: abc123
    [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi!"}]
    ```
    """
    config = {
        "configurable": {"thread_id": id}, 
        "metadata": get_metadata_from_user(user),
    }
    snapshot = await agent.aget_state(config=config)
    if snapshot.created_at is None:
        raise HTTPException(status_code=404, detail="Thread not found!")
    thread_user_id = snapshot.metadata.get("user_id")
    if thread_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to get this thread")
    
    history = snapshot.values.get("messages", [])
    return history

@router.patch(path="/threads/rename/{id}")
async def rename_thread(
    id: str, new_name: str, 
    user: User = Depends(get_current_user),
    agent: CompiledStateGraph = Depends(get_ai_agent), 
):
    """Rename a thread.

    **Input:**
    - `id` (str) — MongoDB ObjectId of the thread
    - `new_name` (str) — New thread name
    - `x-user-id` (str) — Header: MongoDB ObjectId of the user
    """
    # Verify thread belongs to user
    config = {
        "configurable": {"thread_id": id}, 
        "metadata": get_metadata_from_user(user),
    }
    snapshot = await agent.aget_state(config=config)
    if snapshot.created_at is None:
        raise HTTPException(status_code=404, detail="Thread not found!")
    thread_user_id = snapshot.metadata.get("user_id")
    if thread_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to rename this thread")

    agent.update_state(config=config, values={"thread_name": new_name})

@router.delete(path="/threads/{id}")
async def delete_thread(
    id: str, 
    user: User = Depends(get_current_user),
    agent: CompiledStateGraph = Depends(get_ai_agent), 
):
    """Delete thread by id.

    **Input:**
    - `id` (str) — MongoDB ObjectId of the thread
    - `x-user-id` (str) — Header: MongoDB ObjectId of the user

    **Output:** `{"ok": True}` or 404/403

    **Example:**
    ```json
    DELETE /api/v1/threads/64f123abc456def789012
    Headers: x-user-id: abc123
    {"ok": true}
    ```
    """
    # Verify thread belongs to user
    config = {
        "configurable": {"thread_id": id}, 
        "metadata": get_metadata_from_user(user),
    }
    snapshot = await agent.aget_state(config=config)
    if snapshot.created_at is None:
        raise HTTPException(status_code=404, detail="Thread not found!")
    thread_user_id = snapshot.metadata.get("user_id")
    if thread_user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this thread")

    await agent.checkpointer.adelete_thread(thread_id=id)
    return {"ok": True}

     
@router.post("/chat")
async def chat(
    request: Request, req: ChatRequest, 
    user: User = Depends(get_current_user), 
    x_growx_mcp_personal_key: str = Header(...),
    agent: CompiledStateGraph = Depends(get_ai_agent), 
):
    """Chat with UA agent. Sends messages and returns AI response.

    **Input:**
    - `x-user-id` (str) — Header: MongoDB ObjectId of the user
    - `body`: ChatRequest — `thread_id` (str), `messages` (list[Message]), `stream` (bool)

    **Output:** Agent response (dict) or SSE stream if `stream=true`.

    **Example:**
    ```json
    POST /api/v1/chat
    Headers: x-user-id: 64f123abc456def789012
    {"thread_id": "xyz789", "messages": [{"role": "user", "content": "Phân tích ROAS campaign A"}], "stream": false}
    ```
    """
    try:
        context = agent.context_schema(user_id=user.id, games=user.games, growx_mcp_personal_key=x_growx_mcp_personal_key)
        config = {
            "configurable": {"thread_id": req.thread_id}, 
            "metadata": get_metadata_from_user(user),
        }
        state_snapshot = agent.get_state(config=config)
        thread_name = req.messages[-1].content if state_snapshot.created_at is None else state_snapshot.values.get("thread_name")
        input = {"messages": [{"role": m.role, "content": m.content} for m in req.messages], "thread_name": thread_name}

        if state_snapshot.created_at is not None and state_snapshot.metadata.get("user_id") != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to get this thread")
            
        # --- Stream mode (Streamable HTTP) ---
        if req.stream:
            async def event_generator():
                events = asyncio.Queue()
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
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
                    raise e
                finally:
                    for task in (stream_task, disconnect_task):
                        if not task.done():
                            task.cancel()
                    await asyncio.gather(
                        stream_task,
                        disconnect_task,
                        return_exceptions=True,
                    )

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        # --- Non-stream mode ---
        response = await agent.ainvoke(input, config=config, context=context)
        return response
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
