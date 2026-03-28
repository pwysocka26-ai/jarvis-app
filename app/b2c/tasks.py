from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# --- Files ---
DATA_DIR = Path("data/memory")
TASKS_FILE = DATA_DIR / "tasks.json"
PENDING_TRAVEL_FILE = DATA_DIR / "pending_travel.json"
PENDING_CLEAR_FILE = DATA_DIR / "pending_clear.json"
PENDING_REMINDER_FILE = DATA_DIR / "pending_reminder.json"
PENDING_CHECKLIST_FILE = DATA_DIR / "pending_checklist.json"

# --- Travel mode parsing ---
TRAVEL_MODES = {
    "samochodem": "samochodem",
    "auto": "samochodem",
    "autem": "samochodem",
    "rowerem": "rowerem",
    "bike": "rowerem",
    "pieszo": "pieszo",
    "piechota": "pieszo",
    "komunikacją": "komunikacją",
    "komunikacja": "komunikacją",
    "zbiorkom": "komunikacją",
    "tramwajem": "komunikacją",
    "metrem": "komunikacją",
    "autobusem": "komunikacją",
}

def _ensure_dir(p: Path) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
# Public alias (tests & older callers)
def ensure_dir(p: Path) -> None:
    _ensure_dir(p)


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _save_json(path: Path, data: Any) -> None:
    _ensure_dir(path)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def parse_travel_mode(text: str) -> Optional[str]:
    low = (text or "").strip().lower()
    # exact token
    if low in TRAVEL_MODES:
        return TRAVEL_MODES[low]
    # search word boundary
    for k, v in TRAVEL_MODES.items():
        if re.search(rf"\b{re.escape(k)}\b", low):
            return v
    return None

def _parse_date_time_polish(text: str) -> Tuple[Optional[str], Optional[str], str]:
    """
    Very small parser for phrases like:
    - "dziś 19:00"
    - "jutro 8:30"
    - "2026-02-10 19:00"
    Returns (due_date_iso 'YYYY-MM-DD', due_time 'HH:MM', cleaned_text_without_datetime)
    """
    s = (text or "").strip()

    # ISO date optionally + time
    m = re.search(r"(\d{4}-\d{2}-\d{2})(?:\s+(\d{1,2}:\d{2}))?", s)
    if m:
        d = m.group(1)
        t = m.group(2)
        cleaned = (s[:m.start()] + s[m.end():]).strip(" ,")
        return d, t, cleaned

    today = date.today()
    if re.search(r"\bdzi[śs]\b", s, flags=re.IGNORECASE):
        d = today.isoformat()
        s2 = re.sub(r"\bdzi[śs]\b", "", s, flags=re.IGNORECASE).strip()
    elif re.search(r"\bjutro\b", s, flags=re.IGNORECASE):
        d = (today.fromordinal(today.toordinal() + 1)).isoformat()
        s2 = re.sub(r"\bjutro\b", "", s, flags=re.IGNORECASE).strip()
    else:
        d = None
        s2 = s

    mt = re.search(r"\b(\d{1,2}:\d{2})\b", s2)
    t = mt.group(1) if mt else None
    if t:
        # If user provided only a time (e.g. "23:50") without "dziś/jutro/2026-..",
        # default to today so the task appears in today's plan.
        if d is None:
            d = today.isoformat()
        s2 = (s2[:mt.start()] + s2[mt.end():]).strip(" ,")
    return d, t, s2.strip(" ,")

def load_tasks_db() -> Dict[str, Any]:
    db = _load_json(TASKS_FILE, default={"tasks": []})
    if not isinstance(db, dict) or "tasks" not in db or not isinstance(db.get("tasks"), list):
        db = {"tasks": []}
    return db

def save_tasks_db(db: Dict[str, Any]) -> None:
    _save_json(TASKS_FILE, db)


# --- Backwards-compatible API aliases (older parts of Jarvis import these names) ---

def load_tasks():
    """Compatibility wrapper.

    Historically many parts of Jarvis treated the tasks store as a *list*.
    Newer code stores a JSON object: {"tasks": [...]}. This function always
    returns the list to avoid subtle bugs (e.g. iterating dict keys).
    """
    db = load_tasks_db()
    tasks = db.get("tasks", [])
    return tasks if isinstance(tasks, list) else []

