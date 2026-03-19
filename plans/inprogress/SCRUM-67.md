# SCRUM-67: Optimize SQL queries — combine review stats, fix policy fallback, add DB robustness

## Story Details
- **ID**: SCRUM-67
- **Status**: In Progress
- **Priority**: Medium

## Acceptance Criteria
- [ ] Review stats combined into single aggregation query
- [ ] Review samples combined into single query
- [ ] Policy fallback uses SQL WHERE clause instead of Python filtering
- [ ] Database engine configured with connect_timeout and pool_recycle (ALREADY DONE - SCRUM-65)
- [ ] get_db() has rollback on error (ALREADY DONE - SCRUM-65)
- [ ] Ingestion pipeline has per-batch try-except with rollback
- [ ] All existing tests pass
- [ ] New tests for optimized queries

## Technical Approach

### 1. Combine review stats (3 queries → 1)
**File**: `app/agents/review/tools.py` — `get_review_stats()`
- Use a single query with `case()` expressions for sentiment counts, rating buckets, avg, and count
- SQLAlchemy `func.sum(case(...))` pattern

### 2. Combine review samples (3 queries → 1)
**File**: `app/agents/review/tools.py` — `get_review_samples()`
- Single query fetching all sentiments, use window function `row_number()` partitioned by sentiment
- Or simpler: single query with `IN` filter, then split in Python

### 3. Fix policy fallback
**File**: `app/agents/policy/tools.py` — `_db_fallback()`
- Use `or_()` with `Policy.description.ilike()` and `Policy.conditions.ilike()` for each keyword
- Remove the `.limit(5).all()` + Python filter pattern

### 4. Batch-level error handling in ingestion
**File**: `app/services/ingestion/base.py` — `run()`
- Wrap each batch in try-except, call `db.rollback()` on failure
- Commit per batch instead of single commit at end

## Already Completed (SCRUM-65)
- connect_args={"connect_timeout": 10} ✓
- pool_recycle=1800 ✓
- get_db() rollback on error ✓

## Test Requirements
- Update existing review tools tests for new query structure
- Add tests for policy fallback SQL filtering
- Add tests for ingestion batch error recovery
- Expected: ~10-15 new tests
