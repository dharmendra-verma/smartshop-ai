# SCRUM-66 — Eliminate code duplication — DRY refactor

**Status:** Completed
**Time Spent:** ~30 minutes
**Date:** 2026-03-19

---

## Summary

Pure refactor — no behaviour changes. Four DRY violations eliminated:

1. **Agent error handling** — `_handle_agent_error()` added to `BaseAgent`; all 4 agents now delegate to it
2. **Cache factory** — new `app/core/cache_factory.py` with `create_cache()`; 4 cache singletons (LLMCache, ReviewCache, PriceCache, SessionStore) now use it
3. **Product filter logic** — extracted to `_apply_product_filters()` helper in `products.py`
4. **Query builders** — `_build_enriched_query` functions moved to `app/agents/utils.py` as `build_recommendation_query()` and `build_review_query()`

---

## Files Changed

| File | Action |
|------|--------|
| `app/agents/base.py` | Added `_handle_agent_error()` method |
| `app/agents/utils.py` | **Created** — `build_recommendation_query()` + `build_review_query()` |
| `app/core/cache_factory.py` | **Created** — `create_cache()` factory |
| `app/agents/recommendation/agent.py` | Use `build_recommendation_query` + `_handle_agent_error`; removed local `_build_enriched_query` |
| `app/agents/review/agent.py` | Use `build_review_query` + `_handle_agent_error`; removed local `_build_enriched_query` |
| `app/agents/price/agent.py` | Use `_handle_agent_error` |
| `app/agents/policy/agent.py` | Use `_handle_agent_error` |
| `app/core/llm_cache.py` | Use `create_cache()` |
| `app/core/cache.py` | Use `create_cache()` in `get_review_cache()` |
| `app/services/pricing/price_cache.py` | Use `create_cache()` |
| `app/services/session/session_store.py` | Use `create_cache()` |
| `app/api/v1/products.py` | Extracted `_apply_product_filters()` helper |
| `tests/test_agents/test_base.py` | **Created** — 5 tests for `_handle_agent_error` |
| `tests/test_agents/test_utils.py` | **Created** — 5 tests for query builders |
| `tests/test_core/test_cache_factory.py` | **Created** — 4 tests for `create_cache` |

---

## Acceptance Criteria

- [x] Agent error handling extracted to `BaseAgent._handle_agent_error()` — all 4 agents use it
- [x] Cache factory created in `app/core/cache_factory.py` — all 4 cache singletons use it
- [x] Product filter logic extracted to `_apply_product_filters()` in `products.py`
- [x] `_build_enriched_query` functions moved to `app/agents/utils.py`
- [x] All 460 existing tests pass — zero behaviour change
- [x] No new public API or endpoint changes

---

## Test Results

```
474 passed, 7 failed (pre-existing), 97 skipped
New tests: 14 (5 + 5 + 4)
Previous total: 460 passing
New total: 474 passing
```
