# ROUTER_BUILD: late_pred_A_buf10
from __future__ import annotations

from typing import Any, Dict, Optional, List, Tuple
import os
import re
import math
from datetime import date, datetime, timedelta

from app.b2c import tasks as tasks_mod
from app.b2c.travel_mode import morning_brief
from app.b2c.maps_google import get_eta_minutes


# Travel configuration (MVP)
TRAVEL_BUFFER_MIN = 10  # safety buffer (minutes)

YES = {"tak", "t", "yes", "y", "ok", "jasne", "pewnie"}
NO = {"nie", "n", "no"}


def _clean_title_for_display(title: str) -> str:
    """Make task titles user-friendly (defensive cleanup)."""
    t = (title or "").strip()
    # strip accidental command prefixes that might leak into title
    t = re.sub(r"^\s*[-•]*\s*(dodaj|add)\s*:?\s*", "", t, flags=re.IGNORECASE)
    return t.strip()

# Wersja A: emoji (działa wszędzie)
PRIORITY_EMOJI = {
    1: "🔴",  # p1
    2: "🟠",  # p2
    3: "🟢",  # p3
}


def _task_time_str(t: Dict[str, Any]) -> str:
    """Return HH:MM if task has a concrete due time."""
    v = t.get("time")
    if isinstance(v, str) and v.strip():
        return v.strip()
    due_at = t.get("due_at")
    if isinstance(due_at, str) and "T" in due_at and len(due_at) >= 16:
        return due_at.split("T", 1)[1][:5]
    return ""

SORT_PRIORITY = "priority"
SORT_TIME = "time"

ORIGIN_HOME = "dom"
ORIGIN_WORK = "praca"
ORIGIN_CURRENT = "tu"
ORIGIN_CUSTOM = "custom"


