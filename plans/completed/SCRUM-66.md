# SCRUM-66 — Eliminate code duplication — DRY refactor for agents, caches, and query filters

**Jira:** https://projecttracking.atlassian.net/browse/SCRUM-66
**Status:** In Progress
**Priority:** Medium
**Assignee:** Dharmendra Verma

---

## Problem

Four DRY violations create maintenance burden and inconsistency risk. This is a **pure refactor** — no behaviour changes, no new features. All 460 existing passing tests must continue to pass.

| Duplication | Files Affected | Lines |
|---|---|---|
| Agent error handling (identical try/except block) | 4 agent files | ~20 lines each × 4 |
| Cache factory (identical Redis→TTLCache pattern) | 4 cache files | ~18 lines each × 4 |
| Product filter logic (applied twice in same endpoint) | `products.py` | lines 44–64 |
| `_build_enriched_query` concept in 2 agents | `recommendation/agent.py`, `review/agent.py` | different signatures — see notes |

---

## Acceptance Criteria

- [ ] Agent error handling extracted to `BaseAgent._handle_agent_error()` — all 4 agents use it
- [ ] Cache factory function created in `app/core/cache_factory.py` — all 4 cache singletons use it
- [ ] Product filter logic extracted to `_apply_product_filters()` helper in `products.py`
- [ ] `_build_enriched_query` functions moved to `app/agents/utils.py`
- [ ] All 460 existing tests pass — zero behaviour change
- [ ] No new public API or endpoint changes

---

## Technical Approach

### Refactor 1 — `app/agents/base.py`: Add `_handle_agent_error()`

The identical error-handling block in all 4 agents:
```python
# Currently in recommendation/agent.py, review/agent.py, price/agent.py, policy/agent.py
except Exception as exc:
    exc_type = type(exc).__name__
    if "RateLimitError" in exc_type:
        record_failure(self.name)
        raise AgentRateLimitError(...)
    if "Timeout" in exc_type:
        record_failure(self.name)
        raise AgentTimeoutError(...)
    logger.error("... failed: %s", exc, exc_info=True)
    record_failure(self.name)
    return AgentResponse(success=False, data={}, error="Service temporarily unavailable.")
```

**Add to `BaseAgent` in `app/agents/base.py`:**

```python
def _handle_agent_error(self, exc: Exception, query: str = "") -> AgentResponse:
    """
    Shared error handler for all agents.
    - RateLimitError → record_failure + raise AgentRateLimitError
    - Timeout        → record_failure + raise AgentTimeoutError
    - Anything else  → log + record_failure + return failure AgentResponse
    """
    from app.core.exceptions import AgentRateLimitError, AgentTimeoutError
    from app.core.alerting import record_failure

    exc_type = type(exc).__name__
    if "RateLimitError" in exc_type:
        record_failure(self.name)
        raise AgentRateLimitError(
            f"OpenAI rate limit: {exc}",
            user_message="I'm experiencing high demand. Please try again in a moment.",
            context={"agent": self.name, "query": query[:100]},
        ) from exc
    if "Timeout" in exc_type:
        record_failure(self.name)
        raise AgentTimeoutError(
            f"OpenAI timeout: {exc}",
            user_message="The AI assistant is taking too long. Please try again.",
            context={"agent": self.name},
        ) from exc
    logger.error("%s failed: %s", self.name, exc, exc_info=True)
    record_failure(self.name)
    return AgentResponse(
        success=False,
        data={},
        error="Service temporarily unavailable.",
    )
```

**Then in each agent, replace the except block with:**

```python
except Exception as exc:
    return self._handle_agent_error(exc, query=query)
```

**Files to update:** `app/agents/recommendation/agent.py`, `app/agents/review/agent.py`,
`app/agents/price/agent.py`, `app/agents/policy/agent.py`

---

### Refactor 2 — New file `app/core/cache_factory.py`: Shared Redis→TTLCache factory

**Create `app/core/cache_factory.py`:**

```python
"""Shared factory for dual-backend (Redis → TTLCache) cache singletons."""

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
```

**Then refactor each cache singleton to use it:**

