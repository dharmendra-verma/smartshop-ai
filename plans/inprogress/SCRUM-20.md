# SCRUM-20 — Performance Optimization and Latency Improvements

**Jira:** https://projecttracking.atlassian.net/browse/SCRUM-20
**Priority:** Medium
**Status:** In Progress

---

## Story

> As a user, I want fast responses so that I can complete my shopping tasks efficiently without waiting.

---

## Acceptance Criteria

- [ ] P95 response latency ≤ 3 seconds
- [ ] Database query optimization (indexes, query plans)
- [ ] Redis caching for frequent queries
- [ ] Async processing for non-blocking operations
- [ ] LLM token usage optimized
- [ ] Batch processing where applicable
- [ ] Load testing completed (100+ concurrent users)
- [ ] Performance monitoring dashboard set up

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Agent response time | ≤ 3s P95 |
| DB query latency | ≤ 200ms P95 |
| Cache hit rate | ≥ 60% |
| LLM tokens / request avg | ≤ 1,500 |

---

## Current State — What Already Exists

| Component | Status | Detail |
|-----------|--------|--------|
| `TTLCache` + `RedisCache` dual backend | ✅ | `app/core/cache.py` — same interface |
| `PriceCache` | ✅ | `app/services/pricing/` — `price:` prefix, 3600s TTL |
| `SessionStore` | ✅ | `app/services/session/` — `session:` prefix, 1800s TTL |
| DB connection pooling | ✅ | `pool_size=20`, `max_overflow=10`, `pool_pre_ping=True` |
| `OPENAI_MAX_TOKENS=1500` | ✅ | Config setting already present |
| `UsageLimits(request_limit=15)` | ✅ | All agents — prevents runaway LLM loops |
| DB indexes on products | ✅ | `idx_product_category_brand`, `idx_product_price`, `name`, `brand`, `category` |
| Pagination | ✅ | `/api/v1/products` — offset/limit, max 100 per page |
| `X-Process-Time-Ms` response header | ✅ | `RequestLoggingMiddleware` |

**What is missing:**
1. **GZip response compression** — `GZipMiddleware` not added; all JSON responses sent uncompressed
2. **LLM response cache** — agent answers for identical queries are recomputed every time; no 24h cache
3. **DB engine singleton** — `get_engine()` / `get_session_factory()` called fresh on each request (no singleton); creates unnecessary overhead
4. **Additional DB indexes** — `rating` and `stock` columns have no index (used in ordering/filtering); review table `product_id` index worth checking
5. **Performance metrics store** — no in-process counters for P95 latency tracking; only per-request headers
6. **Cache warming at startup** — no pre-loading of popular product queries into cache
7. **Prompt token optimization** — system prompts have verbose instructional text; can be trimmed to reduce token usage by ~20%

---

## Technical Approach

### 1. GZip Compression — `main.py` (MODIFY, 2-line change)

```python
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)  # compress responses > 1KB
```

Add after `CORSMiddleware`. This alone can reduce response payload size by 60–80% for large product list JSON responses.

### 2. LLM Response Cache — `app/core/llm_cache.py` (NEW)

Cache the full `AgentResponse` for identical query hashes. 24h TTL for deterministic queries. Uses the existing `TTLCache`/`RedisCache` pattern:

```python
"""LLM response cache — 24h TTL for identical agent queries."""
import hashlib, time, logging
from app.agents.base import AgentResponse

logger = logging.getLogger(__name__)
_LLM_CACHE_TTL = 86400  # 24 hours

# Module-level singleton (same pattern as PriceCache / SessionStore)
_llm_cache = None

def get_llm_cache():
    global _llm_cache
    if _llm_cache is not None:
        return _llm_cache
    from app.core.config import get_settings
    from app.core.cache import RedisCache, TTLCache
    settings = get_settings()
    try:
        cache = RedisCache(settings.REDIS_URL, default_ttl=_LLM_CACHE_TTL, key_prefix="llm:")
        cache._client.ping()
        _llm_cache = cache
        logger.info("LLMCache: using Redis")
    except Exception:
        _llm_cache = TTLCache(default_ttl=_LLM_CACHE_TTL, max_size=500)
        logger.info("LLMCache: using in-memory TTLCache")
    return _llm_cache

def reset_llm_cache():
    global _llm_cache
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

def set_cached_llm_response(agent_name: str, query: str, response: AgentResponse) -> None:
    if response.success:
        get_llm_cache().set(_cache_key(agent_name, query), response.model_dump())
        logger.debug("LLMCache SET: agent=%s", agent_name)
```

