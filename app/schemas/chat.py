from typing import Any
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    mode: str = "chat"
    history: list[dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    intent: str | None = None
    meta: dict[str, Any] = {}
