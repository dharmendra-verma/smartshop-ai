"""Module-level price cache singleton — Redis or in-memory TTLCache."""

import logging

logger = logging.getLogger(__name__)

_price_cache = None


def get_price_cache():
    """Return the shared price cache. Uses Redis if available, else in-memory TTLCache."""
    global _price_cache
    if _price_cache is not None:
        return _price_cache

    from app.core.config import get_settings
    from app.core.cache_factory import create_cache

    settings = get_settings()
    _price_cache = create_cache(
        redis_url=settings.REDIS_URL,
        key_prefix="price:",
        ttl=3600,
        max_size=500,
        name="PriceCache",
    )
    return _price_cache


def reset_price_cache() -> None:
    """Reset singleton (for testing)."""
    global _price_cache
    _price_cache = None