```python
# app/core/llm_cache.py  — get_llm_cache()
from app.core.cache_factory import create_cache

def get_llm_cache():
    global _llm_cache
    if _llm_cache is not None:
        return _llm_cache
    from app.core.config import get_settings
    settings = get_settings()
    _llm_cache = create_cache(
        redis_url=settings.REDIS_URL,
        key_prefix="llm:",
        ttl=_LLM_CACHE_TTL,
        max_size=500,
        name="LLMCache",
    )
    return _llm_cache

# app/core/cache.py  — get_review_cache()
_review_cache = create_cache(
    redis_url=settings.REDIS_URL,
    key_prefix="smartshop:",
    ttl=settings.CACHE_TTL_SECONDS,
    max_size=settings.CACHE_MAX_SIZE,
    name="ReviewCache",
)

# app/services/pricing/price_cache.py  — get_price_cache()
_price_cache = create_cache(
    redis_url=settings.REDIS_URL,
    key_prefix="price:",
    ttl=3600,
    max_size=500,
    name="PriceCache",
)

# app/services/session/session_store.py  — get_session_store()
_session_store = create_cache(
    redis_url=settings.REDIS_URL,
    key_prefix="session:",
    ttl=SESSION_TTL,
    max_size=SESSION_MAX_MEMORY,
    name="SessionStore",
)
```

---

### Refactor 3 — `app/api/v1/products.py`: Extract `_apply_product_filters()`

**Current state** — filters applied twice (main query lines 44–52, count query lines 56–64):

```python
# Currently duplicated
if category:
    query = query.filter(Product.category.ilike(f"%{category}%"))
if brand:
    query = query.filter(or_(
        Product.brand.ilike(f"%{brand}%"),
        Product.name.ilike(f"%{brand}%"),
    ))
```

**Extract helper at module level:**

```python
from sqlalchemy import or_

def _apply_product_filters(query, category: str | None, brand: str | None):
    """Apply category and brand filters to any SQLAlchemy product query."""
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if brand:
        query = query.filter(
            or_(
                Product.brand.ilike(f"%{brand}%"),
                Product.name.ilike(f"%{brand}%"),
            )
        )
    return query
```

**Then in `list_products()`:**

```python
query = _apply_product_filters(query, category, brand)
count_query = _apply_product_filters(count_query, category, brand)
total = count_query.count()
```

Also remove the `from sqlalchemy import or_` inside the function body — it moves to module level.

---

### Refactor 4 — New file `app/agents/utils.py`: Move `_build_enriched_query` functions

> ⚠️ **Important note:** The two `_build_enriched_query` functions have different signatures and bodies — they are conceptually similar but not identical duplicates. The pragmatic fix is to move both to a shared module as clearly named functions.

**Create `app/agents/utils.py`:**

```python
"""Shared utilities for agent query building."""


def build_recommendation_query(query: str, hints: dict, max_results: int) -> str:
    """Build enriched query string for the RecommendationAgent."""
    parts = [query]
    if hints.get("max_price"):
        parts.append(f"Maximum price: ${hints['max_price']}")
    if hints.get("min_price"):
        parts.append(f"Minimum price: ${hints['min_price']}")
    if hints.get("categories"):
        parts.append(f"Categories of interest: {', '.join(hints['categories'])}")
    if hints.get("brands"):
        parts.append(f"Preferred brands: {', '.join(hints['brands'])}")
    parts.append(f"Return up to {max_results} recommendations.")
    return "\n".join(parts)


def build_review_query(query: str, product_id: str | None, max_reviews: int) -> str:
    """Build enriched query string for the ReviewSummarizationAgent."""
    parts = [query]
    if product_id:
        parts.append(f"Product ID (use directly, skip find_product): {product_id}")
    parts.append(
        f"Fetch up to {max_reviews // 2} positive and {max_reviews // 2} negative reviews."
    )
    return "\n".join(parts)
```

**In `app/agents/recommendation/agent.py`:** replace `_build_enriched_query(...)` call and definition with:
```python
from app.agents.utils import build_recommendation_query
# ...
enriched_query = build_recommendation_query(query, hints, max_results)
```

**In `app/agents/review/agent.py`:** replace with:
```python
from app.agents.utils import build_review_query
# ...
enriched_query = build_review_query(query, product_id, max_reviews)
```

---

## File Map

| File | Action | Change |
|------|--------|--------|
| `app/agents/base.py` | Modify | Add `_handle_agent_error()` method |
| `app/agents/recommendation/agent.py` | Modify | Replace error block + `_build_enriched_query` |
| `app/agents/review/agent.py` | Modify | Replace error block + `_build_enriched_query` |
| `app/agents/price/agent.py` | Modify | Replace error block with `_handle_agent_error()` |
| `app/agents/policy/agent.py` | Modify | Replace error block with `_handle_agent_error()` |
| `app/core/cache_factory.py` | **Create** | New `create_cache()` factory function |
| `app/core/llm_cache.py` | Modify | Use `create_cache()` |
| `app/core/cache.py` | Modify | Use `create_cache()` in `get_review_cache()` |
| `app/services/pricing/price_cache.py` | Modify | Use `create_cache()` |
| `app/services/session/session_store.py` | Modify | Use `create_cache()` |
| `app/api/v1/products.py` | Modify | Extract `_apply_product_filters()` helper |
| `app/agents/utils.py` | **Create** | `build_recommendation_query()` + `build_review_query()` |
| `tests/test_agents/test_base.py` | Modify | Add tests for `_handle_agent_error()` |
| `tests/test_core/test_cache_factory.py` | **Create** | Tests for `create_cache()` |
| `tests/test_agents/test_utils.py` | **Create** | Tests for `build_*_query()` helpers |

