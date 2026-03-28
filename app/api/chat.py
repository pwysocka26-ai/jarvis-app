from __future__ import annotations

import os
import re
import traceback
from typing import Any
from datetime import date as _date, timedelta as _timedelta

from fastapi import APIRouter, Depends, Header, HTTPException

from app.schemas import ChatRequest, ChatResponse
from app.orchestrator.core import handle_chat

# Backwards-compatible alias (older code/tests may import `_auth` from this module).
_auth = None

router = APIRouter(tags=["chat"])

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


@router.post("/chat", response_model=ChatResponse)
@router.post("/v1/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    if DIAG:
        print("\n### HIT /chat ###")
        print("### REQ ### message_head=", _head(req.message, 120), "| mode=", req.mode)

    out = handle_chat(req.message, mode=req.mode)

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
    intent = out.get("intent") if isinstance(out, dict) else None
    meta = {k: v for k, v in out.items() if k not in ("reply", "intent")} if isinstance(out, dict) else {}

    # Add optional structured fields for stable tests/clients
    structured = _build_structured_payload(intent, req.message)
    if structured:
        meta = dict(meta)
        meta.setdefault("structured", structured)

    return ChatResponse(reply=reply, intent=intent, meta=meta)
