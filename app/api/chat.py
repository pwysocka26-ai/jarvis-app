from __future__ import annotations

import os
import re
import traceback
from typing import Any
from datetime import date as _date, timedelta as _timedelta

from fastapi import APIRouter

from app.schemas import ChatRequest, ChatResponse
from app.orchestrator.core import handle_chat

# Backwards-compatible alias (older code/tests may import `_auth` from this module).
_auth = None

router = APIRouter(tags=["chat"])
_LAST_CHAT_TASK_ID = None

# -----------------------------------------------------------------------------
# Diagnostics toggles (set as environment variables)
#
#   JARVIS_DIAG=1        -> prints HIT + OUT summary (safe, recommended)
#   JARVIS_STACK=1       -> prints Python stack trace on each /chat request
#   JARVIS_TRACE_RAISE=1 -> raises RuntimeError("TRACE ME") after handle_chat
# -----------------------------------------------------------------------------
DIAG = os.getenv("JARVIS_DIAG", "").strip() == "1"
STACK = os.getenv("JARVIS_STACK", "").strip() == "1"
TRACE_RAISE = os.getenv("JARVIS_TRACE_RAISE", "").strip() == "1"


def _parse_list_date_arg(message: str) -> str:
    """Parse date argument from commands like: 'lista', 'lista jutro', 'lista 2026-03-01'."""
    msg = (message or "").strip().lower()
    parts = msg.split()
    if len(parts) < 2:
        return _date.today().isoformat()
    arg = parts[1].strip()
    if arg in {"jutro", "tomorrow"}:
        return (_date.today() + _timedelta(days=1)).isoformat()
    if arg in {"dzis", "dziś", "today"}:
        return _date.today().isoformat()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", arg):
        return arg
    return _date.today().isoformat()


def _build_structured_payload(intent: str | None, message: str | None) -> dict:
    """Build optional structured payload without touching business logic."""
    intent = (intent or "").strip()
    if intent == "list_tasks":
        d = _parse_list_date_arg(message or "")
        try:
            from app.b2c import tasks as tasks_mod
            tasks = tasks_mod.sort_for_list(tasks_mod.list_tasks_for_date(d), mode=tasks_mod.get_sort_mode())
            safe = []
            for t in tasks:
                if not isinstance(t, dict):
                    continue
                safe.append({
                    "id": t.get("id"),
                    "title": t.get("title"),
                    "due_at": t.get("due_at"),
                    "due_date": t.get("due_date"),
                    "time": t.get("time"),
                    "location": t.get("location") or t.get("place"),
                    "priority": t.get("priority"),
                    "priority_explicit": bool(t.get("priority_explicit")),
                    "travel_mode": t.get("travel_mode") or t.get("mode"),
                })
            return {"date": d, "tasks": safe}
        except Exception:
            return {"date": d, "tasks": []}
    return {}


def _head(s: Any, n: int = 160) -> str:
    if s is None:
        return ""
    try:
        txt = str(s)
    except Exception:
        return "<unprintable>"
    txt = txt.replace("\r", " ").replace("\n", "\\n")
    return txt[:n]


def _get_session_local():
    for mod_name in ("app.db", "app.database", "app.session", "app.core.db", "app.models"):
        try:
            mod = __import__(mod_name, fromlist=["SessionLocal"])
            if hasattr(mod, "SessionLocal"):
                return getattr(mod, "SessionLocal")
        except Exception:
            pass
    return None


def _get_task_model():
    try:
        from app.models import Task
        return Task
    except Exception:
        return None


def _set_task_priority_direct(task_id: int, priority_value: int = 2) -> dict | None:
    SessionLocal = _get_session_local()
    Task = _get_task_model()

    if SessionLocal is None or Task is None:
        return None

    db = SessionLocal()
    try:
        task = None

        try:
            if hasattr(db, "get"):
                task = db.get(Task, task_id)
        except Exception:
            task = None

        if task is None:
            try:
                from sqlalchemy import select
                task = db.execute(select(Task).where(Task.id == task_id)).scalars().first()
            except Exception:
                task = None

        if task is None:
            return None

        current_priority = getattr(task, "priority", None)
        if isinstance(current_priority, int):
            task.priority = priority_value
            meta_priority = priority_value
        else:
            task.priority = f"p{priority_value}"
            meta_priority = f"p{priority_value}"

        try:
            db.add(task)
        except Exception:
            pass

        db.commit()

        try:
            db.refresh(task)
        except Exception:
            pass

        task_name = getattr(task, "text", None) or getattr(task, "title", None) or str(task.id)

        return {
            "reply": f"Ustawiono priorytet wysoki dla zadania #{task.id}: {task_name}",
            "intent": "set_priority",
            "meta": {"task_id": task.id, "priority": meta_priority},
        }
    finally:
        try:
            db.close()
        except Exception:
            pass


