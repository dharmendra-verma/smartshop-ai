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
