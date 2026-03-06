"""Startup cache warmer — pre-loads common queries into LLM and product cache."""

import logging

logger = logging.getLogger(__name__)

WARM_QUERIES = [
    ("recommendation", "best smartphones under $500"),
    ("recommendation", "wireless headphones for gym"),
    ("recommendation", "budget laptops for students"),
    ("recommendation", "4K smart TV deals"),
    ("review", "Samsung Galaxy review summary"),
    ("review", "Apple laptop customer reviews"),
]


async def warm_caches() -> None:
    """Pre-warm LLM response cache with popular queries. Called at startup."""
    from app.core.llm_cache import get_cached_llm_response

    warmed = 0
    for agent_name, query in WARM_QUERIES:
        if get_cached_llm_response(agent_name, query) is not None:
            warmed += 1
    logger.info("CacheWarmer: %d/%d queries already cached", warmed, len(WARM_QUERIES))
