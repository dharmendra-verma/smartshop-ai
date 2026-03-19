# SCRUM-69: Harden error handling — Completion Report

## Status: Completed

## Summary
Fixed silent failures across the codebase: GeneralResponseAgent now reports errors honestly, all API endpoints have explicit error boundaries returning 503, session parse failures are tracked in alerting, and intent classifier distinguishes failed classifications.

## Changes Made

### 1. GeneralResponseAgent — success=False on exception
- Changed `success=True` to `success=False` in except block
- Now calls `record_failure()` on ALL exceptions (not just rate limits/timeouts)
- Includes error type in `error` field for debugging

### 2. API endpoint error boundaries
- Added try-except to recommendations, reviews, price, and policy endpoints
- Returns 503 with meaningful messages instead of generic 500 from middleware
- Re-raises HTTPException to preserve intentional error responses (404, 500)

### 3. Session parse alerting
- Added `record_failure("session_parse")` on JSON parse failures
- Logs raw data length and exception details at WARNING level

### 4. Intent classifier classification_failed flag
- Added `classification_failed: bool` field to `_IntentResult` (default False)
- Set to True when classification fails and falls back to GENERAL
- Orchestrator can now distinguish "classified as general" from "couldn't classify"

### 5. Ingestion batch recovery — ALREADY DONE (SCRUM-67)

## Files Changed
- `app/agents/orchestrator/general_agent.py` — success=False, always record_failure
- `app/agents/orchestrator/intent_classifier.py` — classification_failed flag
- `app/services/session/session_manager.py` — alerting on parse failure
- `app/api/v1/recommendations.py` — endpoint try-except
- `app/api/v1/reviews.py` — endpoint try-except
- `app/api/v1/price.py` — endpoint try-except
- `app/api/v1/policy.py` — endpoint try-except
- `tests/test_agents/test_error_handling.py` — new file, 11 tests

## Test Results
- **Total**: 510 passed, 1 pre-existing failure, 97 skipped
- **New tests added**: 11
- **Test count**: 511

## Time Spent
~10 minutes
