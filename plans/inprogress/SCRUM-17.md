# SCRUM-17 — Implement Context Memory & Session Management

## Story
As a user, I want the assistant to remember our conversation so that I can ask follow-up
questions without repeating context.

## Acceptance Criteria
- [ ] Session state management implemented
- [ ] Conversation history stored and retrieved
- [ ] Context window management (token limits — last 10 message pairs)
- [ ] Follow-up queries work correctly (e.g. "Which of these has better reviews?")
- [ ] Session persistence across page reloads (server-side via session_id)
- [ ] Context cleared on user request
- [ ] Memory-efficient storage (Redis primary / TTLCache fallback, 30-min TTL)
- [ ] `DELETE /api/v1/chat/session/{session_id}` endpoint

## Current Test Count
222 (after SCRUM-14). Target after this story: **241** (+19 new tests).

---

## Architecture Overview

```
Streamlit  ──POST /api/v1/chat {session_id}──▶  Orchestrator (SCRUM-16)
               │                                       │
               │                          SessionManager.get_history()
               │                                       │
               │                         build_enriched_query(query, history)
               │                                       │
               │                            agent.process(enriched, ctx)
               │                                       │
               │                          SessionManager.append_turn()
               ◀──────────────────── ChatResponse {session_id, intent, response}

Streamlit  ──DELETE /api/v1/chat/session/{id}──▶  SessionManager.clear(id)
```

### Dual-Backend Session Store (same pattern as PriceCache / SCRUM-14)
- **Redis** (primary): `redis://localhost:6379/0`, key prefix `session:`, TTL 1800s (30 min).
- **TTLCache** (fallback): in-memory, max 200 sessions, same 30-min TTL.
- Module-level singleton `get_session_store()` with `reset_session_store()` for tests.

---

## Tasks

### Task 1 — `app/services/session/__init__.py`
Empty init.

```python
# app/services/session/__init__.py
```

---

### Task 2 — `app/services/session/session_store.py`

Module-level singleton wrapping Redis or TTLCache.

```python
"""Server-side session store — Redis primary, TTLCache fallback."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

SESSION_TTL = 1800  # 30 minutes
SESSION_MAX_MEMORY = 200

_session_store = None


def get_session_store():
    """Return shared session store singleton."""
    global _session_store
    if _session_store is not None:
        return _session_store

    from app.core.config import get_settings
    from app.core.cache import RedisCache, TTLCache

    settings = get_settings()
    try:
        store = RedisCache(
            redis_url=settings.REDIS_URL,
            default_ttl=SESSION_TTL,
            key_prefix="session:",
        )
        store._client.ping()
        _session_store = store
        logger.info("SessionStore: using Redis")
    except Exception:
        _session_store = TTLCache(default_ttl=SESSION_TTL, max_size=SESSION_MAX_MEMORY)
        logger.info("SessionStore: Redis unavailable, using TTLCache")

    return _session_store


def reset_session_store() -> None:
    """Reset singleton (for testing only)."""
    global _session_store
    _session_store = None
```

---

### Task 3 — `app/services/session/session_manager.py`

Business logic layer: sliding window, serialisation, enriched query.

