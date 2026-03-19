# SCRUM-67: Optimize SQL queries — Completion Report

## Status: Completed

## Summary
Optimized SQL queries across review tools, policy fallback, and ingestion pipeline for better performance and robustness.

## Changes Made

### 1. Review stats — 3 queries combined to 1
**File**: `app/agents/review/tools.py` — `get_review_stats()`
- Replaced 3 separate queries (sentiment counts, rating distribution, avg rating) with a single aggregation query using `case()` expressions
- Uses `func.sum(case(...))` for conditional counting in one DB round-trip

### 2. Review samples — 3 queries combined to 1
**File**: `app/agents/review/tools.py` — `get_review_samples()`
- Replaced 3 separate `fetch_reviews()` calls (positive, negative, neutral) with a single query using `IN` filter
- Results split in Python with per-sentiment limits

### 3. Policy fallback — SQL WHERE instead of Python filtering
**File**: `app/agents/policy/tools.py` — `_db_fallback()`
- Replaced `db.query(Policy).limit(5).all()` + Python keyword filtering with SQL `or_()` + `ilike()` filtering
- Handles empty query string gracefully

### 4. Ingestion — per-batch error handling with rollback
**File**: `app/services/ingestion/base.py` — `run()`
- Added per-batch try-except with `db.rollback()` on failure
- Changed from single commit at end to commit-per-batch
- Properly reverts success/fail counts when batch commit fails

### Already Done (SCRUM-65)
- `connect_args={"connect_timeout": 10}` — already in database.py
- `pool_recycle=1800` — already in database.py
- `get_db()` rollback on error — already in database.py

## Files Changed
- `app/agents/review/tools.py` — combined queries
- `app/agents/policy/tools.py` — SQL WHERE filtering
- `app/services/ingestion/base.py` — batch error handling
- `tests/test_agents/test_review_agent.py` — updated mocks, added 4 new tests
- `tests/test_agents/test_sql_optimizations.py` — new file, 8 tests (policy fallback + ingestion)

## Test Results
- **Total collected**: 589
- **Passed**: 485
- **Failed**: 7 (all pre-existing: 6 Redis module, 1 logging config)
- **Skipped**: 97
- **New tests added**: 12

## Time Spent
~15 minutes
