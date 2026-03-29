from __future__ import annotations

import re
from typing import Any

PRIORITY_MAP = {
    "wysoki": "p2",
    "ważny": "p2",
    "wazny": "p2",
    "pilny": "p1",
    "niski": "p4",
    "normalny": "p3",
    "średni": "p3",
    "sredni": "p3",
    "p1": "p1",
    "p2": "p2",
    "p3": "p3",
    "p4": "p4",
    "p5": "p5",
}

ADD_PREFIXES = (
    "dodaj zadanie ",
    "dodaj do listy ",
    "dodaj mi ",
    "dodaj ",
    "muszę ",
    "musze ",
    "mam ",
    "pamiętaj ",
    "pamietaj ",
)

SHOPPING_HINTS = (
    "kup ",
    "zakup ",
    "zakupy",
    "lista zakup",
    "sklep",
    "spożywcze",
    "spozywcze",
)

LIST_HINTS = (
    "lista",
    "pokaż listę",
    "pokaz liste",
    "pokaż zadania",
    "pokaz zadania",
    "co mam dziś",
    "co mam dzis",
)

DELETE_HINTS = (
    "usuń",
    "usun",
    "skasuj",
    "wywal",
)

def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())

def _last_task_id_from_history(history: list[dict[str, Any]] | None) -> int | None:
    if not history:
        return None
    for item in reversed(history):
        text = str(item.get("text", "") or "")
        m = re.search(r"#(\d+)", text)
        if m:
            return int(m.group(1))
    return None

def _normalize_add(msg: str) -> str:
    s = _clean(msg)
    low = s.lower()

    for prefix in ADD_PREFIXES:
        if low.startswith(prefix):
            s = s[len(prefix):].strip()
            low = s.lower()
            break

    if low.startswith("kup "):
        s = s[4:].strip()

    return s

def interpret_chat_message(message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    raw = _clean(message)
    if not raw:
        return None

    low = raw.lower()

    # lista
    if any(low == x or low.startswith(x + " ") for x in LIST_HINTS):
        return {
            "action": "list_tasks",
            "normalized": "lista",
        }

    # usuń zadanie / usuń to / usuń ostatnie
    if any(low.startswith(x) for x in DELETE_HINTS):
        m = re.search(r"(?:usuń|usun|skasuj|wywal)\s+(?:zadanie\s+)?(\d+)", low)
        if m:
            task_id = m.group(1)
            return {
                "action": "delete_task",
                "normalized": f"usuń {task_id}",
            }

        if "ostatnie" in low or "to" in low or "poprzednie" in low:
            last_id = _last_task_id_from_history(history)
            if last_id is not None:
                return {
                    "action": "delete_task",
                    "normalized": f"usuń {last_id}",
                }

    # priorytet naturalny
    if "priorytet" in low or "ważne" in low or "wazne" in low or "pilne" in low:
        task_id = None
        m = re.search(r"(?:zadania?|tasku?)\s+#?(\d+)", low)
        if m:
            task_id = m.group(1)
        else:
            m = re.search(r"priorytet\s+(\d+)", low)
            if m:
                task_id = m.group(1)

        if task_id is None and ("to" in low or "ostatnie" in low):
            last_id = _last_task_id_from_history(history)
            if last_id is not None:
                task_id = str(last_id)

        pr = None
        for key, value in PRIORITY_MAP.items():
            if key in low:
                pr = value
                break

        if task_id and pr:
            return {
                "action": "set_priority",
                "normalized": f"priorytet {task_id} {pr}",
            }

    # naturalne dodawanie zadania
    looks_like_task = False

    if any(h in low for h in SHOPPING_HINTS):
        looks_like_task = True

    if any(low.startswith(p) for p in ADD_PREFIXES):
        looks_like_task = True

    if low.startswith("jutro ") or low.startswith("dzis ") or low.startswith("dziś "):
        looks_like_task = True

    if looks_like_task:
        task_text = _normalize_add(raw)
        if task_text:
            return {
                "action": "add_task",
                "normalized": f"dodaj: {task_text}",
            }

    return None
