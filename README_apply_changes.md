# Jarvis - gotowe pliki do podmiany

## Pliki
- `chat.py` -> wstaw do `app/api/chat.py`
- `test_chat_mvp_flow.py` -> wstaw do `tests/test_chat_mvp_flow.py`

## Co naprawia nowy `chat.py`
- `zrób to jutro` nie wywołuje już `handle_chat("ustaw date ...")`
- `usuń ostatnie` usuwa po stabilnym ID, a nie przez niejednoznaczne `usuń N`
- `_LAST_CHAT_TASK_ID` aktualizuje się po dodaniu zadania na podstawie najnowszego taska w store

## Minimalne kroki wdrożenia
1. Skopiuj `chat.py` do `app/api/chat.py`
2. Skopiuj `test_chat_mvp_flow.py` do `tests/test_chat_mvp_flow.py`
3. Zrestartuj backend:
   `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`
4. Przetestuj kolejno:
   - `muszę kupić mleko`
   - `zrób to jutro`
   - `co mam jutro`
   - `usuń ostatnie`

## Commit
```bash
git checkout integrate/new-life-sync
git add app/api/chat.py tests/test_chat_mvp_flow.py
git commit -m "Make MVP chat commands deterministic"
git push origin integrate/new-life-sync
```