def _as_reply(intent: str, reply: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out = {"intent": intent, "reply": reply, "response": reply}
    if extra:
        out.update(extra)
    return out


def _reply_from_any(out: Any, default: str = "OK") -> str:
    if isinstance(out, dict):
        return str(out.get("reply") or out.get("response") or default)
    if out is True:
        return default
    if out is False or out is None:
        return "Nie udało się."
    return str(out)


# -----------------------------
# Tasks DB settings (persisted)
# -----------------------------
def _load_db() -> Dict[str, Any]:
    # Prefer new API if present
    if hasattr(tasks_mod, "load_tasks_db"):
        return tasks_mod.load_tasks_db()  # type: ignore[attr-defined]
    # Fallback: try older storage
    if hasattr(tasks_mod, "load_tasks"):
        return {"tasks": tasks_mod.load_tasks()}  # type: ignore[attr-defined]
    return {}


def _save_db(db: Dict[str, Any]) -> bool:
    if hasattr(tasks_mod, "save_tasks_db"):
        tasks_mod.save_tasks_db(db)  # type: ignore[attr-defined]
        return True
    return False


def _get_settings() -> Dict[str, Any]:
    db = _load_db()
    s = db.get("settings")
    return s if isinstance(s, dict) else {}


def _set_settings(settings: Dict[str, Any]) -> bool:
    db = _load_db()
    db["settings"] = settings
    return _save_db(db)


def _get_sort_mode() -> str:
    mode = _get_settings().get("sort_mode")
    return mode if mode in {SORT_PRIORITY, SORT_TIME} else SORT_TIME


def _set_sort_mode(mode: str) -> bool:
    if mode not in {SORT_PRIORITY, SORT_TIME}:
        return False
    s = _get_settings()
    s["sort_mode"] = mode
    return _set_settings(s)


def _get_origin_mode() -> str:
    mode = _get_settings().get("origin_mode")
    return mode if mode in {ORIGIN_HOME, ORIGIN_WORK, ORIGIN_CURRENT} else ORIGIN_HOME


def _set_origin_mode(mode: str) -> bool:
    if mode not in {ORIGIN_HOME, ORIGIN_WORK, ORIGIN_CURRENT}:
        return False
    s = _get_settings()
    s["origin_mode"] = mode
    return _set_settings(s)


def _set_place(key: str, value: str) -> bool:
    s = _get_settings()
    s[key] = value
    # stamp last update for current location
    if key == "origin_current":
        s["origin_current_updated_at"] = datetime.now().isoformat(timespec="seconds")
    return _set_settings(s)


def _get_place(key: str) -> Optional[str]:
    v = _get_settings().get(key)
    return str(v).strip() if isinstance(v, str) and v.strip() else None


def _get_origin_address() -> Optional[str]:
    """Resolve origin based on selected origin_mode, with fallback:
    tu -> dom -> praca
    dom -> dom
    praca -> praca
    """
    mode = _get_origin_mode()
    if mode == ORIGIN_CURRENT:
        cur = _get_place("origin_current")
        if cur:
            return cur
        # fallback
        home = _get_place("origin_home")
        if home:
            return home
        return _get_place("origin_work")

    if mode == ORIGIN_WORK:
        work = _get_place("origin_work")
        if work:
            return work
        return _get_place("origin_home")

    # ORIGIN_HOME
    home = _get_place("origin_home")
    if home:
        return home
    return _get_place("origin_work")


# -----------------------------
# Sorting & display helpers
# -----------------------------
def _parse_time_to_minutes(t: Optional[str]) -> Optional[int]:
    if not t:
        return None
    m = re.match(r"^(\d{1,2}):(\d{2})$", str(t).strip())
    if not m:
        return None
    hh, mm = int(m.group(1)), int(m.group(2))
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None
    return hh * 60 + mm


def _parse_created_at(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(str(ts))
    except Exception:
        return None


def _sort_for_list(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort used by list/delete and LIVE numbering.

    Single source of truth lives in app.b2c.tasks.sort_for_list.
    """
    mode = _get_sort_mode()
    try:
        return tasks_mod.sort_for_list(tasks or [], mode=mode)
    except Exception:
        return tasks or []



def _label_for_date(d: date) -> str:
    if d == date.today():
        return "dziś"
    if d == date.today() + timedelta(days=1):
        return "jutro"
    return d.isoformat()


def _parse_date_arg(arg: str) -> Optional[date]:
    if arg in {"dziś", "dzis", "dzisiaj"}:
        return date.today()
    if arg == "jutro":
        return date.today() + timedelta(days=1)
    try:
        return date.fromisoformat(arg)
    except Exception:
        return None


def _extract_date_and_index(parts: List[str], default_date: date) -> Optional[Tuple[date, int]]:
    if len(parts) == 2:
        try:
            return (default_date, int(parts[1]))
        except Exception:
            return None
    if len(parts) >= 3:
        d = _parse_date_arg(parts[1])
        if d is None:
            return None
        try:
            return (d, int(parts[2]))
        except Exception:
            return None
    return None



def _normalize_travel_mode(s: str) -> Optional[str]:
    t = (s or "").strip().lower()
    t = t.replace("ą","a").replace("ę","e").replace("ł","l").replace("ó","o").replace("ś","s").replace("ć","c").replace("ń","n").replace("ż","z").replace("ź","z")
    # allow variants
    if t in {"samochod", "samochodem", "auto", "car", "driving"}:
        return "samochod"
    if t in {"autobus", "komunikacja", "komunikacja_miejska", "komunikacja miejska", "komunikacja", "komunikacja", "transit", "bus"}:
        return "autobus"
    if t in {"rower", "rowerem", "bike", "biking"}:
        return "rower"
    if t in {"pieszo", "pieszo.", "spacer", "walk", "walking"}:
        return "pieszo"
    return None


def _mvp_eta_minutes(travel_mode: str) -> int:
    mode = _normalize_travel_mode(travel_mode) or "samochod"
    return {"samochod": 25, "autobus": 40, "rower": 18, "pieszo": 60}.get(mode, 25)


def _google_mode_from_task(travel_mode: str) -> Optional[str]:
    tm = (travel_mode or "").lower()
    # cover Polish variants
    if tm in {"samochód", "samochodem", "auto", "car", "driving"}:
        return "driving"
    if tm in {"komunikacja", "komunikacją", "zbiorkom", "transit", "bus", "metro", "tram"}:
        return "transit"
    if tm in {"rower", "rowerem", "bike", "bicycle", "bicycling"}:
        return "bicycling"
    if tm in {"pieszo", "spacer", "walk", "walking"}:
        return "walking"
    return None


def route_intent(message: str, persona: str = "b2c", mode: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    low = (message or "").strip().lower()

    def _is_command_like(txt: str) -> bool:
        t = (txt or "").strip().lower()
        return (
            t.startswith("/")
            or t.startswith("lista")
            or t.startswith("dodaj")
            or t.startswith("usun")
            or t.startswith("usuń")
            or t.startswith("priorytet")
            or t.startswith("sort")
            or t.startswith("ustaw")
            or t.startswith("tu jestem")
            or t.startswith("start:")
            or t.startswith("rano")
            or t.startswith("diag")
            or t.startswith("help")
        )


    # =============================
    # CHECKLIST attached to task
    # =============================
    def _resolve_task_for_live_number(num: int, d: date | None = None) -> Optional[Dict[str, Any]]:
        d = d or date.today()
        tasks_for_day = _sort_for_list(tasks_mod.list_tasks_for_date(d) or [])
        if 1 <= num <= len(tasks_for_day):
            return tasks_for_day[num - 1]
        return None

    # active checklist capture (line-by-line)
    pending_c = tasks_mod.get_pending_checklist() if hasattr(tasks_mod, "get_pending_checklist") else None
    if pending_c:
        task_id = int(pending_c.get("task_id"))
        if low in {"koniec", "zapisz", "done", "stop"}:
            title = str((pending_c.get("title") or "Lista")).rstrip(":")
            if hasattr(tasks_mod, "clear_pending_checklist"):
                tasks_mod.clear_pending_checklist()
            return _as_reply("checklist_done", f"✅ Zapisano listę „{title}”.")
        if (message or "").strip().startswith("-"):
            txt = (message or "").strip().lstrip("-").strip()
            if hasattr(tasks_mod, "add_checklist_item_to_task"):
                t = tasks_mod.add_checklist_item_to_task(task_id, txt)
                cl = (t or {}).get("checklist") if isinstance(t, dict) else {}
                items = (cl or {}).get("items") if isinstance(cl, dict) else []
                idx_item = len(items) if isinstance(items, list) else "?"
                return _as_reply("checklist_item", f"✅ Dodano: {txt} (#{idx_item}). Wpisz kolejne albo `koniec`.")
        if (message or "").strip().endswith(":"):
            title = (message or "").strip().rstrip(":")
            if hasattr(tasks_mod, "set_checklist_title"):
                tasks_mod.set_checklist_title(task_id, title)
            if hasattr(tasks_mod, "set_pending_checklist"):
                tasks_mod.set_pending_checklist(task_id, title=title)
            return _as_reply("checklist", "OK — podawaj pozycje listy linia po linii. Na końcu wpisz `koniec`.")
        # while active, keep guidance instead of falling into other flows
        return _as_reply("checklist", "Podaj pozycję listy jako `- coś` albo wpisz `koniec`.")

    # start checklist capture for the last task
    if (message or "").strip().endswith(":") and low not in {"start:", "tryb:"}:
        last_task = tasks_mod.get_last_task() if hasattr(tasks_mod, "get_last_task") else None
        if last_task and isinstance(last_task, dict) and last_task.get("id") is not None:
            title = (message or "").strip().rstrip(":")
            if hasattr(tasks_mod, "set_checklist_title"):
                tasks_mod.set_checklist_title(int(last_task["id"]), title)
            if hasattr(tasks_mod, "set_pending_checklist"):
                tasks_mod.set_pending_checklist(int(last_task["id"]), title=title)
            return _as_reply("checklist", "OK — podawaj pozycje listy linia po linii. Na końcu wpisz `koniec`.")

    # pokaż 1
    m_show = re.search(r"^poka[żz]\s+(\d+)\s*$", low)
    if m_show:
        num = int(m_show.group(1))
        t = _resolve_task_for_live_number(num)
        if not t:
            return _as_reply("show_task", f"Nie ma zadania #{num} na dziś.")
        lines = [f"#{num} {_clean_title_for_display(str(t.get('title') or '(bez tytułu)'))}"]
        if t.get("location"):
            lines.append(f"Miejsce: {t.get('location')}")
        due = str(t.get("due_at") or "")
        if due:
            lines.append(f"Kiedy: {due.replace('T',' ')}")
        cl = t.get("checklist")
        if isinstance(cl, dict):
            lines.append(f"{cl.get('title') or 'Lista'}:")
            items = cl.get("items") or []
            for idx_i, it in enumerate(items, start=1):
                txt = it.get("text") if isinstance(it, dict) else str(it)
                done = bool(it.get("done")) if isinstance(it, dict) else False
                mark = "☑" if done else "☐"
                lines.append(f"{num}.{idx_i} {mark} {txt}")
        return _as_reply("show_task", "\n".join(lines))

    # zrobione 1.2 / odznacz 1.2
    m_done = re.search(r"^zrobione\s+(\d+)\.(\d+)\s*$", low)
    if m_done:
        task_no = int(m_done.group(1)); item_no = int(m_done.group(2))
        t = _resolve_task_for_live_number(task_no)
        if not t:
            return _as_reply("checklist", f"Nie ma zadania #{task_no} na dziś.")
        ok = tasks_mod.toggle_checklist_item(int(t["id"]), item_no, True) if hasattr(tasks_mod, "toggle_checklist_item") else None
        return _as_reply("checklist", "✅ Odhaczone." if ok else "Nie udało się odhaczyć pozycji.")

    m_undo = re.search(r"^odznacz\s+(\d+)\.(\d+)\s*$", low)
    if m_undo:
        task_no = int(m_undo.group(1)); item_no = int(m_undo.group(2))
        t = _resolve_task_for_live_number(task_no)
        if not t:
            return _as_reply("checklist", f"Nie ma zadania #{task_no} na dziś.")
        ok = tasks_mod.toggle_checklist_item(int(t["id"]), item_no, False) if hasattr(tasks_mod, "toggle_checklist_item") else None
        return _as_reply("checklist", "✅ Odznaczone." if ok else "Nie udało się odznaczyć pozycji.")

    m_add_item = re.search(r"^dodaj do\s+(\d+)\s*:\s*(.+)$", low)
    if m_add_item:
        task_no = int(m_add_item.group(1)); txt = message.split(":",1)[1].strip()
        t = _resolve_task_for_live_number(task_no)
        if not t:
            return _as_reply("checklist", f"Nie ma zadania #{task_no} na dziś.")
        ok = tasks_mod.add_checklist_item_manual(int(t["id"]), txt) if hasattr(tasks_mod, "add_checklist_item_manual") else None
        return _as_reply("checklist", f"✅ Dodano: {txt}" if ok else "Nie udało się dodać pozycji.")

    m_del_item = re.search(r"^(?:usu[ńn]\s+z)\s+(\d+)\s*:\s*(.+)$", low)
    if m_del_item:
        task_no = int(m_del_item.group(1)); txt = message.split(":",1)[1].strip()
        t = _resolve_task_for_live_number(task_no)
        if not t:
            return _as_reply("checklist", f"Nie ma zadania #{task_no} na dziś.")
        ok = tasks_mod.remove_checklist_item_manual(int(t["id"]), txt) if hasattr(tasks_mod, "remove_checklist_item_manual") else None
        return _as_reply("checklist", f"✅ Usunięto: {txt}" if ok else "Nie udało się usunąć pozycji.")



    # =============================
    # CHECKLIST commands (stable, no pending state)
    # =============================
    def _resolve_task_for_live_number(num: int, d: date | None = None) -> Optional[Dict[str, Any]]:
        d = d or date.today()
        tasks_for_day = _sort_for_list(tasks_mod.list_tasks_for_date(d) or [])
        if 1 <= num <= len(tasks_for_day):
            return tasks_for_day[num - 1]
        return None

    m_add_full = re.search(r"^dodaj do zadania\s+(\d+)\s+([^:]+):\s*(.+)$", low)
    if m_add_full:
        task_no = int(m_add_full.group(1))
        title = message.split(":", 1)[0].split(None, 4)[4].strip()  # preserves original case after task number
        items_part = message.split(":", 1)[1].strip()
        t = _resolve_task_for_live_number(task_no)
        if not t:
            return _as_reply("checklist", f"Nie ma zadania #{task_no} na dziś.")
        items = [x.strip() for x in items_part.split(",") if x.strip()]
        saved = tasks_mod.replace_task_checklist(int(t["id"]), title, items) if hasattr(tasks_mod, "replace_task_checklist") else None
        if not saved:
            return _as_reply("checklist", "Nie udało się dodać checklisty.")
        cl = saved.get("checklist") or {}
        lines = [f"✅ Dodano checklistę do zadania #{task_no}", "", f"{cl.get('title') or 'Lista'}:"]
        for idx_i, it in enumerate(cl.get("items") or [], start=1):
            txt = it.get("text") if isinstance(it, dict) else str(it)
            lines.append(f"{task_no}.{idx_i} ☐ {txt}")
        return _as_reply("checklist", "\n".join(lines))

    m_add_short = re.search(r"^dodaj do\s+(\d+)\s*:\s*(.+)$", low)
    if m_add_short:
        task_no = int(m_add_short.group(1))
        txt = message.split(":", 1)[1].strip()
        t = _resolve_task_for_live_number(task_no)
        if not t:
            return _as_reply("checklist", f"Nie ma zadania #{task_no} na dziś.")
        ok = tasks_mod.add_checklist_item_manual(int(t["id"]), txt) if hasattr(tasks_mod, "add_checklist_item_manual") else None
        return _as_reply("checklist", f"✅ Dodano: {txt}" if ok else "Nie udało się dodać pozycji.")

    m_show = re.search(r"^poka[żz]\s+(\d+)\s*$", low)
    if m_show:
        num = int(m_show.group(1))
        t = _resolve_task_for_live_number(num)
        if not t:
            return _as_reply("show_task", f"Nie ma zadania #{num} na dziś.")
        lines = [f"#{num} {_clean_title_for_display(str(t.get('title') or '(bez tytułu)'))}"]
        if t.get("location"):
            lines.append(f"Miejsce: {t.get('location')}")
        due = str(t.get("due_at") or "")
        if due:
            lines.append(f"Kiedy: {due.replace('T',' ')}")
        cl = t.get("checklist")
        if isinstance(cl, dict):
            lines.append("")
            lines.append(f"{cl.get('title') or 'Lista'}:")
            for idx_i, it in enumerate(cl.get("items") or [], start=1):
                txt = it.get("text") if isinstance(it, dict) else str(it)
                done = bool(it.get("done")) if isinstance(it, dict) else False
                mark = "☑" if done else "☐"
                lines.append(f"{num}.{idx_i} {mark} {txt}")
        return _as_reply("show_task", "\n".join(lines))

    m_done = re.search(r"^zrobione\s+(\d+)\.(\d+)\s*$", low)
    if m_done:
        task_no = int(m_done.group(1)); item_no = int(m_done.group(2))
        t = _resolve_task_for_live_number(task_no)
        if not t:
            return _as_reply("checklist", f"Nie ma zadania #{task_no} na dziś.")
        ok = tasks_mod.toggle_checklist_item(int(t["id"]), item_no, True) if hasattr(tasks_mod, "toggle_checklist_item") else None
        return _as_reply("checklist", "✅ Odhaczone." if ok else "Nie udało się odhaczyć pozycji.")

    m_undo = re.search(r"^odznacz\s+(\d+)\.(\d+)\s*$", low)
    if m_undo:
        task_no = int(m_undo.group(1)); item_no = int(m_undo.group(2))
        t = _resolve_task_for_live_number(task_no)
        if not t:
            return _as_reply("checklist", f"Nie ma zadania #{task_no} na dziś.")
        ok = tasks_mod.toggle_checklist_item(int(t["id"]), item_no, False) if hasattr(tasks_mod, "toggle_checklist_item") else None
        return _as_reply("checklist", "✅ Odznaczone." if ok else "Nie udało się odznaczyć pozycji.")

    m_del_item = re.search(r"^(?:usu[ńn]\s+z)\s+(\d+)\s*:\s*(.+)$", low)
    if m_del_item:
        task_no = int(m_del_item.group(1)); txt = message.split(":", 1)[1].strip()
        t = _resolve_task_for_live_number(task_no)
        if not t:
            return _as_reply("checklist", f"Nie ma zadania #{task_no} na dziś.")
        ok = tasks_mod.remove_checklist_item_manual(int(t["id"]), txt) if hasattr(tasks_mod, "remove_checklist_item_manual") else None
        return _as_reply("checklist", f"✅ Usunięto: {txt}" if ok else "Nie udało się usunąć pozycji.")


    # =============================
    # ORIGIN settings
    # =============================
    if low.startswith("ustaw dom:"):
        addr = message.split(":", 1)[1].strip()
        ok = _set_place("origin_home", addr)
        return _as_reply("set_origin_home", "✅ Ustawiono dom." if ok else "Nie udało się ustawić domu.")

    if low.startswith("ustaw praca:") or low.startswith("ustaw pracę:") or low.startswith("ustaw prace:"):
        addr = message.split(":", 1)[1].strip()
        ok = _set_place("origin_work", addr)
        return _as_reply("set_origin_work", "✅ Ustawiono pracę." if ok else "Nie udało się ustawić pracy.")

    if low.startswith("tu jestem:"):
        addr = message.split(":", 1)[1].strip()
        ok = _set_place("origin_current", addr)
        return _as_reply("set_origin_current", "✅ OK, zapamiętałem gdzie jesteś." if ok else "Nie udało się zapisać lokalizacji.")


    # =============================
    # TRAVEL mode + ETA (MVP)
    # =============================
    if low.startswith("tryb:"):
        raw = message.split(":", 1)[1].strip()
        mode_norm = _normalize_travel_mode(raw)
        if not mode_norm:
            return _as_reply("set_travel_mode", "Podaj tryb: `samochód`, `autobus/komunikacja`, `rower`, `pieszo`.")
        _set_place("travel_mode_default", mode_norm)
        pretty = {"samochod":"samochód", "autobus":"autobus", "rower":"rower", "pieszo":"pieszo"}[mode_norm]
        return _as_reply("set_travel_mode", f"✅ Ustawiono tryb: {pretty}.")

    # Shortcuts without "tryb:"
    pending_t_guard = tasks_mod.get_pending_travel()
    mode_norm = _normalize_travel_mode(low)
    if (not pending_t_guard) and mode_norm and low in {"samochod","samochód","samochodem","autobus","komunikacja","komunikacją","rower","rowerem","pieszo"}:
        _set_place("travel_mode_default", mode_norm)
        pretty = {"samochod":"samochód", "autobus":"autobus", "rower":"rower", "pieszo":"pieszo"}[mode_norm]
        return _as_reply("set_travel_mode", f"✅ Ustawiono tryb: {pretty}.")



    if low in {"czy zdążę", "czy zdzaze", "spóźnię się?", "spoznie sie?", "spoznie sie", "spóźnię się", "czy sie spoznie", "czy się spóźnię"}:
        today = date.today()
        tasks = _sort_for_list(tasks_mod.list_tasks_for_date(today) or [])
        # only tasks that have both time and location
        cand = []
        for t in tasks:
            if not isinstance(t, dict):
                continue
            due_at = str(t.get("due_at") or "")
            if "T" not in due_at:
                continue
            if not (t.get("location") or t.get("place")):
                continue
            cand.append(t)

        if not cand:
            return _as_reply("late_check", "Nie mam dziś zadania z godziną i adresem. Dodaj np. `dodaj: dentysta dziś 18:30 Narbutta 86, Warszawa`.")

        t = cand[0]
        destination = str(t.get("location") or t.get("place") or "").strip()
        origin = _get_origin_address()
        if not origin:
            return _as_reply("late_check", "Skąd ruszasz? Ustaw `ustaw dom: ...` albo `tu jestem: ...`.")

        travel_mode = str(t.get("travel_mode") or _get_place("travel_mode_default") or "samochod")
        mins = _mvp_eta_minutes(travel_mode)

        due_at = str(t.get("due_at") or "")
        try:
            dt = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            if dt.tzinfo is not None:
                dt = dt.astimezone().replace(tzinfo=None)
        except Exception:
            return _as_reply("late_check", "Nie potrafię odczytać godziny tego zadania.")

        now = datetime.now()
        deadline = dt - timedelta(minutes=mins + TRAVEL_BUFFER_MIN)
        delta = deadline - now

        pretty = {"samochod":"samochód", "autobus":"autobus", "rower":"rower", "pieszo":"pieszo"}.get(_normalize_travel_mode(travel_mode) or "samochod", "samochód")
        leave_hhmm = deadline.strftime("%H:%M")

        # minutes as integers
        mins_left = int(math.ceil(delta.total_seconds() / 60.0))
        if delta.total_seconds() >= 0:
            return _as_reply(
                "late_check",
                f"✅ Zdążysz. Masz jeszcze **{mins_left} min**.\nWyjdź o **{leave_hhmm}** (bufor {TRAVEL_BUFFER_MIN} min).\nETA ({pretty}): {mins} min\n{origin} → {destination}",
            )

        late_by = int(math.ceil((now - deadline).total_seconds() / 60.0))
        return _as_reply(
            "late_check",
            f"⏰ Powinnaś wyjść **{late_by} min temu**.\nSpóźnisz się około **{late_by} min** (przy stałym ETA).\nWyjdź teraz.\nETA ({pretty}): {mins} min\n{origin} → {destination}",
        )


    if low.startswith("eta"):
        # eta or eta <nr>
        parts = (message or "").strip().split()
        want_no = None
        if len(parts) >= 2:
            try:
                want_no = int(parts[1])
            except Exception:
                want_no = None

        today = date.today()
        tasks = _sort_for_list(tasks_mod.list_tasks_for_date(today) or [])
        # keep only tasks with a location
        tasks_loc = [t for t in tasks if isinstance(t, dict) and (t.get("location") or t.get("place"))]
        if not tasks_loc:
            return _as_reply("eta", "Nie mam dzisiaj zadania z adresem. Dodaj np. `dodaj: dentysta dziś 18:30 Narbutta 86, Warszawa`.")

        t = None
        if want_no is not None:
            idx = want_no - 1
            if 0 <= idx < len(tasks_loc):
                t = tasks_loc[idx]
        if t is None:
            t = tasks_loc[0]

        destination = str(t.get("location") or t.get("place") or "").strip()
        if not destination:
            return _as_reply("eta", "To zadanie nie ma adresu.")

        origin = _get_origin_address()
        if not origin:
            return _as_reply("eta", "Skąd ruszasz? Ustaw `ustaw dom: ...` albo `tu jestem: ...`.")

        travel_mode = str(t.get("travel_mode") or _get_place("travel_mode_default") or "samochod")
        mins = _mvp_eta_minutes(travel_mode)

        # Leave time if we have due_at with time
        due_at = str(t.get("due_at") or "")
        leave_line = ""
        if "T" in due_at:
            try:
                dt = datetime.fromisoformat(due_at.replace("Z","+00:00"))
                if dt.tzinfo is not None:
                    dt = dt.astimezone().replace(tzinfo=None)
                leave_dt = dt - timedelta(minutes=mins + TRAVEL_BUFFER_MIN)
                leave_line = f"\nWyjdź o **{leave_dt.strftime('%H:%M')}** (bufor {TRAVEL_BUFFER_MIN} min)."
            except Exception:
                leave_line = ""

        pretty = {"samochod":"samochód", "autobus":"autobus", "rower":"rower", "pieszo":"pieszo"}.get(_normalize_travel_mode(travel_mode) or "samochod", "samochód")
        return _as_reply("eta", f"ETA ({pretty}): **{mins} min**\n{origin} → {destination}{leave_line}")
    if low.startswith("start:"):
        arg = message.split(":", 1)[1].strip().lower()
        if arg in {"dom", "home"}:
            ok = _set_origin_mode(ORIGIN_HOME)
            return _as_reply("set_origin_mode", "✅ Start ustawiony: dom." if ok else "Nie udało się ustawić.")
        if arg in {"praca", "work"}:
            ok = _set_origin_mode(ORIGIN_WORK)
            return _as_reply("set_origin_mode", "✅ Start ustawiony: praca." if ok else "Nie udało się ustawić.")
        if arg in {"tu", "obecna", "current"}:
            ok = _set_origin_mode(ORIGIN_CURRENT)
            return _as_reply("set_origin_mode", "✅ Start ustawiony: obecna lokalizacja (tu)." if ok else "Nie udało się ustawić.")
        return _as_reply("set_origin_mode", "Użyj: `start: dom` / `start: praca` / `start: tu`.")

    # =============================
    # SORT (toggle)
    # =============================
    if low.startswith("sort"):
        parts = low.split()
        if len(parts) == 1:
            cur = _get_sort_mode()
            label = "priorytet" if cur == SORT_PRIORITY else "czas"
            return _as_reply("sort_mode", f"Aktualne sortowanie: **{label}**. Ustaw: `sort priorytet` lub `sort czas`.")
        arg = parts[1]
        if arg in {"priorytet", "priority", "p"}:
            ok = _set_sort_mode(SORT_PRIORITY)
            return _as_reply("sort_mode", "✅ Ustawiono sortowanie: **priorytet**." if ok else "Nie udało się zapisać.")
        if arg in {"czas", "time", "t"}:
            ok = _set_sort_mode(SORT_TIME)
            return _as_reply("sort_mode", "✅ Ustawiono sortowanie: **czas**." if ok else "Nie udało się zapisać.")
        return _as_reply("sort_mode", "Użyj: `sort priorytet` albo `sort czas`.")

    # =============================
    # PRIORYTET (dla istniejącego zadania)
    # priorytet 2 p1
    # priorytet jutro 2 p3
    # priorytet 2026-02-22 2 p1
    # =============================
    if low.startswith("priorytet"):
        parts = low.split()
        if len(parts) not in {3, 4}:
            return _as_reply("set_priority", "Użyj: `priorytet 2 p1` albo `priorytet jutro 2 p3`.")

        if len(parts) == 3:
            target_date = date.today()
            n_s = parts[1]
            p_s = parts[2]
        else:
            target_date = _parse_date_arg(parts[1])
            if target_date is None:
                return _as_reply("set_priority", "Nie rozumiem daty. Użyj: `priorytet jutro 2 p3` albo `priorytet 2026-02-22 2 p1`.")
            n_s = parts[2]
            p_s = parts[3]

        try:
            n = int(n_s)
        except Exception:
            return _as_reply("set_priority", "Podaj numer z listy, np. `priorytet 2 p1`.")

        m = re.match(r"^p?(\d)$", p_s)
        if not m:
            return _as_reply("set_priority", "Podaj priorytet jako p1..p5, np. `priorytet 2 p1`.")
        pr = int(m.group(1))
        if pr < 1 or pr > 5:
            return _as_reply("set_priority", "Priorytet musi być w zakresie p1..p5.")

        tasks = _sort_for_list(tasks_mod.list_tasks_for_date(target_date) or [])
        if not (1 <= n <= len(tasks)):
            return _as_reply("set_priority", f"Nie ma zadania #{n} na {_label_for_date(target_date)}.")

        tid = int(tasks[n - 1].get("id"))
        out = tasks_mod.update_task(tid, priority=pr, priority_explicit=True)
        if not out:
            return _as_reply("set_priority", "Nie udało się ustawić priorytetu.")

        emoji = PRIORITY_EMOJI.get(pr, f"p{pr}")
        return _as_reply("set_priority", f"✅ Ustawiono priorytet {emoji} dla zadania #{n} na {_label_for_date(target_date)}.")

    # =============================
    # DELETE (LIVE numeracja) + data
    # usuń 2
    # usuń jutro 2
    # usuń 2026-02-22 2
    # =============================
    if low.startswith("usuń") or low.startswith("usun"):
        parts = low.split()
        parsed = _extract_date_and_index(parts, default_date=date.today())
        if not parsed:
            return _as_reply("delete_task", "Użyj: `usuń 2` albo `usuń jutro 2` albo `usuń 2026-02-22 2`.")

        target_date, n = parsed
        tasks = _sort_for_list(tasks_mod.list_tasks_for_date(target_date) or [])

        if 1 <= n <= len(tasks):
            tid = int(tasks[n - 1].get("id"))
            tasks_mod.delete_task_by_id(tid)
            return _as_reply("delete_task", f"🗑 Usunięto zadanie #{n} na {_label_for_date(target_date)}.")

        # fallback: traktuj jako ID tylko dla formatu "usuń <liczba>"
        if len(parts) == 2:
            out = tasks_mod.delete_task_by_id(n)
            return _as_reply("delete_task", _reply_from_any(out, default=f"🗑 Usunięto zadanie #{n}."))
        return _as_reply("delete_task", f"Nie ma zadania #{n} na {_label_for_date(target_date)}.")

    # =============================
    # LISTA (LIVE numeracja) + data
    # lista / lista dziś / lista jutro / lista YYYY-MM-DD
    # + ETA tylko dla zadań z godziną
    # =============================
    if low.startswith("lista") or low == "list":
        parts = (low.split() if low != "list" else ["lista"])
        target_date = date.today()

        if len(parts) >= 2:
            d = _parse_date_arg(parts[1])
            if d is None:
                return _as_reply("list_tasks", "Nie rozumiem daty. Użyj: `lista jutro` albo `lista 2026-02-22`.")
            target_date = d

        tasks = _sort_for_list(tasks_mod.list_tasks_for_date(target_date) or [])
        if not tasks:
            return _as_reply("list_tasks", f"Brak zaplanowanych zadań na {_label_for_date(target_date)}.")

        origin = _get_origin_address()
        api_key_present = bool(os.getenv("GOOGLE_MAPS_API_KEY"))

        lines = [f"**Najważniejsze na {_label_for_date(target_date)}:**"]
        for idx, t in enumerate(tasks, start=1):
            title = str(t.get("title") or "(bez tytułu)").strip()
            loc = str(t.get("location") or "").strip()
            time_s = _task_time_str(t)
            when = f"{time_s} — " if time_s else ""

            # Emoji priorytetu:
            # - p1: 🔴 zawsze
            # - p2: 🟠 tylko jeśli jawnie nadany (priority_explicit=True)
            # - p3: 🟢 zawsze
            emoji = ""
            try:
                pr = int(t.get("priority")) if t.get("priority") is not None else None
            except Exception:
                pr = None
            explicit = bool(t.get("priority_explicit"))
            if pr in PRIORITY_EMOJI:
                if pr == 2:
                    if explicit:
                        emoji = PRIORITY_EMOJI[pr] + " "
                else:
                    emoji = PRIORITY_EMOJI[pr] + " "
            elif pr:
                if pr == 2:
                    if explicit:
                        emoji = "p2 "
                else:
                    emoji = f"p{pr} "

            # ETA only if task has time
            eta_s = ""
            travel_mode = t.get("travel_mode") or t.get("mode")
            gm = _google_mode_from_task(str(travel_mode or ""))
            if api_key_present and origin and loc and time_s and gm:
                minutes = get_eta_minutes(origin=origin, destination=loc, mode=gm)
                if minutes is not None:
                    eta_s = f" (ETA: {minutes} min)"

            tail = f", {loc}" if loc else ""
            lines.append(f"• #{idx} {emoji}{when}{title}{tail}{eta_s}")

        # Small hint if not configured
        if not api_key_present:
            lines.append("")
            lines.append("_Aby włączyć ETA: ustaw zmienną środowiskową `GOOGLE_MAPS_API_KEY`._")
        elif not origin:
            lines.append("")
            lines.append("_Aby włączyć ETA: ustaw `ustaw dom:` lub `ustaw praca:` albo `tu jestem:`._")

        return _as_reply("list_tasks", "\n".join(lines))

    # =============================
    # Pending reminder FIRST
    # =============================
    pending_r = tasks_mod.get_pending_reminder()
    if pending_r:
        task_id = int(pending_r.get("task_id"))
        reminder_at = str(pending_r.get("reminder_at"))
    
        if low in YES:
            tasks_mod.clear_pending_reminder()
            out = tasks_mod.set_reminder(task_id, reminder_at, enabled=True)
    
            # Make numbering consistent with the live list (router numbering), not internal task IDs.
            live_no = None
            try:
                t = tasks_mod.get_task(task_id)
                if t:
                    due_at = str(t.get("due_at") or "")
                    due_date = due_at.split("T", 1)[0] if "T" in due_at else (due_at[:10] if len(due_at) >= 10 else "")
                    tasks_for_day: List[Dict[str, Any]] = []
                    if due_date:
                        if hasattr(tasks_mod, "list_tasks_for_date"):
                            tasks_for_day = tasks_mod.list_tasks_for_date(due_date) or []
                        elif hasattr(tasks_mod, "list_tasks"):
                            tasks_for_day = tasks_mod.list_tasks(date=due_date) or []
                    tasks_for_day = _sort_for_list(tasks_for_day)
                    for i, tt in enumerate(tasks_for_day, start=1):
                        if tt.get("id") == task_id:
                            live_no = i
                            break
            except Exception:
                live_no = None
    
            if isinstance(out, dict):
                if live_no is not None:
                    out["reply"] = f"⏰ Ustawiłem przypomnienie dla zadania #{live_no} na **{reminder_at}**."
                else:
                    out["reply"] = f"⏰ Ustawiłem przypomnienie na **{reminder_at}**."
            return _as_reply("set_reminder", _reply_from_any(out, default=f"⏰ Ustawiono przypomnienie na {reminder_at}."))
    
        if low in NO:
            tasks_mod.clear_pending_reminder()
            return _as_reply("set_reminder", "OK — bez przypomnienia.")
    
        if not _is_command_like(message):
            return _as_reply("set_reminder", f"Ustawić przypomnienie na **{reminder_at}**? (tak/nie)")
    
    # ============================
    # Pending clear-day confirmation
    # ============================
    pending_clear = tasks_mod.get_pending_clear()
    if pending_clear:
        ans = low.strip()
        if ans in ("tak", "t", "yes", "y"):
            date_iso = str(pending_clear.get("date") or "")
            removed = tasks_mod.clear_tasks_for_date(date_iso)
            tasks_mod.clear_pending_clear()
            return _as_reply("cleared_day", f"🧹 Usunięto {removed} zadań na {date_iso}.")
        if ans in ("nie", "n", "no"):
            tasks_mod.clear_pending_clear()
            return _as_reply("clear_cancelled", "OK, nie usuwam.")
        return _as_reply("confirm_clear_day", "Na pewno usunąć **wszystkie** zadania na dziś? (tak/nie)")
    # Pending travel (2-step: start -> mode)
    # =============================
    pending_t = tasks_mod.get_pending_travel()
    if pending_t:
        created_from = str(pending_t.get("created_from") or "")
        try:
            pending_task_id = int(pending_t.get("task_id"))
        except Exception:
            pending_task_id = None
    
        # Step 1: ask/handle START (always after adding timed+location task)
        if created_from == "add_start" and pending_task_id is not None:
            if _is_command_like(message) or not (message or '').strip():
                return _as_reply("set_origin_mode", "Skąd ruszasz? Napisz: `dom` / `praca` / `tu` albo podaj adres startu.")
    
            ans = (message or "").strip()
            ans_low = ans.lower()
            if ans_low in {"dom", "home"}:
                _set_place("origin_mode", ORIGIN_HOME)
            elif ans_low in {"praca", "work"}:
                _set_place("origin_mode", ORIGIN_WORK)
            elif ans_low in {"tu", "tutaj", "obecna", "obecna lokalizacja"}:
                _set_place("origin_mode", ORIGIN_HERE)
            else:
                # Treat as explicit address start
                _set_place("origin_custom", ans)
                _set_place("origin_mode", ORIGIN_CUSTOM)
    
            # If task already has travel mode, skip asking and go straight to reminder proposal
            t = tasks_mod.get_task(pending_task_id)
            travel_mode = (t or {}).get("travel_mode") or (t or {}).get("mode")
            if travel_mode:
                tasks_mod.clear_pending_travel()
    
                origin = _get_origin_address()
                loc = (t or {}).get("location")
                due_at = (t or {}).get("due_at")
                gm = _google_mode_from_task(str(travel_mode))
                if origin and loc and due_at and gm and os.getenv("GOOGLE_MAPS_API_KEY"):
                    mins = get_eta_minutes(origin=origin, destination=str(loc), mode=gm)
                    if mins is not None:
                        try:
                            dt = datetime.fromisoformat(str(due_at).replace("Z", "+00:00"))
                        except Exception:
                            dt = None
                        if dt is not None:
                            if dt.tzinfo is not None:
                                dt = dt.astimezone().replace(tzinfo=None)
                            remind_dt = dt - timedelta(minutes=int(mins) + 10)
                            reminder_at = remind_dt.strftime("%Y-%m-%dT%H:%M")
                            tasks_mod.set_pending_reminder(pending_task_id, reminder_at, created_from="add")
                            return _as_reply("set_reminder", f"✅ OK. ETA: **{mins} min**. Proponuję wyjść o **{remind_dt.strftime('%H:%M')}**. Ustawić przypomnienie? (tak/nie)")
    
                return _as_reply("set_origin_mode", "✅ OK.")
    
            # Next: ask for travel mode
            tasks_mod.set_pending_travel(pending_task_id, created_from="add_mode")
            return _as_reply("set_travel_mode", "✅ OK. Jak jedziesz? Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")
    
        # Step 2: handle travel mode
        if created_from == "add_mode" and pending_task_id is not None:
            if _is_command_like(message) or not (message or "").strip():
                return _as_reply("set_travel_mode", "✅ OK. Jak jedziesz? Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")
            out = tasks_mod.apply_travel_mode_to_pending(message)
            if out is None:
                return _as_reply("set_travel_mode", "Nie złapałam sposobu dojazdu. Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")
            if out is not None:
                t = tasks_mod.get_task(pending_task_id)
                origin = _get_origin_address()
                loc = (t or {}).get("location")
                due_at = (t or {}).get("due_at")
                travel_mode = (t or {}).get("travel_mode") or (t or {}).get("mode")
                gm = _google_mode_from_task(str(travel_mode or ""))
                if origin and loc and due_at and gm and os.getenv("GOOGLE_MAPS_API_KEY"):
                    mins = get_eta_minutes(origin=origin, destination=str(loc), mode=gm)
                    if mins is not None:
                        try:
                            dt = datetime.fromisoformat(str(due_at).replace("Z", "+00:00"))
                        except Exception:
                            dt = None
                        if dt is not None:
                            if dt.tzinfo is not None:
                                dt = dt.astimezone().replace(tzinfo=None)
                            remind_dt = dt - timedelta(minutes=int(mins) + 10)
                            reminder_at = remind_dt.strftime("%Y-%m-%dT%H:%M")
                            tasks_mod.set_pending_reminder(pending_task_id, reminder_at, created_from="add")
                            base = _reply_from_any(out, default="OK")
                            return _as_reply("set_reminder", f"{base}\n\nETA: **{mins} min**. Proponuję wyjść o **{remind_dt.strftime('%H:%M')}**. Ustawić przypomnienie? (tak/nie)")
    
                return _as_reply("set_travel_mode", _reply_from_any(out, default="OK"))
    
            if not _is_command_like(message):
                return _as_reply("set_travel_mode", "Jak jedziesz? Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")
    
        # fallback (older flows)
        out = tasks_mod.apply_travel_mode_to_pending(message)
        if out is not None:
            return _as_reply("set_travel_mode", _reply_from_any(out, default="OK"))
        if not _is_command_like(message):
            return _as_reply("set_travel_mode", "Jak jedziesz? Napisz: `samochodem` / `komunikacją` / `rowerem` / `pieszo`.")
    # DODAJ (spójny numer LIVE z listą)
    # =============================
    if low.startswith("dodaj:") or low.startswith("dodaj "):
        out = tasks_mod.add_task(message)
    
        # spróbuj wyciągnąć task_id i datę zadania z odpowiedzi tasks_mod
        task = out.get("task") if isinstance(out, dict) else None
        tid = None
        task_date = date.today()
    
        if isinstance(task, dict):
            try:
                tid = int(task.get("id")) if task.get("id") is not None else None
            except Exception:
                tid = None
    
            due_at = task.get("due_at")
            due_date = task.get("due_date")
    
            # Canonical: if we have due_at (date+time), use that date.
            if isinstance(due_at, str) and len(due_at) >= 10:
                try:
                    task_date = date.fromisoformat(due_at[:10])
                except Exception:
                    task_date = date.today()
            elif isinstance(due_date, str):
                try:
                    task_date = date.fromisoformat(due_date)
                except Exception:
                    task_date = date.today()
    
        # fallback: parsuj ID z tekstu odpowiedzi
        if tid is None:
            txt = _reply_from_any(out, default="")
            m = re.search(r"#(\d+)", txt)
            if m:
                try:
                    tid = int(m.group(1))
                except Exception:
                    tid = None
    
        if tid is not None:
            tasks_for_day = _sort_for_list(tasks_mod.list_tasks_for_date(task_date) or [])
    
            matched: Optional[Tuple[int, Dict[str, Any]]] = None
    
            # 1) Prefer match by internal stable id
            if tid is not None:
                for idx, t in enumerate(tasks_for_day, start=1):
                    try:
                        if str(t.get("id")) == str(tid):
                            matched = (idx, t)
                            break
                    except Exception:
                        continue
    
            # 2) Fallback: match by (due_at + title) from returned task payload
            if matched is None and isinstance(task, dict):
                want_title = str(task.get("title") or "").strip()
                want_due_at = str(task.get("due_at") or "").strip()
                if want_title or want_due_at:
                    for idx, t in enumerate(tasks_for_day, start=1):
                        try:
                            if want_due_at and str(t.get("due_at") or "").strip() != want_due_at:
                                continue
                            if want_title and str(t.get("title") or "").strip() != want_title:
                                continue
                            matched = (idx, t)
                            break
                        except Exception:
                            continue
    
            if matched is not None:
                idx, t = matched
                title = str(t.get("title") or "(bez tytułu)").strip()
                base_msg = f"✅ Dodane zadanie #{idx}: {title} (na {_label_for_date(task_date)})"
    
                # If task has a concrete hour AND location, start a short flow: ALWAYS ask START, then travel mode.
                has_time = bool(_task_time_str(t))
                has_loc = bool(t.get("location"))
                if has_time and has_loc:
                    # keep stable id (not live number) in pending flow
                    try:
                        tasks_mod.set_pending_travel(int(t.get("id")), created_from="add_start")
                    except Exception:
                        if tid is not None:
                            tasks_mod.set_pending_travel(int(tid), created_from="add_start")
                    return _as_reply(
                        "set_origin_mode",
                        base_msg + "\n\nSkąd ruszasz? Napisz: `dom` / `praca` / `tu` albo podaj adres startu."
                    )
    
                return _as_reply("add_task", base_msg)
    
        return _as_reply("add_task", _reply_from_any(out))
    
    # =============================
    # =============================
    # MORNING (no questions; just overview + refresh ETA cache)
    # =============================
    if low in {"rano", "dzień dobry", "dzien dobry", "poranek"}:
        today = date.today()
        tasks_today = _sort_for_list(tasks_mod.list_tasks_for_date(today) or [])
        if not tasks_today:
            return _as_reply("morning", "Dzień dobry 🙂 Dziś nie masz żadnych zadań na liście.")
    
        c1 = c2 = c3 = 0
        for t in tasks_today:
            pr = t.get("priority")
            if pr == 1:
                c1 += 1
            elif pr == 2:
                c2 += 1
            elif pr == 3:
                c3 += 1
    
        api_key_present = bool(os.getenv("GOOGLE_MAPS_API_KEY"))
        origin = _get_origin_address()
    
        out_lines = []
        out_lines.append(f"Dzień dobry 🙂 Masz dziś **{len(tasks_today)}** zadań. (p1: {c1}, p2: {c2}, p3: {c3})")
        out_lines.append("")
        out_lines.append("**Najbliższe z godziną:**")
    
        shown = 0
        for t in tasks_today:
            time_s = _task_time_str(t)
            if not time_s:
                continue
            title = str(t.get("title") or "(bez tytułu)").strip()
            loc = t.get("location")
            pr = t.get("priority")
            emoji = _priority_emoji(pr, bool(t.get("priority_explicit")))
    
            eta_s = ""
            travel_mode = t.get("travel_mode") or t.get("mode")
            gm = _google_mode_from_task(str(travel_mode or ""))
            if api_key_present and origin and loc and gm:
                mins = get_eta_minutes(origin=origin, destination=str(loc), mode=gm)
                if mins is not None:
                    eta_s = f" (ETA: {mins} min)"
    
            tail = f", {loc}" if loc else ""
            out_lines.append(f"• {emoji}{time_s} — {title}{tail}{eta_s}")
            shown += 1
            if shown >= 3:
                break
    
        if shown == 0:
            out_lines.append("• (brak zadań z konkretną godziną)")
    
        return _as_reply("morning", "\n".join(out_lines))
    return _as_reply("unknown", "Nie mam jeszcze tej komendy. Spróbuj: `lista`, `dodaj: ...`, `usuń ...`, `priorytet ...`.")