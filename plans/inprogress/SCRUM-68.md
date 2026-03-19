# SCRUM-68: Improve AI routing accuracy — confidence gating, comparison mode, hallucination tracking

## Acceptance Criteria
- [ ] Orchestrator uses confidence threshold (default 0.6) — low confidence routes to general
- [ ] RecommendationAgent reads and uses `compare_mode` flag
- [ ] Hallucinated product IDs logged and tracked with `record_failure("hallucination")`
- [ ] Response metadata includes `requested_count` vs `returned_count`
- [ ] Price agent validates `best_deal` against actual product list
- [ ] FAISS search applies minimum similarity threshold (configurable)
- [ ] General agent receives fallback context when taking over from failed agent
- [ ] New tests for all behaviors

## Technical Approach

### 1. Confidence gating (orchestrator.py)
- After classify(), check `intent_result.confidence < 0.6`
- If low, override to general agent with log message
- Make threshold configurable via Settings

### 2. Comparison mode (recommendation/agent.py)
- Check `context.get("compare_mode")` in process()
- Adjust enriched_query to emphasize side-by-side comparison

### 3. Hallucination tracking (recommendation/agent.py)
- In `_hydrate_recommendations()`, count dropped IDs
- Call `record_failure("hallucination")` for each dropped ID
- Add `requested_count` and `returned_count` to response metadata

### 4. Price agent best_deal validation (price/agent.py)
- After LLM output, check if `best_deal` matches any product name
- If not, set best_deal to first product or "Unknown"

### 5. FAISS similarity threshold (policy/vector_store.py)
- Add `min_score` parameter to search() (default 0.4)
- Filter results below threshold
- Make configurable via Settings

### 6. Fallback context (orchestrator.py)
- When falling back to general agent, pass `fallback_reason` and `original_intent` in context
