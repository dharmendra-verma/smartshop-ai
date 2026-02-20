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
