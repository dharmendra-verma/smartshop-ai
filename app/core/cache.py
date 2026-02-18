"""Cache backends for agent results.

Provides two implementations with an identical interface:
- TTLCache: in-memory, zero-dependency (default fallback)
- RedisCache: Redis-backed, JSON-serialized (used when Redis is available)

get_review_cache() auto-selects RedisCache if Redis is reachable, else TTLCache.
"""

import json
import time
import threading
import logging
from typing import Any

logger = logging.getLogger(__name__)


class TTLCache:
    """
    Thread-safe in-memory cache with TTL expiry.

    Used as fallback when Redis is unavailable.
    """

    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
        self._max_size = max_size

    def get(self, key: str) -> Any | None:
        """Return cached value or None if missing/expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store value with TTL. Evicts oldest entry if at max_size."""
        ttl = ttl or self._default_ttl
        expires_at = time.time() + ttl
        with self._lock:
            if len(self._store) >= self._max_size and key not in self._store:
                oldest = min(self._store, key=lambda k: self._store[k][1])
                del self._store[oldest]
            self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        """Remove a key from the cache."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)


class RedisCache:
    """
    Redis-backed cache with JSON serialization.

    Same interface as TTLCache so agent code works unchanged.
    """

    def __init__(self, redis_url: str, default_ttl: int = 3600, key_prefix: str = "smartshop:"):
        import redis as _redis
        self._client = _redis.Redis.from_url(redis_url, decode_responses=True)
        self._default_ttl = default_ttl
        self._key_prefix = key_prefix

    def _prefixed(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    def get(self, key: str) -> Any | None:
        """Return cached value (deserialized from JSON) or None."""
        raw = self._client.get(self._prefixed(key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Cache: corrupt value for key=%s, deleting", key)
            self._client.delete(self._prefixed(key))
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store value as JSON with TTL (seconds)."""
        ttl = ttl or self._default_ttl
        self._client.set(self._prefixed(key), json.dumps(value), ex=ttl)

    def delete(self, key: str) -> None:
        """Remove a key from the cache."""
        self._client.delete(self._prefixed(key))

    def clear(self) -> None:
        """Delete all keys with our prefix. Use with caution in shared Redis."""
        cursor = 0
        pattern = f"{self._key_prefix}*"
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                self._client.delete(*keys)
            if cursor == 0:
                break

    @property
    def size(self) -> int:
        """Count keys with our prefix. Approximate in large databases."""
        count = 0
        cursor = 0
        pattern = f"{self._key_prefix}*"
        while True:
            cursor, keys = self._client.scan(cursor=cursor, match=pattern, count=100)
            count += len(keys)
            if cursor == 0:
                break
        return count


# Module-level singleton — auto-selects Redis or in-memory
_review_cache = None


def get_review_cache() -> TTLCache | RedisCache:
    """Return the shared review cache. Uses Redis if available, else in-memory TTLCache."""
    global _review_cache
    if _review_cache is not None:
        return _review_cache

    from app.core.config import get_settings
    settings = get_settings()

    try:
        cache = RedisCache(
            redis_url=settings.REDIS_URL,
            default_ttl=settings.CACHE_TTL_SECONDS,
            key_prefix="smartshop:",
        )
        # Verify connection
        cache._client.ping()
        _review_cache = cache
        logger.info("Cache: using Redis at %s", settings.REDIS_URL)
    except Exception:
        _review_cache = TTLCache(
            default_ttl=settings.CACHE_TTL_SECONDS,
            max_size=settings.CACHE_MAX_SIZE,
        )
        logger.info("Cache: Redis unavailable, using in-memory TTLCache")

    return _review_cache


def reset_review_cache() -> None:
    """Reset the singleton (useful for testing)."""
    global _review_cache
    _review_cache = None