```python
"""Session manager — CRUD for conversation history with sliding context window."""

import json
import logging
import time
from typing import Any
from uuid import uuid4

from app.services.session.session_store import get_session_store

logger = logging.getLogger(__name__)

MAX_PAIRS = 10          # keep last 10 user/assistant turns = 20 messages
CONTEXT_SEPARATOR = "\n"


class ChatMessage:
    """Single chat message stored in session."""
    __slots__ = ("role", "content", "timestamp")

    def __init__(self, role: str, content: str, timestamp: float | None = None):
        self.role = role
        self.content = content
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "content": self.content, "timestamp": self.timestamp}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ChatMessage":
        return cls(role=d["role"], content=d["content"], timestamp=d.get("timestamp", 0.0))


class SessionManager:
    """Manages conversation sessions with a sliding context window."""

    def __init__(self, store=None):
        self._store = store  # injected or lazily resolved

    @property
    def store(self):
        if self._store is None:
            self._store = get_session_store()
        return self._store

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_session(self) -> str:
        """Generate a new session_id and initialise empty history."""
        session_id = str(uuid4())
        self._save_messages(session_id, [])
        return session_id

    def get_history(self, session_id: str) -> list[ChatMessage]:
        """Return the stored message list (possibly empty)."""
        raw = self.store.get(session_id)
        if raw is None:
            return []
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            return [ChatMessage.from_dict(m) for m in data]
        except Exception:
            logger.warning("Failed to parse session %s; returning empty", session_id)
            return []

    def append_turn(self, session_id: str, user_msg: str, assistant_msg: str) -> None:
        """Append one user+assistant turn, enforcing the sliding window."""
        messages = self.get_history(session_id)
        messages.append(ChatMessage("user", user_msg))
        messages.append(ChatMessage("assistant", assistant_msg))

        # Enforce MAX_PAIRS: keep only the last MAX_PAIRS * 2 messages
        if len(messages) > MAX_PAIRS * 2:
            messages = messages[-(MAX_PAIRS * 2):]

        self._save_messages(session_id, messages)

    def clear(self, session_id: str) -> bool:
        """Clear a session. Returns True if it existed."""
        existed = self.store.get(session_id) is not None
        self._save_messages(session_id, [])
        return existed

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _save_messages(self, session_id: str, messages: list[ChatMessage]) -> None:
        payload = json.dumps([m.to_dict() for m in messages])
        self.store.set(session_id, payload)


def build_enriched_query(query: str, history: list[ChatMessage]) -> str:
    """
    Prepend recent conversation history to the current query so the agent
    has context for follow-up questions.

    Format:
        [CONVERSATION HISTORY]
        user: ...
        assistant: ...
        ...
        [CURRENT QUERY]
        user: <query>
    """
    if not history:
        return query

    lines = ["[CONVERSATION HISTORY]"]
    for msg in history:
        lines.append(f"{msg.role}: {msg.content}")
    lines.append("[CURRENT QUERY]")
    lines.append(f"user: {query}")
    return CONTEXT_SEPARATOR.join(lines)


# Module-level singleton (for use inside API routes)
_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager


def reset_session_manager() -> None:
    """Reset singleton (for testing)."""
    global _manager
    _manager = None
```

---

### Task 4 — Update `app/schemas/chat.py` (SCRUM-16 file)

SCRUM-16 defines `ChatRequest` / `ChatResponse`. Add `session_id` fields if not
already present:

```python
# Add to ChatRequest
session_id: str | None = None   # omit → backend creates a new session

# Add to ChatResponse (already likely present from SCRUM-16)
session_id: str                 # always returned so client can persist it
```

---

### Task 5 — Update `app/api/v1/chat.py` (SCRUM-16 file)

Wire `SessionManager` into the chat endpoint:

```python
from app.services.session.session_manager import get_session_manager, build_enriched_query
from app.services.session.session_store import get_session_store

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    manager = get_session_manager()

    # Resolve or create session
    session_id = request.session_id or manager.create_session()

    # Retrieve history and build enriched query
    history = manager.get_history(session_id)
    enriched_query = build_enriched_query(request.message, history)

    # Orchestrate (SCRUM-16)
    deps = AgentDependencies.from_db(db)
    context = {"deps": deps, "max_results": request.max_results or 5}
    agent_response, intent_result = await _orchestrator.handle(enriched_query, context)

    if not agent_response.success:
        raise HTTPException(status_code=500, detail=agent_response.error)

    # Persist turn (store original user query, not enriched)
    answer = agent_response.data.get("answer") or str(agent_response.data)
    manager.append_turn(session_id, request.message, answer)

    return ChatResponse(
        session_id=session_id,
        intent=intent_result.intent.value,
        response=agent_response.data,
        success=True,
    )


@router.delete("/session/{session_id}", status_code=204)
async def clear_session(session_id: str):
    """Clear conversation history for a session."""
    manager = get_session_manager()
    manager.clear(session_id)
    # Return 204 regardless — idempotent
```

---

### Task 6 — Update `app/main.py`

No new imports needed; startup event can pre-warm session store:

```python
@app.on_event("startup")
async def startup_event():
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    # Pre-warm session store (establishes Redis connection early)
    from app.services.session.session_store import get_session_store
    get_session_store()
    logger.info("Docs: http://%s:%s/docs", settings.API_HOST, settings.API_PORT)
```

---

### Task 7 — Update Streamlit `streamlit_app.py`

Session-ID initialisation and clear conversation button:

```python
# At top of AI Chat Assistant page block
import uuid

# Initialise persistent session_id (survives page rerenders, NOT browser refresh — use st.query_params for that)
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())

# In sidebar, under Settings
st.divider()
if st.button("🗑️ Clear Conversation", use_container_width=True):
    clear_session_result = _post(f"{api_url}/api/v1/chat/session/{st.session_state['session_id']}", {})
    st.session_state["messages"] = [...]   # reset to initial welcome message
    st.session_state["session_id"] = str(uuid.uuid4())  # fresh session
    st.rerun()

# In chat call (replaces raw message with session_id included):
result = chat_api(api_url,
                  message=prompt,
                  session_id=st.session_state["session_id"],
                  max_results=5)

# Persist session_id returned by server (in case backend rotated it)
if result["success"] and result["data"].get("session_id"):
    st.session_state["session_id"] = result["data"]["session_id"]
```

