from typing import Any
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    mode: str = "chat"


class ChatResponse(BaseModel):
    reply: str
    intent: str | None = None
    meta: dict[str, Any] = {}