def save_tasks(db):
    """Compatibility wrapper.

    Accepts either a list of tasks or a full db dict.
    """
    if isinstance(db, dict):
        return save_tasks_db(db)
    if isinstance(db, list):
        return save_tasks_db({"tasks": db})
    # Defensive fallback
    return save_tasks_db({"tasks": []})

def pop_pending_reminder():
    """Return and clear pending reminder (compat helper)."""
    pending = get_pending_reminder()
    if pending:
        clear_pending_reminder()
    return pending

def _next_id(tasks: List[Dict[str, Any]]) -> int:
    """Smallest free positive integer id.

    Re-uses gaps after deletions so the user sees ids 1..N whenever possible.
    """
    used = set()
    for t in tasks:
        try:
            used.add(int(t.get("id")))
        except Exception:
            continue
    i = 1
    while i in used:
        i += 1
    return i


_PR_RE = re.compile(r"^p\s*([1-5])$", re.IGNORECASE)


def _parse_priority(token: str):
    token = (token or "").strip().lower()
    m = _PR_RE.match(token)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _parse_duration_minutes(token: str):
    """Parse durations like: 30m, 90m, 1h, 1h30m, 1h 30m, 45min."""
    tok = (token or "").strip().lower().replace("minutes", "min").replace("mins", "min")
    tok = re.sub(r"\s+", "", tok)
    if not tok:
        return None
    m = re.match(r"^(\d+)(?:m|min)$", tok)
    if m:
        return int(m.group(1))
    m = re.match(r"^(\d+)h(?:(\d+)(?:m|min)?)?$", tok)
    if m:
        h = int(m.group(1))
        mm = int(m.group(2) or 0)
        return h * 60 + mm
    return None


def _strip_meta_tokens_from_title(title: str):
    """Allow 'dentysta p1 30m' (no commas) and strip meta tokens from the end.

    If multiple meta tokens are present (e.g. 'p2 p1'), we strip *all* of them and
    keep the last one as the effective value (closest to the end of the input).
    """
    if not title:
        return "", None, None
    words = title.strip().split()
    pr = None
    dur = None
    while words:
        w = words[-1]
        p = _parse_priority(w)
        if p is not None:
            pr = p  # overwrite to support '... p2 p1'
            words.pop()
            continue
        d = _parse_duration_minutes(w)
        if d is not None:
            dur = d  # overwrite to support duplicates
            words.pop()
            continue
        break
    return " ".join(words).strip(), pr, dur



def _infer_location_from_title(title: str) -> Tuple[str, Optional[str]]:
    raw = (title or "").strip()
    if not raw:
        return raw, None
    tokens = raw.split()
    if len(tokens) < 3:
        return raw, None
    digit_idx = None
    for i, tok in enumerate(tokens):
        if re.search(r"\d", tok):
            digit_idx = i
            break
    if digit_idx is None:
        return raw, None
    start = max(1, digit_idx - 1)
    street_markers = {"ul", "ul.", "al", "al.", "aleje", "pl", "pl.", "plac", "os", "os.", "osiedle"}
    if start - 1 >= 0 and tokens[start - 1].lower() in street_markers:
        start -= 1
    title_part = " ".join(tokens[:start]).strip(" ,")
    loc_part = " ".join(tokens[start:]).strip(" ,")
    if not title_part or not loc_part or not re.search(r"\d", loc_part):
        return raw, None
    return title_part, loc_part

