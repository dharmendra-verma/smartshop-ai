# SmartShop AI — Rubric Gap Analysis

**Date:** 2026-03-14
**Analyzed by:** Claude (code review)

## Scoring Summary

| # | Criteria | Max | Current Score | Grade | Key Gap |
|---|----------|-----|---------------|-------|---------|
| 1 | Code Readability & Organization | 10 | 9 (90%) | Good | Minor: inconsistent type hints (`Optional[str]` vs `str \| None`), ~15-20 functions missing docstrings |
| 2 | Code Reusability & Modularity | 10 | 7.5 (75%) | Satisfactory | Duplicated error handling in 4 agents, duplicated cache factory in 4 files, duplicated filter logic in products |
| 3 | Error Handling & Debugging | 10 | 7.5 (75%) | Satisfactory | GeneralResponseAgent returns `success=True` on errors; SQLAlchemy errors hit generic 500; no endpoint-level try-except (**SCRUM-65 partially covers**) |
| 4 | Database Connection Handling | 10 | 7.5 (75%) | Satisfactory | No connection timeout; no explicit rollback; health check doesn't verify DB (**SCRUM-65 covers health check**) |
| 5 | SQL Query Efficiency | 10 | 9 (90%) | Good | Review stats uses 3 separate queries; policy fallback loads ALL rows; duplicate filter logic |
| 6 | AI Query Processing | 10 | 9 (90%) | Good | Comparison mode flag set but never read by agent; intent confidence not used for routing |
| 7 | Agent Building & Integration | 10 | 10 (100%) | Excellent | All 5 agents + orchestrator work well; circuit breaker, fallback chain |
| 8 | Multi-Agent System | 10 | 9 (90%) | Good | No multi-intent support; confidence not gating routing; no structured context passed to fallback agent |
| 9 | Session & Query Memory | 10 | 9 (90%) | Good | Text-based context (not semantic); 10-turn window may be short; no user notification of truncation |
| 10 | Accuracy & Trustworthiness | 10 | 9 (90%) | Good | Hallucinated product IDs silently dropped; price agent no output validation; no similarity threshold on FAISS |
| 11 | Deployment & Scalability | 10 | 10 (100%) | Excellent | Full CI/CD, Docker multi-stage, Azure Container Apps, auto-scaling, rollback, IaC |
| 12 | UI & Usability | 10 | 10 (100%) | Excellent | Design tokens, modular components, floating chat, inline reviews, comparison, responsive |
| 13 | Unique Enhancements (Bonus) | 10 | 10 (100%) | Excellent | Circuit breaker, FAISS RAG, 3-tier caching, request ID correlation, metrics/alerting |

**Total: 109 / 120 (base) + 10 (bonus) = 109/130 ≈ 84%**
**With fixes applied: ~125/130 ≈ 96%**

---

## Detailed Gap Analysis

### Gap 1 — Code Reusability (Score: 75% → target 100%)

**Duplicated error handling in all agents:**
- `recommendation/agent.py` lines 117-142
- `review/agent.py` lines 150-175
- `price/agent.py` lines 119-144
- `policy/agent.py` (similar pattern)
- All check for RateLimitError/Timeout, record_failure, raise exceptions → should be in BaseAgent

**Duplicated cache factory (Redis → TTLCache fallback):**
- `app/core/llm_cache.py` lines 15-33
- `app/core/cache.py` lines 139-166
- `app/services/pricing/price_cache.py` lines 10-33
- `app/services/session/session_store.py` lines 13-36
- Same try-Redis-fallback-to-TTLCache pattern → should be a factory function

**Duplicated filter logic in products endpoint:**
- `app/api/v1/products.py` lines 44-52 (main query) and 56-64 (count query) — identical filters applied twice

**Duplicated `_build_enriched_query()` function:**
- `recommendation/agent.py` lines 145-161
- `review/agent.py` lines 178-189

### Gap 2 — Error Handling (Score: 75% → target 100%)
*SCRUM-65 covers: DB health check, SQLAlchemy error mapping, startup probe, structured logging*

**Additional gaps not in SCRUM-65:**
- `GeneralResponseAgent` line 49-58: returns `success=True` on ANY exception — masks failures
- No endpoint-level try-except on products/reviews/recommendations — relies solely on middleware
- Session history JSON parse failure silently returns empty (session_manager.py line 67-69)
- Ingestion pipeline has no batch-level rollback (base.py lines 40-50)
- Intent classification errors silently default to GENERAL with confidence=0.0

### Gap 3 — Database Connection (Score: 75% → target 100%)
*SCRUM-65 covers: health check DB probe*

**Additional gaps:**
- No `connect_args={"timeout": 10}` on engine creation (database.py line 25-31)
- No `pool_recycle` configured — long-lived connections can go stale
- No explicit `db.rollback()` in `get_db()` dependency on error
- Ingestion pipeline: single commit at end, no per-batch error isolation

### Gap 4 — SQL Query Efficiency (Score: 90% → target 100%)
- Review stats: 3 separate queries (sentiment counts, rating distribution, avg rating) → combine into 1
- Review samples: 3 fetches by sentiment → combine into 1 with UNION or OR filter
- Policy fallback: `db.query(Policy).limit(5).all()` loads without WHERE clause
- Products: duplicate filter application for main query and count query

### Gap 5 — AI Routing & Accuracy (Score: 90% → target 100%)
- `compare_mode=True` flag set in orchestrator line 47 but RecommendationAgent never reads it
- Intent confidence score calculated but not used for routing decisions — low confidence still routes to specialized agent
- No multi-intent detection (e.g., "compare prices and show reviews")
- Hallucinated product IDs silently dropped in `_hydrate_recommendations()` — no logging/alerting
- Price agent: no validation that `best_deal` product name exists in results
- FAISS policy search: no minimum similarity threshold — returns low-relevance results
- General fallback agent doesn't receive prior agent context or session history

### Gap 6 — Session Memory (Score: 90% → target 100%)
- Session context is text-prepended, not semantically structured
- No tracking of "current product being discussed" across turns
- 10-turn window (MAX_PAIRS=10) may lose important early context
- No notification to user when history is truncated
