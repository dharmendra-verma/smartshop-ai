"""Module-level price cache singleton — Redis or in-memory TTLCache."""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_price_cache = None


def get_price_cache():
    """Return the shared price cache. Uses Redis if available, else in-memory TTLCache."""
    global _price_cache
    if _price_cache is not None:
        return _price_cache

    from app.core.config import get_settings
    from app.core.cache import RedisCache, TTLCache

    settings = get_settings()
    try:
        cache = RedisCache(
            redis_url=settings.REDIS_URL,
            default_ttl=3600,  # 1-hour TTL for prices
            key_prefix="price:",
        )
        cache._client.ping()
        _price_cache = cache
        logger.info("PriceCache: using Redis")
    except Exception:
        _price_cache = TTLCache(default_ttl=3600, max_size=500)
        logger.info("PriceCache: Redis unavailable, using in-memory TTLCache")

    return _price_cache


def reset_price_cache() -> None:
    """Reset singleton (for testing)."""
    global _price_cache
    _price_cache = None
