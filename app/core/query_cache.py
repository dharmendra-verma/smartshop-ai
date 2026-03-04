"""Query-level fallback cache for agent responses."""

import hashlib
import time
import logging

logger = logging.getLogger(__name__)

_query_cache: dict[str, tuple[dict, float]] = {}
_QUERY_CACHE_TTL = 86400  # 24 hours


def _make_key(agent: str, query: str) -> str:
    normalized = query.strip().lower()
    return f"{agent}:{hashlib.sha256(normalized.encode()).hexdigest()[:16]}"


def get_cached_response(agent: str, query: str) -> dict | None:
    """Return cached response dict if available and not expired, else None."""
    key = _make_key(agent, query)
    entry = _query_cache.get(key)
    if entry is None:
        return None
    data, expires_at = entry
    if time.time() > expires_at:
        del _query_cache[key]
        return None
    logger.debug("QueryCache HIT: agent=%s query='%s...'", agent, query[:40])
    result = dict(data)
    result["from_cache"] = True
    result["cache_warning"] = "Live data unavailable — showing cached result."
    return result


def cache_response(agent: str, query: str, data: dict) -> None:
    """Store a successful agent response in the fallback cache."""
    key = _make_key(agent, query)
    _query_cache[key] = (dict(data), time.time() + _QUERY_CACHE_TTL)
    logger.debug("QueryCache SET: agent=%s", agent)


def reset_query_cache() -> None:
    """Clear the cache (for tests)."""
    _query_cache.clear()
