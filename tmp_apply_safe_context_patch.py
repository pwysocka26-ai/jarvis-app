from pathlib import Path
import sys

p = Path("app/api/chat.py")
text = p.read_text(encoding="utf-8")

if "_LAST_CHAT_TASK_ID = None" in text:
    print("OK: patch już istnieje")
    sys.exit(0)

marker1 = 'from app.schemas.chat import ChatRequest, ChatResponse'
if marker1 not in text:
    print("ERROR: nie znalazłem importu ChatRequest/ChatResponse")
    sys.exit(1)

text = text.replace(
    marker1,
    marker1 + '\n\n_LAST_CHAT_TASK_ID = None\n',
    1
)

old = '''    out = handle_chat(req.message, mode=req.mode)
    intent = out.get("intent") if isinstance(out, dict) else None
    reply = out.get("reply", "") if isinstance(out, dict) else ""
'''

new = '''    global _LAST_CHAT_TASK_ID

    raw_msg = req.message.strip()
    low = raw_msg.lower()
    effective_msg = raw_msg

    # naturalne dodawanie zadań
    natural_prefixes = (
        "muszę ",
        "musze ",
        "mam kupić ",
        "mam kupic ",
        "trzeba ",
        "potrzebuję ",
        "potrzebuje ",
        "kup ",
        "kupić ",
        "kupic ",
    )

    if low.startswith(natural_prefixes):
        item = raw_msg
        for pref in ("muszę ", "musze ", "mam kupić ", "mam kupic ", "trzeba ", "potrzebuję ", "potrzebuje "):
            if item.lower().startswith(pref):
                item = item[len(pref):].strip()
                break

        if item.lower().startswith("kupić "):
            item = item[6:].strip()
        elif item.lower().startswith("kupic "):
            item = item[6:].strip()
        elif item.lower().startswith("kup "):
            item = item[4:].strip()

        if item:
            effective_msg = f"dodaj: {item}"

    # naturalne follow-upy na ostatnim zadaniu
    elif _LAST_CHAT_TASK_ID is not None and low in (
        "ustaw to jako ważne",
        "ustaw to jako wazne",
        "oznacz to jako ważne",
        "oznacz to jako wazne",
        "to jest ważne",
        "to jest wazne",
        "ważne",
        "wazne",
    ):
        effective_msg = f"priorytet {_LAST_CHAT_TASK_ID} p2"

    elif _LAST_CHAT_TASK_ID is not None and low in (
        "ustaw to jako pilne",
        "oznacz to jako pilne",
        "pilne",
    ):
        effective_msg = f"priorytet {_LAST_CHAT_TASK_ID} p1"

    elif _LAST_CHAT_TASK_ID is not None and low in (
        "usuń to ostatnie",
        "usun to ostatnie",
        "usuń to",
        "usun to",
        "usuń ostatnie",
        "usun ostatnie",
    ):
        effective_msg = f"usuń {_LAST_CHAT_TASK_ID}"

    elif low in (
        "pokaż listę",
        "pokaz liste",
        "pokaż listę zadań",
        "pokaz liste zadan",
        "pokaż zadania",
        "pokaz zadania",
        "lista",
    ):
        effective_msg = "lista"

    out = handle_chat(effective_msg, mode=req.mode)
    intent = out.get("intent") if isinstance(out, dict) else None
    reply = out.get("reply", "") if isinstance(out, dict) else ""

    if intent == "add_task":
        import re
        m = re.search(r"#(\\d+)", str(reply))
        if m:
            _LAST_CHAT_TASK_ID = int(m.group(1))
'''

if old not in text:
    print("ERROR: nie znalazłem stabilnego fragmentu do podmiany")
    sys.exit(1)

text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
print("OK: patch wgrany")
