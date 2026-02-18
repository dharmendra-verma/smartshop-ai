# SCRUM-39: Fix Default Schemas — Time Log

## Summary
- **Issue**: Model schemas (Product, Review, Policy) did not match CSV data structure
- **Status**: Fixed and verified
- **Date**: 2026-02-18

## Time Breakdown

| Phase | Duration | Description |
|-------|----------|-------------|
| Analysis & Investigation | ~8 min | Read Jira issue, analyzed all 3 CSV files, compared with models, schemas, ingesters, and tests. Identified root cause via git diff. |
| Planning | ~3 min | Created implementation plan, identified 4 files to fix and 14 failing tests |
| Implementation | ~4 min | Updated 4 test files to align with new schema |
| Verification | ~1 min | Ran full test suite — 99/99 passed |
| **Total** | **~16 min** | |

## Files Modified

### Models/Schemas/Ingesters (already fixed by SCRUM-7, uncommitted)
- `app/models/product.py` — `product_id` (int) -> `id` (String), added `stock`/`rating`, removed `image_url`
- `app/models/review.py` — `review_text` -> `text`, `timestamp` -> `review_date`, `rating` int -> Float, FK type String
- `app/models/policy.py` — `category/question/answer/effective_date` -> `policy_type/description/conditions/timeframe`
- `app/schemas/ingestion.py` — Updated to match new model fields
- `app/services/ingestion/product_ingester.py` — Updated field mappings and validation
- `app/services/ingestion/review_ingester.py` — Updated field mappings, date parsing, sentiment inference
- `app/services/ingestion/policy_ingester.py` — Updated field mappings

### Tests (fixed in this session)
- `tests/test_services/test_product_ingester.py` — Added `id` column to CSV data, removed `image_url`, updated dedup test
- `tests/test_services/test_review_ingester.py` — Fixed `products_in_db` fixture to include `id`, updated column names (`text` not `review_text`)
- `tests/test_services/test_policy_ingester.py` — Rewrote CSV test data for new schema (`policy_type, description, conditions, timeframe`)
- `tests/test_core/test_database.py` — Added `id` to Product creation in `test_session_lifecycle`

## Test Results
- **99/99 tests passed**
- **0 failures**
- **Coverage**: 72% overall, 100% on models