`chat_api()` in `api_client.py` already has `session_id` parameter (added in SCRUM-16).
Ensure it passes it through:

```python
def chat_api(base_url: str, message: str, session_id: str | None = None,
             max_results: int = 5) -> dict[str, Any]:
    payload = {"message": message, "max_results": max_results}
    if session_id:
        payload["session_id"] = session_id
    return _post(f"{base_url}/api/v1/chat", payload)
```

---

### Task 8 — Tests (19 new tests, target 241)

#### `tests/test_services/test_session_manager.py` — 12 tests

```
test_create_session_returns_uuid_string
test_get_history_empty_for_new_session
test_append_turn_stores_user_and_assistant
test_sliding_window_trims_to_max_pairs
test_clear_session_empties_history
test_clear_returns_true_when_existed
test_clear_returns_false_when_not_existed
test_build_enriched_query_empty_history_returns_query
test_build_enriched_query_with_history_prepends_context
test_get_history_handles_corrupt_json_gracefully
test_append_multiple_turns_ordering_correct
test_session_ttl_refreshed_on_append   # store.set called with same key again
```

Pattern:
```python
import pytest
from unittest.mock import MagicMock, patch
from app.services.session.session_manager import (
    SessionManager, ChatMessage, build_enriched_query,
    get_session_manager, reset_session_manager,
)

@pytest.fixture(autouse=True)
def reset_singleton():
    reset_session_manager()
    yield
    reset_session_manager()

def make_manager():
    mock_store = MagicMock()
    mock_store.get.return_value = None
    return SessionManager(store=mock_store)

def test_create_session_returns_uuid_string():
    mgr = make_manager()
    sid = mgr.create_session()
    assert isinstance(sid, str) and len(sid) == 36

def test_sliding_window_trims_to_max_pairs():
    """After 11 pairs appended, only 10 pairs (20 msgs) remain."""
    mock_store = MagicMock()
    saved = []
    mock_store.get.side_effect = lambda k: saved[-1] if saved else None
    mock_store.set.side_effect = lambda k, v: saved.append(v)
    mgr = SessionManager(store=mock_store)
    sid = "test-session"
    for i in range(11):
        mgr.append_turn(sid, f"user {i}", f"asst {i}")
    import json
    final = json.loads(saved[-1])
    assert len(final) == 20  # 10 pairs * 2

def test_build_enriched_query_with_history_prepends_context():
    history = [
        ChatMessage("user", "Show me laptops"),
        ChatMessage("assistant", "Here are 5 laptops..."),
    ]
    result = build_enriched_query("Which is cheapest?", history)
    assert "[CONVERSATION HISTORY]" in result
    assert "user: Show me laptops" in result
    assert "[CURRENT QUERY]" in result
    assert "user: Which is cheapest?" in result
```

#### `tests/test_api/test_chat.py` — 7 tests (extending SCRUM-16 file)

```
test_chat_creates_session_when_none_provided       # response has session_id
test_chat_reuses_existing_session_id               # returns same session_id back
test_chat_enriches_query_with_history              # mock orchestrator sees enriched query
test_clear_session_returns_204                     # DELETE /api/v1/chat/session/{id}
test_clear_session_idempotent_on_missing_id        # 204 even if unknown
test_chat_endpoint_integration_with_session_store  # real TTLCache store
test_chat_history_grows_then_clears                # full round-trip
```

---

## File Map

| File | Action |
|------|--------|
| `app/services/session/__init__.py` | CREATE |
| `app/services/session/session_store.py` | CREATE |
| `app/services/session/session_manager.py` | CREATE |
| `app/schemas/chat.py` | MODIFY — add `session_id` fields |
| `app/api/v1/chat.py` | MODIFY — wire SessionManager |
| `app/main.py` | MODIFY — pre-warm session store on startup |
| `app/ui/streamlit_app.py` | MODIFY — session_id init + clear button |
| `app/ui/api_client.py` | MODIFY — pass session_id in `chat_api()` |
| `tests/test_services/test_session_manager.py` | CREATE |
| `tests/test_api/test_chat.py` | CREATE / EXTEND |

---

## Dependencies

- **SCRUM-16 must be merged first** — this story extends `POST /api/v1/chat` and
  `ChatRequest` / `ChatResponse` schemas introduced there.
- `app.core.cache.RedisCache` and `TTLCache` must be available (established in SCRUM-14).
- No new pip packages required.

---

## Test Count Verification

| Layer | New Tests |
|-------|----------|
| `test_session_manager.py` | 12 |
| `test_chat.py` (session additions) | 7 |
| **Total new** | **19** |
| **Cumulative** | **241** |