---

## Test Requirements

This is a pure refactor — the goal is zero regression, not new behaviour. Test additions are small.

### `tests/test_agents/test_base.py` — ~5 new tests for `_handle_agent_error()`

```python
# 1. RateLimitError → raises AgentRateLimitError
def test_handle_rate_limit_raises():
    agent = ConcreteAgent("test")
    exc = Exception("RateLimitError: quota exceeded")
    with pytest.raises(AgentRateLimitError):
        agent._handle_agent_error(exc, query="q")

# 2. Timeout → raises AgentTimeoutError
def test_handle_timeout_raises():
    exc = Exception("TimeoutError: timed out")
    with pytest.raises(AgentTimeoutError):
        agent._handle_agent_error(exc)

# 3. Generic → returns AgentResponse(success=False)
def test_handle_generic_returns_failure():
    exc = ValueError("something broke")
    resp = agent._handle_agent_error(exc)
    assert resp.success is False

# 4. RateLimitError calls record_failure
def test_handle_rate_limit_records_failure(mock_record_failure):
    ...

# 5. Generic calls record_failure
def test_handle_generic_records_failure(mock_record_failure):
    ...
```

### `tests/test_core/test_cache_factory.py` — ~4 new tests

```python
# 1. Redis available → returns RedisCache
def test_create_cache_uses_redis_when_available(mock_redis):
    cache = create_cache(redis_url=..., key_prefix="x:", ttl=60, max_size=100)
    assert isinstance(cache, RedisCache)

# 2. Redis unavailable → returns TTLCache
def test_create_cache_falls_back_to_ttlcache():
    cache = create_cache(redis_url="redis://bad-host", ...)
    assert isinstance(cache, TTLCache)

# 3. TTLCache has correct TTL
def test_create_cache_ttlcache_ttl():
    cache = create_cache(..., ttl=300, ...)
    assert cache._default_ttl == 300

# 4. RedisCache has correct key_prefix
def test_create_cache_redis_key_prefix(mock_redis):
    cache = create_cache(..., key_prefix="myprefix:", ...)
    assert cache._key_prefix == "myprefix:"
```

### `tests/test_agents/test_utils.py` — ~4 new tests

```python
# 1. build_recommendation_query includes max_price hint
def test_recommendation_query_with_max_price():
    result = build_recommendation_query("laptop", {"max_price": 1000}, 5)
    assert "Maximum price: $1000" in result

# 2. build_recommendation_query no hints
def test_recommendation_query_no_hints():
    result = build_recommendation_query("laptop", {}, 5)
    assert "Return up to 5 recommendations" in result

# 3. build_review_query with product_id
def test_review_query_with_product_id():
    result = build_review_query("reviews for X", product_id="P123", max_reviews=10)
    assert "P123" in result

# 4. build_review_query without product_id
def test_review_query_no_product_id():
    result = build_review_query("reviews", product_id=None, max_reviews=10)
    assert "Product ID" not in result
```

**Expected new tests: ~13 → total ~473**

---

## Dependencies

- Builds directly on SCRUM-65 — `app/core/database.py` is already updated (no conflicts here)
- SCRUM-67 (SQL) and SCRUM-69 (error hardening) both touch agent files — do SCRUM-66 first so those stories inherit the cleaner `_handle_agent_error()` base
- SCRUM-69 also touches agent error handling — dev should be aware that the error-handling shape will change in this story

---

## Risks & Notes

| Risk | Mitigation |
|------|-----------|
| `_handle_agent_error` changes error message format | Keep exact same `user_message` strings — tests check these |
| Cache factory changes log message format | Tests that assert on log output will need updating — check existing cache tests |
| `_build_enriched_query` rename in tests | Grep for `_build_enriched_query` in tests before removing local definitions |
| Policy agent error handling may differ slightly | Read `app/agents/policy/agent.py` error block before replacing — verify it matches the shared pattern |
| Pure refactor — NO new features | Do not add new capabilities during this story; any improvements go in SCRUM-67/68/69 |
