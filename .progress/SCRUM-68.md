# SCRUM-68: Improve AI routing accuracy — Completion Report

## Status: Completed

## Summary
Improved AI routing accuracy with confidence gating, comparison mode support, hallucination tracking, best_deal validation, FAISS similarity threshold, and fallback context passing.

## Changes Made

### 1. Confidence gating (orchestrator.py)
- Added `INTENT_CONFIDENCE_THRESHOLD` setting (default 0.6) to config
- Orchestrator routes to general agent when confidence < threshold
- General intent exempt from gating (can't redirect general to general)

### 2. Comparison mode (recommendation/agent.py)
- RecommendationAgent now reads `compare_mode` from context
- Appends comparison-specific instructions to enriched query

### 3. Hallucination tracking (recommendation/agent.py)
- `_hydrate_recommendations()` now returns tuple of (results, hallucinated_ids)
- Dropped IDs logged at WARNING level and tracked via `record_failure("hallucination")`
- Response includes `requested_count` vs `returned_count` in data
- `hallucinated_ids` included in response metadata

### 4. Price agent best_deal validation (price/agent.py)
- After LLM output, validates `best_deal` against actual product names
- Corrects to first product name if hallucinated, with WARNING log

### 5. FAISS similarity threshold (policy/vector_store.py)
- Added `min_score` parameter to `search()` (default from `FAISS_MIN_SIMILARITY_SCORE=0.4`)
- Results below threshold are filtered out with debug logging
- Returns empty list if no results pass threshold

### 6. Fallback context (orchestrator.py)
- When falling back (agent unavailable or exception), passes `fallback_reason` and `original_intent` in context
- Both unavailable-agent and exception fallback paths include context

## Files Changed
- `app/core/config.py` — added INTENT_CONFIDENCE_THRESHOLD, FAISS_MIN_SIMILARITY_SCORE
- `app/agents/orchestrator/orchestrator.py` — confidence gating, fallback context
- `app/agents/recommendation/agent.py` — compare_mode, hallucination tracking
- `app/agents/price/agent.py` — best_deal validation
- `app/agents/policy/vector_store.py` — min_score threshold
- `tests/test_agents/test_ai_routing.py` — new file, 14 tests

## Test Results
- **Total**: 499 passed, 1 pre-existing failure, 97 skipped
- **New tests added**: 14
- **Test count**: 500

## Time Spent
~15 minutes
