from .domain import Game
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class UpdateUserRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    user_name: str | None = Field(None, min_length=1, max_length=100)
    user_email: str | None = Field(None, max_length=255)
    games: list[Game] | None = None

    @field_validator("user_email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v

class UserCreateRequest(BaseModel):
    user_name: str = Field(..., min_length=1, max_length=100)
    user_email: str = Field(..., max_length=255)
    games: list[Game] = []

    @field_validator("user_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v

class ThreadDTO(BaseModel):
    thread_id: str = Field(..., min_length=1)
    thread_name: str | None = Field(None, max_length=200)
    updated_at: str  # "2026-09-18T10:00:00Z"

class ListThreadsResponse(BaseModel):
    total: int
    items: list[ThreadDTO]

class Message(BaseModel):
    role: str
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("user", "assistant", "system"):
            raise ValueError("role must be 'user', 'assistant', or 'system'")
        return v

class ChatRequest(BaseModel):
    thread_id: str = Field(..., min_length=1)
    messages: list[Message]
    stream: bool = False

    @model_validator(mode="after")
    def validate_messages(self) -> "ChatRequest":
        if not self.messages:
            raise ValueError("No messages provided")
        return self
