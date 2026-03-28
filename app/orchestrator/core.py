from __future__ import annotations

from typing import Any, Dict, List

from app.intent.router import route_intent


def _as_reply(intent: str, reply: str, extra: dict | None = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"intent": intent, "reply": reply}
    if extra:
        out.update(extra)
    return out


def _memory_store():
    from app.memory.factory import get_memory_store
    return get_memory_store("default")


def _list_facts() -> List[str]:
    try:
        store = _memory_store()
        if hasattr(store, "list_facts"):
            facts = store.list_facts()
            return [str(x).strip() for x in facts if str(x).strip()]
    except Exception:
        pass
    return []


def _remember_fact(fact: str) -> None:
    store = _memory_store()
    if hasattr(store, "remember_fact"):
        store.remember_fact(fact)
        return
    raise RuntimeError("Memory backend does not support remember_fact")


def _forget_by_query(query: str) -> int:
    query = (query or "").strip().lower()
    if not query:
        return 0
    facts = _list_facts()
    removed = 0
    try:
        store = _memory_store()
        for fact in facts:
            if query in fact.lower():
                if hasattr(store, "forget_fact"):
                    store.forget_fact(fact)
                    removed += 1
    except Exception:
        return 0
    return removed


def _recall_home() -> str | None:
    for fact in reversed(_list_facts()):
        low = fact.lower()
        if low.startswith("mieszkam ") or "mieszkam przy" in low or "mój adres" in low or "moj adres" in low:
            return fact
    return None


def _clear_pending_flows() -> None:
    try:
        from app.b2c import tasks as tasks_mod
        for fn_name in ("clear_pending_travel", "clear_pending_transport", "clear_pending_reminder", "clear_pending_checklist"):
            fn = getattr(tasks_mod, fn_name, None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass
    except Exception:
        pass


def _try_handle_memory(message: str) -> Dict[str, Any] | None:
    raw = (message or "").strip()
    low = raw.lower()
    if not raw:
        return None

    if low.startswith("zapamiętaj:") or low.startswith("zapamietaj:"):
        fact = raw.split(":", 1)[1].strip()
        if not fact:
            return _as_reply("memory", "Co mam zapamiętać?")
        _remember_fact(fact)
        _clear_pending_flows()
        return _as_reply("memory_remember", "✅ Zapamiętałem.")

    if low in {"pamięć", "pamiec", "pokaż pamięć", "pokaz pamiec", "co pamiętasz", "co pamietasz"}:
        facts = _list_facts()
        _clear_pending_flows()
        if not facts:
            return _as_reply("memory_list", "Pamięć jest pusta.")
        body = "\n".join(f"{i + 1}. {fact}" for i, fact in enumerate(facts))
        return _as_reply("memory_list", f"Pamiętam:\n{body}")

    if low.startswith("zapomnij:"):
        query = raw.split(":", 1)[1].strip()
        if not query:
            return _as_reply("memory_forget", "Napisz, co mam usunąć z pamięci.")
        removed = _forget_by_query(query)
        _clear_pending_flows()
        if removed:
            return _as_reply("memory_forget", f"✅ Usunięto {removed} wpis(ów).")
        return _as_reply("memory_forget", "Nie znalazłem takiego wpisu w pamięci.")

    if low.startswith("gdzie mieszkam"):
        home = _recall_home()
        _clear_pending_flows()
        if home:
            return _as_reply("memory_recall", home)
        return _as_reply("memory_recall", "Nie mam zapisanego adresu.")

    return None


def handle_chat(message: str, mode: str = "b2c") -> Dict[str, Any]:
    mem = _try_handle_memory(message)
    if mem:
        return mem

    try:
        return route_intent(message, mode=mode)
    except TypeError:
        return route_intent(message, persona=mode)