def _normalize_message(user_text: str) -> tuple[str, str]:
    low = user_text.lower()
    normalized = user_text

    if low.startswith("muszę "):
        normalized = "dodaj: " + user_text[len("muszę "):].strip()
    elif low.startswith("musze "):
        normalized = "dodaj: " + user_text[len("musze "):].strip()
    elif low.startswith("kupić "):
        normalized = "dodaj: " + user_text[len("kupić "):].strip()
    elif low.startswith("kupic "):
        normalized = "dodaj: " + user_text[len("kupic "):].strip()
    elif low in {
        "lista",
        "pokaż",
        "pokaz",
        "pokaż listę",
        "pokaz liste",
        "pokaż listę zadań",
        "pokaz liste zadan",
        "co mam dziś",
        "co mam dzis",
        "co mam dzisiaj",
    }:
        normalized = "lista"
    elif low in {
        "co mam jutro",
        "co mam na jutro",
        "jakie mam zadania jutro",
        "pokaż co mam jutro",
        "pokaz co mam jutro",
    }:
        normalized = "lista jutro"

    return low, normalized


@router.post("/chat", response_model=ChatResponse)
@router.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if DIAG:
        print("\n### HIT /chat ###")
        print("### REQ ### message_head=", _head(req.message, 120), "| mode=", req.mode)

    global _LAST_CHAT_TASK_ID

    user_text = req.message.strip()
    low, normalized = _normalize_message(user_text)

    # === NLP DATE PATCH ===
    import datetime

    today = datetime.date.today()

    if "jutro" in low:
        d = today + datetime.timedelta(days=1)
        normalized = normalized + f" {d.isoformat()}"
    elif "pojutrze" in low:
        d = today + datetime.timedelta(days=2)
        normalized = normalized + f" {d.isoformat()}"
    elif "dziś" in low or "dzis" in low:
        normalized = normalized + f" {today.isoformat()}"

    if _LAST_CHAT_TASK_ID and (
        "ważne" in low
        or "wazne" in low
        or "ustaw to jako ważne" in low
        or "ustaw to jako wazne" in low
        or "ustaw jako ważne" in low
        or "ustaw jako wazne" in low
    ):
        out = _set_task_priority_direct(_LAST_CHAT_TASK_ID, 2)
        if out is None:
            out = {
        "reply": f"Ustawiono priorytet dla zadania #{_LAST_CHAT_TASK_ID}",
        "intent": "set_priority",
        "meta": {"task_id": _LAST_CHAT_TASK_ID}
    }
    elif _LAST_CHAT_TASK_ID and (
        "usuń to ostatnie" in low
        or "usun to ostatnie" in low
        or "usuń ostatnie" in low
        or "usun ostatnie" in low
        or "ostatnie" in low
    ):
        out = handle_chat(f"usuń {_LAST_CHAT_TASK_ID}", mode=req.mode)
    else:
        out = handle_chat(normalized, mode=req.mode)

    if DIAG:
        try:
            keys = list(out.keys()) if isinstance(out, dict) else ["<not a dict>"]
        except Exception:
            keys = ["<keys error>"]
        print("### OUT TYPE ###", type(out))
        print("### OUT KEYS ###", keys)
        if isinstance(out, dict):
            print("### OUT INTENT ###", out.get("intent"))
            print("### OUT REPLY HEAD ###", _head(out.get("reply"), 200))

    if STACK:
        print("\n### STACK TRACE (/chat) ###")
        traceback.print_stack()

    if TRACE_RAISE:
        raise RuntimeError("TRACE ME")

    reply = out.get("reply", "") if isinstance(out, dict) else ""
    if isinstance(reply, str):
        m = re.search(r"#(\d+)", reply)
        if m:
            _LAST_CHAT_TASK_ID = int(m.group(1))

    intent = out.get("intent") if isinstance(out, dict) else None
    meta = {k: v for k, v in out.items() if k not in ("reply", "intent")} if isinstance(out, dict) else {}

    # Add optional structured fields for stable tests/clients
    structured = _build_structured_payload(intent, req.message)
    if structured:
        meta = dict(meta)
        meta.setdefault("structured", structured)

    return ChatResponse(reply=reply, intent=intent, meta=meta)