def add_task(raw: str) -> Dict[str, Any]:
    """Adds a task. Accepts optional travel mode anywhere in text."""
    raw = (raw or "").strip()
    travel = parse_travel_mode(raw)

    due_date, due_time, rest = _parse_date_time_polish(raw)
    title = rest.strip()
    # Defensive: strip command prefix if it leaked into the title
    title = re.sub(r"^\s*[-•]*\s*(dodaj|add)\s*:?\s*", "", title, flags=re.I)

    # normalize separators
    title = re.sub(r"\s+", " ", title).strip(" ,")

    # Allow meta tokens even without commas: "... p1 30m"
    title, pr_from_title, dur_from_title = _strip_meta_tokens_from_title(title)

    # if user wrote "... , samochodem" treat as travel mode and remove from title
    if travel:
        title = re.sub(rf"(?:,|\s)+{re.escape(travel)}\s*$", "", title, flags=re.IGNORECASE).strip(" ,")

    # Optional parsing: title, location..., p1, 30m
    location = None
    priority = pr_from_title
    duration_min = dur_from_title
    if "," in title:
        parts = [p.strip() for p in title.split(",") if p.strip()]
        if parts:
            title = parts[0]
            loc_parts = []
            for tok in parts[1:]:
                p = _parse_priority(tok)
                if p is not None:
                    priority = p  # overwrite to prevent 'p2 p1' leaking into location
                    continue
                d = _parse_duration_minutes(tok)
                if d is not None:
                    duration_min = d  # overwrite to prevent duplicates leaking into location
                    continue
                loc_parts.append(tok)
            if loc_parts:
                location = ", ".join(loc_parts)
    else:
        title, inferred_location = _infer_location_from_title(title)
        if inferred_location:
            location = inferred_location

    if priority is None:
        priority = 2

    db = load_tasks_db()
    tasks = db["tasks"]
    task_id = _next_id(tasks)

    due_at = None
    if due_date and due_time:
        due_at = f"{due_date}T{due_time}"
    elif due_date:
        due_at = due_date

    task = {
        "id": task_id,
        "title": title if title else "(bez tytułu)",
        "created_at": _now_iso(),
        "due_at": due_at,
        "done": False,
        "tags": [],
        # normalized meta
        "priority": int(priority) if priority is not None else 2,
        "priority_explicit": True if pr_from_title is not None else (True if "," in (rest or "") and re.search(r"\bp[1-3]\b", (raw or ""), re.I) else False),
        "duration_min": int(duration_min) if duration_min is not None else None,
        "location": location,
        "reminder_at": None,
        "reminder_enabled": False,
        "travel_mode": travel,  # None if not set
    }
    tasks.append(task)
    save_tasks_db(db)

    try:
        due_has_time = bool((task.get("time") or "").strip()) or ("T" in str(task.get("due_at") or ""))
        has_location = bool((task.get("location") or task.get("location_text") or task.get("address") or "").strip())
        if due_has_time and has_location:
            set_pending_travel(task_id, created_from="add")
    except Exception:
        pass

    reply = f"✅ Dodane zadanie #{task_id}: {task['title']}"
    if due_at:
        reply += f" (na {due_at.replace('T', ' ')})"
    if travel:
        reply += f" — dojazd: {travel}"
    return {"reply": reply, "task": task}


# --- Sorting utilities (single source of truth) ---

def _parse_time_to_minutes(time_str: str | None) -> int | None:
    if not time_str:
        return None
    try:
        h, m = time_str.split(":")
        return int(h) * 60 + int(m)
    except Exception:
        return None


def _task_time_str(task: Dict[str, Any]) -> str | None:
    # supports both legacy 'time' and ISO 'due_at'
    if task.get("time"):
        return str(task.get("time"))[:5]
    due_at = task.get("due_at")
    if isinstance(due_at, str) and "T" in due_at:
        return due_at.split("T")[1][:5]
    return None


def sort_for_list(tasks: List[Dict[str, Any]], mode: str = "time") -> List[Dict[str, Any]]:
    """Sort tasks for displaying in 'lista' and for live numbering.

    mode:
      - 'time' (default): time axis first; priority only breaks ties within the same time.
      - 'priority': priority first; then time.
    """
    mode = (mode or "time").strip().lower()
    if mode not in {"time", "priority"}:
        mode = "time"

    def key_time_axis(t: Dict[str, Any]):
        time_min = _parse_time_to_minutes(_task_time_str(t))
        has_time = 0 if time_min is not None else 1
        # default priority is 3 (lowest)
        pr = int(t.get("priority") or 3)
        created = str(t.get("created_at") or "")
        # Time axis is sacred: priority never moves across different times.
        return (has_time, time_min if time_min is not None else 9999, pr, created)

    def key_priority_first(t: Dict[str, Any]):
        pr = int(t.get("priority") or 3)
        time_min = _parse_time_to_minutes(_task_time_str(t))
        has_time = 0 if time_min is not None else 1
        created = str(t.get("created_at") or "")
        return (pr, has_time, time_min if time_min is not None else 9999, created)

    return sorted(tasks, key=key_time_axis if mode == "time" else key_priority_first)

