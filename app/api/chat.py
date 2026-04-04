from __future__ import annotations

import re
import datetime

from fastapi import APIRouter

from app.schemas import ChatRequest, ChatResponse
from app.orchestrator.core import handle_chat

router = APIRouter(tags=["chat"])

_LAST_CHAT_TASK_ID = None


def _normalize_message(user_text: str) -> tuple[str, str]:
    low = user_text.lower().strip()
    normalized = user_text.strip()

    if low.startswith("muszę "):
        normalized = "dodaj: " + normalized[len("muszę "):].strip()
    elif low.startswith("musze "):
        normalized = "dodaj: " + normalized[len("musze "):].strip()
    elif low.startswith("kupić "):
        normalized = "dodaj: " + normalized[len("kupić "):].strip()
    elif low.startswith("kupic "):
        normalized = "dodaj: " + normalized[len("kupic "):].strip()
    elif low in {
        "lista",
        "pokaż",
        "pokaz",
        "pokaż listę",
        "pokaz liste",
        "pokaż listę zadań",
        "pokaz liste zadan",
    }:
        normalized = "lista"
    elif low in {
        "co mam jutro",
        "co mam na jutro",
        "jakie mam zadania jutro",
        "co jutro",
        "lista na jutro",
        "pokaż jutro",
        "pokaz jutro",
        "pokaż co mam jutro",
        "pokaz co mam jutro",
    }:
        normalized = "lista jutro"

    return low, normalized


@router.post("/chat", response_model=ChatResponse)
@router.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    global _LAST_CHAT_TASK_ID

    user_text = req.message.strip()
    low, normalized = _normalize_message(user_text)

    if _LAST_CHAT_TASK_ID is not None and (
        "zrób to jutro" in low
        or "zrob to jutro" in low
        or "przenieś to na jutro" in low
        or "przenies to na jutro" in low
        or "daj to na jutro" in low
    ):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        out = handle_chat(
            f"ustaw date {_LAST_CHAT_TASK_ID} {tomorrow.isoformat()}",
            mode=req.mode,
        )

    elif _LAST_CHAT_TASK_ID is not None and (
        "usuń ostatnie" in low
        or "usun ostatnie" in low
        or "usuń to ostatnie" in low
        or "usun to ostatnie" in low
        or "usuń ostatni" in low
        or "usun ostatni" in low
        or "usuń ostatnią" in low
        or "usun ostatnią" in low
        or low in {"usuń", "usun"}
    ):
        out = handle_chat(f"usuń {_LAST_CHAT_TASK_ID}", mode=req.mode)

    else:
        out = handle_chat(normalized, mode=req.mode)

    reply = out.get("reply", "") if isinstance(out, dict) else ""

    if isinstance(reply, str):
        m = re.search(r"#(\d+)", reply)
        if m:
            _LAST_CHAT_TASK_ID = int(m.group(1))

    intent = out.get("intent") if isinstance(out, dict) else None
    meta = {k: v for k, v in out.items() if k not in ("reply", "intent")} if isinstance(out, dict) else {}

    return ChatResponse(reply=reply, intent=intent, meta=meta)
