"""LLM response cache — 24h TTL for identical agent queries."""

import hashlib
import logging

from app.agents.base import AgentResponse

logger = logging.getLogger(__name__)

_LLM_CACHE_TTL = 86400  # 24 hours

_llm_cache = None


def get_llm_cache():
    global _llm_cache
    if _llm_cache is not None:
        return _llm_cache
    from app.core.config import get_settings
    from app.core.cache import RedisCache, TTLCache

    settings = get_settings()
    try:
        cache = RedisCache(
            settings.REDIS_URL, default_ttl=_LLM_CACHE_TTL, key_prefix="llm:"
        )
        cache._client.ping()
        _llm_cache = cache
        logger.info("LLMCache: using Redis")
    except Exception:
        _llm_cache = TTLCache(default_ttl=_LLM_CACHE_TTL, max_size=500)
        logger.info("LLMCache: using in-memory TTLCache")
    return _llm_cache


def reset_llm_cache():
    global _llm_cache
    if _llm_cache is not None:
        try:
            _llm_cache.clear()
        except Exception:
            pass
    _llm_cache = None


def _cache_key(agent_name: str, query: str) -> str:
    normalized = query.strip().lower()
    return f"{agent_name}:{hashlib.sha256(normalized.encode()).hexdigest()[:16]}"


def get_cached_llm_response(agent_name: str, query: str) -> AgentResponse | None:
    cached = get_llm_cache().get(_cache_key(agent_name, query))
    if cached:
        logger.debug("LLMCache HIT: agent=%s query='%s...'", agent_name, query[:40])
        cached["metadata"] = cached.get("metadata", {})
        cached["metadata"]["from_llm_cache"] = True
        return AgentResponse(**cached)
    return None


def set_cached_llm_response(
    agent_name: str, query: str, response: AgentResponse
) -> None:
    if response.success:
        get_llm_cache().set(_cache_key(agent_name, query), response.model_dump())
        logger.debug("LLMCache SET: agent=%s", agent_name)