# --- End sorting utilities ---
def list_tasks_for_date(d) -> List[Dict[str, Any]]:
    """List tasks for a specific date.

    Accepts 'YYYY-MM-DD' string, datetime.date or datetime.datetime.
    """
    from datetime import date as _date, datetime as _datetime

    if isinstance(d, _datetime):
        d_str = d.date().isoformat()
    elif isinstance(d, _date):
        d_str = d.isoformat()
    else:
        d_str = str(d)

    out: List[Dict[str, Any]] = []
    for t in load_tasks():
        if not isinstance(t, dict):
            continue
        due = str(t.get("due_at") or "")
        if due.startswith(d_str):
            out.append(t)

    def _sort_key(t: Dict[str, Any]):
        due = str(t.get("due_at") or "")
        # For a given date list, due is either 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM'
        has_time = 0 if "T" in due else 1
        time_part = ""
        if "T" in due:
            time_part = due.split("T", 1)[1]
        # Priority: p1 first
        pr = t.get("priority", 2)
        try:
            pr = int(pr)
        except Exception:
            pr = 2
        return (has_time, time_part, pr, int(t.get("id") or 0))
    out.sort(key=_sort_key)
    return out



# --- Pending checklist (attach line-by-line list to a task) ---
def get_pending_checklist() -> Optional[Dict[str, Any]]:
    data = _load_json(PENDING_CHECKLIST_FILE, default=None)
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("task_id"), int):
        return None
    return data

def set_pending_checklist(task_id: int, *, title: str = "Lista") -> None:
    _save_json(PENDING_CHECKLIST_FILE, {"task_id": int(task_id), "title": str(title or "Lista"), "created_at": _now_iso()})

def clear_pending_checklist() -> None:
    if PENDING_CHECKLIST_FILE.exists():
        try:
            PENDING_CHECKLIST_FILE.unlink()
        except Exception:
            _save_json(PENDING_CHECKLIST_FILE, None)

def get_last_task() -> Optional[Dict[str, Any]]:
    db = load_tasks_db()
    tasks = db.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        return None
    # prefer highest numeric id
    ordered = []
    for t in tasks:
        try:
            ordered.append((int(t.get("id") or 0), t))
        except Exception:
            continue
    if not ordered:
        return None
    ordered.sort(key=lambda x: x[0])
    return ordered[-1][1]

def add_checklist_item_to_task(task_id: int, text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip().lstrip("-").strip()
    if not text:
        return None
    db = load_tasks_db()
    for t in db["tasks"]:
        if t.get("id") == task_id:
            cl = t.get("checklist")
            if not isinstance(cl, dict):
                cl = {"title": "Lista", "items": []}
                t["checklist"] = cl
            items = cl.get("items")
            if not isinstance(items, list):
                items = []
                cl["items"] = items
            items.append({"text": text, "done": False})
            save_tasks_db(db)
            return t
    return None

def set_checklist_title(task_id: int, title: str) -> Optional[Dict[str, Any]]:
    title = (title or "").strip().rstrip(":") or "Lista"
    db = load_tasks_db()
    for t in db["tasks"]:
        if t.get("id") == task_id:
            cl = t.get("checklist")
            if not isinstance(cl, dict):
                cl = {"title": title, "items": []}
                t["checklist"] = cl
            cl["title"] = title
            save_tasks_db(db)
            return t
    return None

def toggle_checklist_item(task_id: int, item_no: int, done: bool) -> Optional[Dict[str, Any]]:
    db = load_tasks_db()
    for t in db["tasks"]:
        if t.get("id") == task_id:
            cl = t.get("checklist")
            if not isinstance(cl, dict):
                return None
            items = cl.get("items")
            if not isinstance(items, list) or not (1 <= item_no <= len(items)):
                return None
            it = items[item_no - 1]
            if isinstance(it, dict):
                it["done"] = bool(done)
            else:
                items[item_no - 1] = {"text": str(it), "done": bool(done)}
            save_tasks_db(db)
            return t
    return None

def add_checklist_item_manual(task_id: int, text: str) -> Optional[Dict[str, Any]]:
    return add_checklist_item_to_task(task_id, text)

def remove_checklist_item_manual(task_id: int, text: str) -> Optional[Dict[str, Any]]:
    target = (text or "").strip().lower()
    if not target:
        return None
    db = load_tasks_db()
    for t in db["tasks"]:
        if t.get("id") == task_id:
            cl = t.get("checklist")
            if not isinstance(cl, dict):
                return None
            items = cl.get("items")
            if not isinstance(items, list):
                return None
            new_items = []
            removed = False
            for it in items:
                txt = (it.get("text") if isinstance(it, dict) else str(it) or "").strip()
                if not removed and txt.lower() == target:
                    removed = True
                    continue
                new_items.append(it)
            if removed:
                cl["items"] = new_items
                save_tasks_db(db)
                return t
            return None
    return None



def replace_task_checklist(task_id: int, title: str, items_raw: list[str]) -> Optional[Dict[str, Any]]:
    """Replace whole checklist on a task from a comma-separated command."""
    title = (title or "").strip().rstrip(":") or "Lista"
    cleaned: list[Dict[str, Any]] = []
    for it in (items_raw or []):
        txt = str(it).strip().lstrip("-").strip()
        if txt:
            cleaned.append({"text": txt, "done": False})

    db = load_tasks_db()
    for t in db["tasks"]:
        if t.get("id") == task_id:
            t["checklist"] = {"title": title, "items": cleaned}
            save_tasks_db(db)
            return t
    return None

def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    db = load_tasks_db()
    for t in db["tasks"]:
        if t.get("id") == task_id:
            return t
    return None

def update_task(task_id: int, **fields: Any) -> Optional[Dict[str, Any]]:
    db = load_tasks_db()
    for t in db["tasks"]:
        if t.get("id") == task_id:
            t.update(fields)
            save_tasks_db(db)
            return t
    return None

# --- Pending travel (no conversation_state.json needed) ---
def get_pending_travel() -> Optional[Dict[str, Any]]:
    data = _load_json(PENDING_TRAVEL_FILE, default=None)
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("task_id"), int):
        return None
    return data

