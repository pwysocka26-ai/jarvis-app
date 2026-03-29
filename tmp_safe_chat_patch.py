from pathlib import Path
import re
import sys

p = Path("app/api/chat.py")
text = p.read_text(encoding="utf-8")

if "_LAST_CHAT_TASK_ID" in text:
    print("OK: patch już jest w app/api/chat.py")
    sys.exit(0)

# Dodaj modułowy kontekst ostatniego zadania
marker_import = "from app.schemas.chat import ChatRequest, ChatResponse"
if marker_import not in text:
    print("ERROR: nie znalazłem importu ChatRequest/ChatResponse")
    sys.exit(1)

text = text.replace(
    marker_import,
    marker_import + "\n\n_LAST_CHAT_TASK_ID = None\n",
    1,
)

# Znajdź linię wywołania handle_chat(req.message, mode=req.mode)
m = re.search(r'^(?P<indent>\s*)out\s*=\s*handle_chat\(req\.message,\s*mode=req\.mode\)\s*$', text, flags=re.M)
if not m:
    print("ERROR: nie znalazłem linii 'out = handle_chat(req.message, mode=req.mode)'")
    sys.exit(1)

indent = m.group("indent")

block = f"""
{indent}global _LAST_CHAT_TASK_ID
{indent}msg = req.message.strip()
{indent}low = msg.lower()

{indent}# Naturalne follow-upy oparte o kontekst ostatniego zadania
{indent}if low in ("pokaż listę", "pokaz liste", "lista", "pokaż listę zadań", "pokaz liste zadan", "pokaż zadania", "pokaz zadania"):
{indent}    msg = "lista"
{indent}elif _LAST_CHAT_TASK_ID is not None and low in (
{indent}    "ustaw to jako ważne",
{indent}    "ustaw to jako wazne",
{indent}    "oznacz to jako ważne",
{indent}    "oznacz to jako wazne",
{indent}    "zrób to ważnym",
{indent}    "zrob to waznym",
{indent}    "to jest ważne",
{indent}    "to jest wazne",
{indent}    "ważne",
{indent}    "wazne",
{indent}):
{indent}    msg = f"priorytet {{_LAST_CHAT_TASK_ID}} p2"
{indent}elif _LAST_CHAT_TASK_ID is not None and low in (
{indent}    "ustaw to jako pilne",
{indent}    "oznacz to jako pilne",
{indent}    "pilne",
{indent}):
{indent}    msg = f"priorytet {{_LAST_CHAT_TASK_ID}} p1"
{indent}elif _LAST_CHAT_TASK_ID is not None and low in (
{indent}    "usuń to ostatnie",
{indent}    "usun to ostatnie",
{indent}    "usuń ostatnie",
{indent}    "usun ostatnie",
{indent}    "usuń to",
{indent}    "usun to",
{indent}):
{indent}    msg = f"usuń {{_LAST_CHAT_TASK_ID}}"
{indent}else:
{indent}    # Naturalne dodawanie zadań
{indent}    natural_add_prefixes = (
{indent}        "muszę ",
{indent}        "musze ",
{indent}        "mam kupić ",
{indent}        "mam kupic ",
{indent}        "trzeba ",
{indent}        "potrzebuję ",
{indent}        "potrzebuje ",
{indent}        "kup ",
{indent}        "kupić ",
{indent}        "kupic ",
{indent}        "dodaj zadanie ",
{indent}    )
{indent}    if low.startswith(natural_add_prefixes) and not low.startswith(("dodaj:", "dodaj ")):
{indent}        cleaned = msg
{indent}        for pref in ("muszę ", "musze ", "mam kupić ", "mam kupic ", "trzeba ", "potrzebuję ", "potrzebuje "):
{indent}            if cleaned.lower().startswith(pref):
{indent}                cleaned = cleaned[len(pref):].strip()
{indent}                break
{indent}        if cleaned.lower().startswith("kupić "):
{indent}            cleaned = cleaned[6:].strip()
{indent}        elif cleaned.lower().startswith("kupic "):
{indent}            cleaned = cleaned[6:].strip()
{indent}        elif cleaned.lower().startswith("kup "):
{indent}            cleaned = cleaned[4:].strip()
{indent}        elif cleaned.lower().startswith("dodaj zadanie "):
{indent}            cleaned = cleaned[14:].strip()
{indent}
{indent}        if cleaned:
{indent}            msg = "dodaj: " + cleaned
{indent}
{indent}out = handle_chat(msg, mode=req.mode)
"""

start, end = m.span()
text = text[:start] + block + text[end:]

# Po wywołaniu handle_chat zapamiętaj ID ostatnio dodanego taska
m2 = re.search(r'^(?P<indent>\s*)intent\s*=\s*out\.get\("intent"\)\s*if\s*isinstance\(out,\s*dict\)\s*else\s*None\s*$', text, flags=re.M)
if not m2:
    print("ERROR: nie znalazłem linii z intent = out.get(...)")
    sys.exit(1)

indent2 = m2.group("indent")

remember_block = f"""
{indent2}intent = out.get("intent") if isinstance(out, dict) else None
{indent2}reply = out.get("reply", "") if isinstance(out, dict) else ""
{indent2}if intent == "add_task":
{indent2}    m_task = re.search(r"#(\\d+)", str(reply))
{indent2}    if m_task:
{indent2}        _LAST_CHAT_TASK_ID = int(m_task.group(1))
"""

line2 = m2.group(0)
text = text.replace(line2, remember_block.strip("\n"), 1)

p.write_text(text, encoding="utf-8")
print("OK: patch naturalnego chatu dodany poprawnie")
