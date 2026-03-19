# SCRUM-65 — Improve logging & health checks for database connectivity issues

**Status:** Completed
**Time Spent:** ~25 minutes
**Date:** 2026-03-19

---

## Summary

Closed four gaps in database connectivity visibility:
1. `/health` now includes `database` field and returns `"degraded"` status when DB is unreachable
2. `ErrorHandlerMiddleware` catches SQLAlchemy `OperationalError`/`InterfaceError` → HTTP 503 with `"database_unavailable"` + `record_failure("database")`
3. Startup event performs explicit `SELECT 1` probe and logs `CRITICAL` with masked DB host if unreachable
4. `get_engine()` adds `connect_args={"connect_timeout": 10}` and `pool_recycle=1800`; `get_db()` calls `db.rollback()` before close on exception

---

## Files Changed

| File | Change |
|------|--------|
| `app/api/health.py` | Added DB probe, `database` field, `"degraded"` status |
| `app/middleware/error_handler.py` | Added `_get_masked_db_host()` + `SAOperationalError/SAInterfaceError` handler → 503 |
| `app/main.py` | Added explicit DB `SELECT 1` probe at startup with `CRITICAL` log |
| `app/core/database.py` | Added `connect_args`, `pool_recycle` to `get_engine()`; `rollback()` to `get_db()` |
| `tests/test_api/test_health.py` | 6 new tests + updated `test_health_check` to mock DB |
| `tests/test_middleware/test_error_handler.py` | 4 new tests in `TestSQLAlchemyErrorHandler` |
| `tests/test_core/test_database.py` | 4 new tests for pool_recycle, connect_timeout, rollback |

---

## Acceptance Criteria Verification

- [x] `/health` includes a `database` field (`"connected"` or `"unreachable"`)
- [x] `/health` returns `{"status": "degraded"}` (HTTP 200) when DB is down
- [x] `ErrorHandlerMiddleware` catches `OperationalError` and `InterfaceError` → HTTP 503 with `"error": "database_unavailable"` + `record_failure("database")`
- [x] Startup event performs explicit `SELECT 1` probe and logs `CRITICAL` with masked DB host if unreachable
- [x] `get_engine()` includes `connect_args={"connect_timeout": 10}` and `pool_recycle=1800`
- [x] `get_db()` calls `db.rollback()` before `db.close()` on exception
- [x] All existing tests continue to pass (7 pre-existing failures unrelated to this story)
- [x] 14 new tests added (target: ~15)

---

## Test Results

```
460 passed, 7 failed (pre-existing), 97 skipped
New tests: 14
Previous total (after SCRUM-63): ~446
New total: 460 passing
```

Pre-existing failures (not caused by this story):
- `TestRedisCache` (6): `ModuleNotFoundError: No module named 'redis'` — env issue
- `test_log_file_defaults_to_none` (1): SCRUM-63 env config state