def set_pending_travel(task_id: int, *, created_from: str = "rano") -> None:
    _save_json(PENDING_TRAVEL_FILE, {"task_id": task_id, "created_from": created_from, "created_at": _now_iso()})

def clear_pending_travel() -> None:
    if PENDING_TRAVEL_FILE.exists():
        try:
            PENDING_TRAVEL_FILE.unlink()
        except Exception:
            _save_json(PENDING_TRAVEL_FILE, None)


# --- Pending reminder (yes/no) ---
def get_pending_reminder() -> Optional[Dict[str, Any]]:
    data = _load_json(PENDING_REMINDER_FILE, default=None)
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("task_id"), int):
        return None
    if not isinstance(data.get("reminder_at"), str):
        return None
    return data

def set_pending_reminder(task_id: int, reminder_at: str, *, created_from: str = "rano") -> None:
    _save_json(PENDING_REMINDER_FILE, {"task_id": task_id, "reminder_at": reminder_at, "created_from": created_from, "created_at": _now_iso()})

def clear_pending_reminder() -> None:
    if PENDING_REMINDER_FILE.exists():
        try:
            PENDING_REMINDER_FILE.unlink()
        except Exception:
            _save_json(PENDING_REMINDER_FILE, None)


def set_pending_clear(date_iso: str):
    data = {"date": date_iso, "created_at": _now_iso()}
    _atomic_write_json(PENDING_CLEAR_FILE, data)
    return data

def get_pending_clear():
    if not PENDING_CLEAR_FILE.exists():
        return None
    try:
        return _read_json(PENDING_CLEAR_FILE)
    except Exception:
        return None

def clear_pending_clear():
    try:
        if PENDING_CLEAR_FILE.exists():
            PENDING_CLEAR_FILE.unlink()
    except Exception:
        pass

def clear_tasks_for_date(date_iso: str) -> int:
    """Remove all tasks whose due_at starts with YYYY-MM-DD. Returns removed count."""
    db = load_tasks_db()
    tasks_list = db.get("tasks", [])
    before = len(tasks_list)
    remaining = []
    for t in tasks_list:
        due_at = (t.get("due_at") or "").strip()
        if due_at.startswith(date_iso):
            continue
        remaining.append(t)
    db["tasks"] = remaining
    save_tasks_db(db)
    return before - len(remaining)

def parse_yes_no(text: str) -> Optional[bool]:
    low = (text or "").strip().lower()
    yes = {"tak", "t", "ok", "okej", "jasne", "pewnie", "y", "yes"}
    no  = {"nie", "n", "no", "nah", "cancel", "anuluj"}
    if low in yes:
        return True
    if low in no:
        return False
    return None

def set_task_reminder(task_id: int, reminder_at: str, enabled: bool) -> Dict[str, Any]:
    t = update_task(task_id, reminder_at=reminder_at, reminder_enabled=enabled)
    if not t:
        return {"ok": False, "reply": f"Nie znalazłem zadania #{task_id}."}
    if enabled:
        return {"ok": True, "reply": f"⏰ Ustawiłem przypomnienie dla zadania #{task_id} na **{reminder_at}**."}
    return {"ok": True, "reply": f"OK, bez przypomnienia dla zadania #{task_id}."}