**Integrate into each agent's `process()` method:**
```python
# At top of process():
from app.core.llm_cache import get_cached_llm_response, set_cached_llm_response
cached = get_cached_llm_response(self.name, query)
if cached:
    return cached

# After successful result:
set_cached_llm_response(self.name, query, response)
return response
```

### 3. DB Engine Singleton — `app/core/database.py` (MODIFY)

Currently `get_engine()` and `get_session_factory()` create new objects on every call. Add module-level singletons:

```python
_engine: Engine | None = None
_session_factory: sessionmaker | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.DATABASE_URL,
            echo=settings.DB_ECHO,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
            pool_pre_ping=True,
        )
    return _engine

def get_session_factory() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _session_factory

def reset_engine():
    """Reset singletons (for tests)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
```

### 4. Additional DB Indexes — New Alembic Migration (NEW FILE)

Create `alembic/versions/003_add_performance_indexes.py`:

```python
"""Add performance indexes for rating, stock ordering and review product lookups."""
from alembic import op

revision = '003_perf_indexes'
down_revision = '002_add_image_url_to_products'

def upgrade():
    # Products: rating (ORDER BY rating DESC is a common sort)
    op.create_index('idx_product_rating', 'products', ['rating'])
    # Products: stock (filter stock > 0)
    op.create_index('idx_product_stock', 'products', ['stock'])
    # Reviews: product_id (foreign key scan — used in review summarization)
    op.create_index('idx_review_product_id', 'reviews', ['product_id'])
    # Reviews: rating (for rating distribution queries)
    op.create_index('idx_review_rating', 'reviews', ['rating'])

def downgrade():
    op.drop_index('idx_product_rating', 'products')
    op.drop_index('idx_product_stock', 'products')
    op.drop_index('idx_review_product_id', 'reviews')
    op.drop_index('idx_review_rating', 'reviews')
```

Also add the indexes declaratively to `app/models/product.py` (`__table_args__`) and `app/models/review.py`.

### 5. Performance Metrics — `app/core/metrics.py` (NEW)

Simple in-process P95 latency tracker using a rolling deque. Exposed via `GET /health/metrics`:

```python
"""Lightweight in-process performance metrics."""
import time, statistics
from collections import defaultdict, deque

_latencies: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))

def record_latency(endpoint: str, latency_ms: float) -> None:
    _latencies[endpoint].append(latency_ms)

def get_p95(endpoint: str) -> float | None:
    samples = list(_latencies[endpoint])
    if not samples:
        return None
    return statistics.quantiles(samples, n=100)[94]  # 95th percentile

def get_metrics_summary() -> dict:
    return {
        endpoint: {
            "p50_ms": round(statistics.median(list(vals)), 1),
            "p95_ms": round(get_p95(endpoint), 1),
            "sample_count": len(vals),
        }
        for endpoint, vals in _latencies.items()
        if vals
    }
```

Record in `RequestLoggingMiddleware.dispatch()` after each request. Expose via `GET /health/metrics` in `app/api/health.py`.

### 6. Cache Warming at Startup — `app/services/cache_warmer.py` (NEW)

Pre-populate the LLM cache and product list cache with top-N popular queries at startup:

```python
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

async def warm_caches(api_url: str | None = None) -> None:
    """Pre-warm LLM response cache with popular queries. Called at startup."""
    from app.core.llm_cache import get_cached_llm_response
    warmed = 0
    for agent_name, query in WARM_QUERIES:
        if get_cached_llm_response(agent_name, query) is None:
            logger.info("CacheWarmer: queuing '%s' for '%s'", query, agent_name)
            # Note: actual warm-up calls are skipped at startup to avoid cold-start latency;
            # Instead, the cache is populated organically and persists via Redis TTL.
            # This function is a hook for future scheduled warming jobs (SCRUM-44+).
        else:
            warmed += 1
    logger.info("CacheWarmer: %d/%d queries already cached", warmed, len(WARM_QUERIES))
```

Call in `main.py`'s `startup_event()`.

### 7. Prompt Token Optimization (MODIFY agent prompts)

