from __future__ import annotations

import datetime
from typing import Any, Optional

from fastapi import APIRouter

from app.schemas import ChatRequest, ChatResponse
from app.orchestrator.core import handle_chat

router = APIRouter(tags=["chat"])

# MVP state - global, not per-user.
# This keeps behavior deterministic for the single-user flow described in the project notes.
_LAST_CHAT_TASK_ID: Optional[int] = None

_MOVE_TO_TOMORROW_HINTS = (
    "zrób to jutro",
    "zrob to jutro",
    "przenieś to na jutro",
    "przenies to na jutro",
    "daj to na jutro",
)

_DELETE_LAST_HINTS = (
    "usuń ostatnie",
    "usun ostatnie",
    "usuń to ostatnie",
    "usun to ostatnie",
    "usuń ostatni",
    "usun ostatni",
    "usuń ostatnią",
    "usun ostatnią",
)


def _normalize_message(user_text: str) -> tuple[str, str]:
    low = (user_text or "").lower().strip()
    normalized = (user_text or "").strip()

    if low.startswith("muszę "):
        normalized = "dodaj: " + normalized[len("muszę ") :].strip()
    elif low.startswith("musze "):
        normalized = "dodaj: " + normalized[len("musze ") :].strip()
    elif low.startswith("kupić "):
        normalized = "dodaj: " + normalized[len("kupić ") :].strip()
    elif low.startswith("kupic "):
        normalized = "dodaj: " + normalized[len("kupic ") :].strip()
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


def _looks_like_add_command(normalized: str) -> bool:
    return (normalized or "").strip().lower().startswith("dodaj:")


def _latest_task_id_from_store() -> Optional[int]:
    """Return the newest task id using created_at as the source of truth."""
    try:
        from app.b2c import tasks as tasks_mod

        tasks = tasks_mod.load_tasks()
        if not isinstance(tasks, list):
            return None

        best_id: Optional[int] = None
        best_dt: Optional[datetime.datetime] = None

        for task in tasks:
            if not isinstance(task, dict):
                continue
            task_id = task.get("id")
            created_at = task.get("created_at")
            if task_id is None or not created_at:
                continue
            try:
                created_dt = datetime.datetime.fromisoformat(str(created_at))
                task_id_int = int(task_id)
            except Exception:
                continue
            if best_dt is None or created_dt > best_dt:
                best_dt = created_dt
                best_id = task_id_int

        return best_id
    except Exception:
        return None


def _move_task_to_tomorrow(task_id: int) -> dict[str, Any]:
    from app.b2c import tasks as tasks_mod

    task = tasks_mod.get_task(int(task_id))
    if not task:
        return {
            "intent": "move_to_tomorrow",
            "reply": "Nie widzę ostatniego zadania (brak w bazie). Dodaj zadanie ponownie.",
            "ok": False,
        }

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    old_due_at = str(task.get("due_at") or "").strip()

    new_due_at = tomorrow.isoformat()
    if "T" in old_due_at:
        time_part = old_due_at.split("T", 1)[1]
        new_due_at = f"{new_due_at}T{time_part}"

    updated = tasks_mod.update_task(int(task_id), due_at=new_due_at)
    title = str((updated or task).get("title") or "(bez tytułu)")

    return {
        "intent": "move_to_tomorrow",
        "reply": f"✅ Przeniosłem na jutro: {title}",
        "ok": True,
        "task_id": int(task_id),
        "due_at": new_due_at,
    }


def _delete_task_by_id(task_id: int) -> dict[str, Any]:
    from app.b2c import tasks as tasks_mod

    result = tasks_mod.delete_task_by_id(int(task_id))
    if isinstance(result, dict):
        out = {"intent": "delete_last_task", "task_id": int(task_id)}
        out.update(result)
        return out

    return {
        "intent": "delete_last_task",
        "task_id": int(task_id),
        "ok": bool(result),
        "reply": "OK" if result else "Nie udało się usunąć zadania.",
    }


@router.post("/chat", response_model=ChatResponse)
@router.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    global _LAST_CHAT_TASK_ID

    user_text = (req.message or "").strip()
    low, normalized = _normalize_message(user_text)

    if _LAST_CHAT_TASK_ID is not None and any(hint in low for hint in _MOVE_TO_TOMORROW_HINTS):
        out = _move_task_to_tomorrow(_LAST_CHAT_TASK_ID)

    elif _LAST_CHAT_TASK_ID is not None and (
        any(hint in low for hint in _DELETE_LAST_HINTS) or low in {"usuń", "usun"}
    ):
        out = _delete_task_by_id(_LAST_CHAT_TASK_ID)
        if isinstance(out, dict) and out.get("ok"):
            _LAST_CHAT_TASK_ID = None

    else:
        out = handle_chat(normalized, mode=getattr(req, "mode", None))

        if (
            isinstance(out, dict)
            and out.get("intent") == "add_task"
            and _looks_like_add_command(normalized)
        ):
            latest = _latest_task_id_from_store()
            if latest is not None:
                _LAST_CHAT_TASK_ID = latest

    reply = out.get("reply", "") if isinstance(out, dict) else ""
    intent = out.get("intent") if isinstance(out, dict) else None
    meta = (
        {key: value for key, value in out.items() if key not in ("reply", "intent")}
        if isinstance(out, dict)
        else {}
    )

    return ChatResponse(reply=str(reply or ""), intent=intent, meta=meta)