def apply_travel_mode_to_task_id(mode: str, task_id: int) -> Dict[str, Any]:
    mode = parse_travel_mode(mode) or mode
    t = update_task(task_id, travel_mode=mode)
    if not t:
        return {"ok": False, "reply": f"Nie znalazłem zadania #{task_id}.", "task_id": task_id}
    return {"ok": True, "reply": f"✅ Ustawiono dojazd dla zadania #{task_id}: {mode}", "task": t}


def apply_travel_mode_to_pending(message: str) -> dict | None:
    """Handle user's transport choice for a previously requested travel-mode decision.

    - If there is no pending travel decision -> return None (router may continue).
    - If there is pending but message is not a recognized choice -> return a short reminder (and DO NOT fall back to LLM).
    """
    pending = get_pending_travel()
    if not pending:
        return None

    msg = (message or "").strip().lower()

    # Allow other commands to pass through even if travel selection is pending.
    if msg in {"lista", "rano", "/ps", "/diag", "/debug on", "/debug off"} or msg.startswith("usuń") or msg.startswith("dodaj"):
        return None

    # Accept both words and numeric shortcuts
    mode_map = {
        "1": "walking",
        "pieszo": "walking",
        "na piechote": "walking",
        "na piechotę": "walking",
        "2": "transit",
        "komunikacja": "transit",
        "tramwaj": "transit",
        "metro": "transit",
        "autobusem": "transit",
        "3": "car",
        "samochodem": "car",
        "auto": "car",
        "samochod": "car",
        "samochód": "car",
    }

    if msg not in mode_map:
        return {"reply": "Wybierz środek transportu: 1) pieszo  2) komunikacja  3) samochód"}

    task_id = pending.get("task_id")
    if not task_id:
        clear_pending_travel()
        return {"reply": "Ups — nie widzę zadania do dojazdu. Wpisz 'rano' i spróbuj ponownie."}

    mode = mode_map[msg]
    ok = apply_travel_mode_to_task_id(mode, task_id)
    clear_pending_travel()

    if not ok:
        return {"reply": "Nie udało się ustawić trybu dojazdu dla tego zadania."}

    human = {"walking": "pieszo", "transit": "komunikacją", "car": "samochodem"}.get(mode, mode)
    return {"reply": f"✅ Ustawiono dojazd: {human}."}



# -----------------------------------------------------------------------------
# Delete tasks (missing in some branches)
# -----------------------------------------------------------------------------

def delete_task_by_id(task_id: int) -> dict:
    """Usuwa zadanie po ID.

    Zwraca dict (ok/reply), żeby router mógł bezpiecznie zrobić out.get('reply').
    """
    try:
        task_id = int(task_id)
    except Exception:
        return {"ok": False, "reply": "Podaj poprawne ID zadania (liczbę)."}

    tasks = [t for t in load_tasks() if isinstance(t, dict)]
    before = len(tasks)
    tasks = [t for t in tasks if int(t.get("id", -1)) != task_id]

    if len(tasks) == before:
        return {"ok": False, "reply": f"Nie znalazłem zadania #{task_id}."}

    save_tasks(tasks)

    # jeśli usuwamy zadanie, które jest w pending travel / reminder → czyścimy
    try:
        pending = get_pending_travel()
        if pending and int(pending.get("task_id", -1)) == task_id:
            clear_pending_travel()
    except Exception:
        pass
    try:
        pr = get_pending_reminder()
        if pr and int(pr.get("task_id", -1)) == task_id:
            clear_pending_reminder()
    except Exception:
        pass

    return {"ok": True, "reply": f"🗑️ Usunięto zadanie #{task_id}."}


def delete_task(task_id: int) -> dict:
    """Alias dla starszych wersji routera."""
    return delete_task_by_id(task_id)


def set_task_transport(task_id: int, transport: str) -> dict:
    """Alias dla starszych wersji routera/testów."""
    return apply_travel_mode_to_task_id(transport, int(task_id))


# Dodatkowe aliasy zgodne z routerem (żeby nie wywalać 500)
def set_reminder(task_id: int, reminder_at: str, enabled: bool = True) -> dict:
    return set_task_reminder(int(task_id), reminder_at, enabled)


def set_transport(task_id: int, transport: str) -> dict:
    return set_task_transport(int(task_id), transport)

