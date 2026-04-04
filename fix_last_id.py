from pathlib import Path
import re

p = Path("app/api/chat.py")
text = p.read_text(encoding="utf-8")

old = """if isinstance(reply, str):
        m = re.search(r"#(\\d+)", reply)
        if m:
            _LAST_CHAT_TASK_ID = int(m.group(1))"""

new = """if isinstance(reply, str):
        m = re.search(r"#(\\d+)", reply)
        if m:
            globals()['_LAST_CHAT_TASK_ID'] = int(m.group(1))"""

if old not in text:
    print("❌ Nie znalazłem bloku do podmiany")
    exit()

text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")

print("✅ Naprawiono zapisywanie LAST_CHAT_TASK_ID")
