from fastapi import HTTPException

from .domain import Game
from pydantic import BaseModel, ConfigDict, Field


class UpdateUserRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    user_name: str | None = None
    user_email: str | None = None
    games: list[Game] | None = None

class UserCreateRequest(BaseModel):
    user_name: str
    user_email: str
    games: list[Game] = []

class ThreadDTO(BaseModel):
    thread_id: str
    thread_name: str | None
    updated_at: str # "2026-09-18T10:00:00Z"

class ListThreadsResponse(BaseModel):
    total: int
    items: list[ThreadDTO]

class Message(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str

class ChatRequest(BaseModel):
    thread_id: str
    messages: list[Message]
    stream: bool = False

    def validate(self):
        if not self.messages or len(self.messages) == 0:
            raise HTTPException(status_code=400, detail="No messages provided")
        for message in self.messages:
            if message.role not in ["user", "assistant", "system"]:
                raise HTTPException(status_code=400, detail="invalid role")