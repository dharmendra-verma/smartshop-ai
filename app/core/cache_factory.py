"""Shared factory for dual-backend (Redis -> TTLCache) cache singletons."""

import logging
from app.core.cache import RedisCache, TTLCache

logger = logging.getLogger(__name__)


def create_cache(
    redis_url: str,
    key_prefix: str,
    ttl: int,
    max_size: int,
    name: str = "Cache",
):
    """
    Create a cache backend: tries Redis first, falls back to TTLCache.

    Args:
        redis_url:   Redis connection URL from settings
        key_prefix:  Key namespace prefix (e.g. "price:", "session:")
        ttl:         Default TTL in seconds
        max_size:    Max entries for TTLCache fallback
        name:        Human-readable name for log messages

    Returns:
        RedisCache if Redis is reachable, else TTLCache
    """
    try:
        cache = RedisCache(
            redis_url=redis_url,
            default_ttl=ttl,
            key_prefix=key_prefix,
        )
        cache._client.ping()
        logger.info("%s: using Redis", name)
        return cache
    except Exception:
        logger.info("%s: Redis unavailable, using in-memory TTLCache", name)
        return TTLCache(default_ttl=ttl, max_size=max_size)
