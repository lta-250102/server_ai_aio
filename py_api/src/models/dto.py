"""Data-transfer objects for the public API.

Request/response schemas are defined here; persistent entities live in
``models.entity`` and domain types in ``models.domain``.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from models.domain import Game


class UpdateUserRequest(BaseModel):
    """Partial-update payload for a user resource."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    user_name: str | None = Field(None, min_length=1, max_length=100)
    user_email: str | None = Field(None, max_length=255)
    games: list[Game] | None = None

    @field_validator("user_email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Invalid email format")
        return value


class UserCreateRequest(BaseModel):
    """Full-create payload for a user resource."""

    user_name: str = Field(..., min_length=1, max_length=100)
    user_email: str = Field(..., max_length=255)
    games: list[Game] = []

    @field_validator("user_email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Invalid email format")
        return value


class ThreadDTO(BaseModel):
    """Compact representation of a conversation thread."""

    thread_id: str = Field(..., min_length=1)
    thread_name: str | None = Field(None, max_length=200)
    updated_at: str  # "2026-09-18T10:00:00Z"


class ListThreadsResponse(BaseModel):
    """Paginated list of threads."""

    total: int
    items: list[ThreadDTO]


class Message(BaseModel):
    """A single chat message."""

    role: str
    content: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ("user", "assistant", "system"):
            raise ValueError("role must be 'user', 'assistant', or 'system'")
        return value


class ChatRequest(BaseModel):
    """Incoming chat request payload."""

    thread_id: str = Field(..., min_length=1)
    messages: list[Message]
    stream: bool = False

    @model_validator(mode="after")
    def validate_messages(self) -> "ChatRequest":
        if not self.messages:
            raise ValueError("No messages provided")
        return self