Audit and trim the system prompts in each agent. Current RecommendationAgent prompt is ~500 tokens — target ~350 tokens by removing redundant examples and consolidating rules. Apply the same pass to `review/prompts.py`, `price/prompts.py`, `policy/prompts.py`.

Guideline: Remove explanatory prose, keep only rules and the structured output schema description. Estimated saving: ~150 tokens/request × all endpoints = significant cost reduction at scale.

---

## File Map

| File | Action | What Changes |
|------|--------|-------------|
| `app/main.py` | **MODIFY** | Add `GZipMiddleware`; call `warm_caches()` in startup |
| `app/core/llm_cache.py` | **CREATE** | LLM response cache singleton (Redis→TTLCache) |
| `app/core/metrics.py` | **CREATE** | P95 latency tracker; `record_latency`, `get_metrics_summary` |
| `app/core/database.py` | **MODIFY** | Engine + session factory singletons; `reset_engine()` for tests |
| `app/services/cache_warmer.py` | **CREATE** | Startup cache warm-up hook |
| `alembic/versions/003_add_performance_indexes.py` | **CREATE** | Add rating/stock/review indexes |
| `app/models/product.py` | **MODIFY** | Add `idx_product_rating`, `idx_product_stock` to `__table_args__` |
| `app/models/review.py` | **MODIFY** | Add `idx_review_product_id`, `idx_review_rating` to `__table_args__` |
| `app/middleware/logging_middleware.py` | **MODIFY** | Call `record_latency(endpoint, latency_ms)` per request |
| `app/api/health.py` | **MODIFY** | Add `GET /health/metrics` endpoint |
| `app/agents/recommendation/agent.py` | **MODIFY** | LLM cache check at start + set on success |
| `app/agents/review/agent.py` | **MODIFY** | LLM cache check + set |
| `app/agents/price/agent.py` | **MODIFY** | LLM cache check + set |
| `app/agents/policy/agent.py` | **MODIFY** | LLM cache check + set |
| `app/agents/recommendation/prompts.py` | **MODIFY** | Trim to ≤350 tokens |
| `app/agents/review/prompts.py` | **MODIFY** | Trim to ≤350 tokens |
| `app/agents/price/prompts.py` | **MODIFY** | Trim to ≤350 tokens |
| `tests/test_core/test_llm_cache.py` | **CREATE** | Unit tests for LLM cache |
| `tests/test_core/test_metrics.py` | **CREATE** | Unit tests for metrics tracker |
| `tests/test_core/test_database.py` | **MODIFY** | Add tests for engine singleton + reset |

---

## Test Requirements

**New file: `tests/test_core/test_llm_cache.py`** (~7 tests):
```
test_cache_miss_returns_none()
test_cache_hit_after_set()
test_cached_response_has_from_cache_metadata()
test_failed_response_not_cached()
test_different_queries_different_keys()
test_same_query_normalized_matches()
test_reset_llm_cache_clears_singleton()
```

**New file: `tests/test_core/test_metrics.py`** (~5 tests):
```
test_record_latency_adds_sample()
test_p95_returns_none_on_empty()
test_p95_returns_value_with_samples()
test_get_metrics_summary_includes_all_endpoints()
test_metrics_rolling_window_max_200()
```

**Modify: `tests/test_core/test_database.py`** (~3 new tests):
```
test_get_engine_returns_singleton()
test_reset_engine_clears_singleton()
test_get_session_factory_returns_singleton()
```

**Expected new tests:** ~15
**Total after story:** ~327 (312 base + 15)

> Note: If SCRUM-19 is completed first (adds ~18 → 330), then SCRUM-20 adds ~15 → ~345.

---

## Dependencies

- Depends on SCRUM-17 (Redis/TTLCache dual-backend pattern already established) ✅
- GZipMiddleware is part of `starlette` (already a FastAPI dependency) — no new packages needed
- Alembic already configured ✅
- `statistics` is Python stdlib — no new packages needed

---

## Implementation Order

1. `database.py` engine singleton (low risk, enables cleaner testing)
2. `GZipMiddleware` in `main.py` (2-line change, immediate win)
3. Alembic migration `003_add_performance_indexes.py` + model updates
4. `llm_cache.py` + integrate into all 4 agents
5. `metrics.py` + `RequestLoggingMiddleware` integration + `/health/metrics` endpoint
6. `cache_warmer.py` + `main.py` startup hook
7. Prompt trimming (recommendation → review → price → policy)
8. Tests
