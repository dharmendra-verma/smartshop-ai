"""Server-side session store — Redis primary, TTLCache fallback."""

import logging

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
    from app.core.cache_factory import create_cache

    settings = get_settings()
    _session_store = create_cache(
        redis_url=settings.REDIS_URL,
        key_prefix="session:",
        ttl=SESSION_TTL,
        max_size=SESSION_MAX_MEMORY,
        name="SessionStore",
    )
    return _session_store


def reset_session_store() -> None:
    """Reset singleton (for testing only)."""
    global _session_store
    _session_store = None
