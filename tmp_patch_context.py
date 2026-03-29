from pathlib import Path
import sys

p = Path("app/api/chat.py")
text = p.read_text(encoding="utf-8")

if "_LAST_CHAT_TASK_ID = None" in text:
    print("INFO: patch już był dodany")
    sys.exit(0)

anchor_import = "from app.schemas.chat import ChatRequest, ChatResponse"
if anchor_import not in text:
    print("ERROR: nie znalazłem importu schematu czatu")
    sys.exit(1)

text = text.replace(
    anchor_import,
    anchor_import + "\n\n_LAST_CHAT_TASK_ID = None\n",
    1
)

old_block = """    out = handle_chat(req.message, mode=req.mode)
    intent = out.get("intent") if isinstance(out, dict) else None
    reply = out.get("reply", "") if isinstance(out, dict) else ""
"""

new_block = """    global _LAST_CHAT_TASK_ID

    user_text = req.message.strip()
    low = user_text.lower()
    normalized = user_text

    if low.startswith("muszę "):
        normalized = "dodaj: " + user_text[6:].strip()
    elif low.startswith("musze "):
        normalized = "dodaj: " + user_text[6:].strip()
    elif low.startswith("mam kupić "):
        normalized = "dodaj: " + user_text[10:].strip()
    elif low.startswith("mam kupic "):
        normalized = "dodaj: " + user_text[10:].strip()
    elif low.startswith("kupić "):
        normalized = "dodaj: " + user_text[6:].strip()
    elif low.startswith("kupic "):
        normalized = "dodaj: " + user_text[6:].strip()
    elif low in ("pokaż listę", "pokaz liste", "pokaż listę zadań", "pokaz liste zadan", "lista"):
        normalized = "lista"
    elif _LAST_CHAT_TASK_ID is not None and low in (
        "ustaw to jako ważne",
        "ustaw to jako wazne",
        "oznacz to jako ważne",
        "oznacz to jako wazne",
        "ważne",
        "wazne",
    ):
        normalized = f"priorytet {_LAST_CHAT_TASK_ID} p2"
    elif _LAST_CHAT_TASK_ID is not None and low in (
        "ustaw to jako pilne",
        "oznacz to jako pilne",
        "pilne",
    ):
        normalized = f"priorytet {_LAST_CHAT_TASK_ID} p1"
    elif _LAST_CHAT_TASK_ID is not None and low in (
        "usuń to ostatnie",
        "usun to ostatnie",
        "usuń to",
        "usun to",
        "usuń ostatnie",
        "usun ostatnie",
    ):
        normalized = f"usuń {_LAST_CHAT_TASK_ID}"

    out = handle_chat(normalized, mode=req.mode)
    intent = out.get("intent") if isinstance(out, dict) else None
    reply = out.get("reply", "") if isinstance(out, dict) else ""

    if intent == "add_task":
        import re
        m = re.search(r"#(\\d+)", str(reply))
        if m:
            _LAST_CHAT_TASK_ID = int(m.group(1))
"""

if old_block not in text:
    print("ERROR: nie znalazłem dokładnego miejsca podmiany")
    sys.exit(1)

text = text.replace(old_block, new_block, 1)
p.write_text(text, encoding="utf-8")
print("OK: patch zapisany")
