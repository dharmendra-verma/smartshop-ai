# SCRUM-65 — Improve logging & health checks for database connectivity issues

**Jira:** https://projecttracking.atlassian.net/browse/SCRUM-65
**Status:** In Progress
**Priority:** Medium
**Assignee:** Dharmendra Verma

---

## Problem

When the Supabase DB goes down (free-tier auto-pause), the app returns generic 500s on all
DB-dependent endpoints while `/health` still reports `"healthy"`. There is no way to diagnose
the root cause from responses, logs, or health checks alone.

Four specific gaps must be closed:

| Gap | Location | Current Behaviour | Target |
|-----|----------|-------------------|--------|
| 1 | `app/api/health.py:10` | Returns `{"status":"healthy"}` with no DB check | Include `database` field + `"degraded"` when down |
| 2 | `app/middleware/error_handler.py:70` | `OperationalError`/`InterfaceError` hit generic 500 catch-all | Catch SQLAlchemy errors → 503 + `record_failure("database")` |
| 3 | `app/main.py:79-80` | Startup silently logs WARNING if DB unavailable | Explicit DB probe at startup → CRITICAL log with masked host |
| 4 | `app/core/database.py:25-31,54-61` | No `connect_timeout`, no `pool_recycle`, no rollback in `get_db` | Add all three |

---

## Acceptance Criteria

- [ ] `/health` includes a `database` field (`"connected"` or `"unreachable"`)
- [ ] `/health` returns `{"status": "degraded"}` (HTTP 200) when DB is down
- [ ] `ErrorHandlerMiddleware` catches `sqlalchemy.exc.OperationalError` and `sqlalchemy.exc.InterfaceError` → HTTP 503 with `"error": "database_unavailable"` + `record_failure("database")`
- [ ] Startup event performs explicit `SELECT 1` probe and logs `CRITICAL` with masked DB host if unreachable
- [ ] `get_engine()` includes `connect_args={"connect_timeout": 10}` and `pool_recycle=1800`
- [ ] `get_db()` calls `db.rollback()` before `db.close()` on exception
- [ ] All existing 430 tests continue to pass
- [ ] ~15 new tests covering all new behaviours

---

## Technical Approach

### File 1 — `app/api/health.py`

**Change:** Add async DB connectivity check inside `/health`.

```python
# Imports to add
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, InterfaceError
from app.core.database import get_engine

@router.get("/health")
async def health_check():
    """Health check endpoint — includes lightweight DB probe."""
    db_status = "connected"
    overall_status = "healthy"
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except (OperationalError, InterfaceError):
        db_status = "unreachable"
        overall_status = "degraded"

    return {
        "status": overall_status,
        "service": "SmartShop AI",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
    }
```

**Key decisions:**
- Always returns HTTP 200 so Azure Container App probes / Docker healthchecks still pass
- `"degraded"` (not `"unhealthy"`) signals a partial degradation without triggering automatic container restarts
- DB connection inherits the `connect_timeout: 10` set in File 4 so the health probe never hangs
- Use synchronous `engine.connect()` (SQLAlchemy sync engine is already used throughout — no async complexity needed)

---

### File 2 — `app/middleware/error_handler.py`

**Change:** Add a new `except` clause specifically for raw SQLAlchemy connectivity exceptions,
**before** the generic `Exception` catch-all. Also add a helper to extract a masked DB host for
structured logging.

```python
# New imports
import re
from sqlalchemy.exc import OperationalError as SAOperationalError
from sqlalchemy.exc import InterfaceError as SAInterfaceError

# Helper (module-level)
def _get_masked_db_host() -> str:
    """Extract and mask the DB host from DATABASE_URL for safe logging."""
    try:
        from app.core.config import get_settings
        url = get_settings().DATABASE_URL
        # Extract host portion after @ and before / e.g. host:port
        match = re.search(r"@([^/]+)", url)
        return match.group(1) if match else "unknown"
    except Exception:
        return "unknown"

# New except clause — insert between DatabaseError handler and SmartShopError handler:
except (SAOperationalError, SAInterfaceError) as exc:
    db_host = _get_masked_db_host()
    logger.error(
        "DB connectivity error [%s]: type=%s host=%s error=%.200s",
        request_id, type(exc).__name__, db_host, str(exc),
        exc_info=True,
    )
    record_failure("database")
    return JSONResponse(
        status_code=503,
        content={
            "error": "database_unavailable",
            "detail": "Database is currently unavailable. Please try again shortly.",
            "request_id": request_id,
        },
    )
```

**Key decisions:**
- Truncate error string to 200 chars (`%.200s`) to avoid bloated log lines
- `record_failure("database")` ensures the alerting system categorises this correctly (threshold: 10 failures in 5 min)
- Insert between `DatabaseError` and `SmartShopError` handlers — preserves existing custom exception priority

**Exception handler order after this change:**
1. `AgentRateLimitError` → 429
2. `AgentTimeoutError` → 504
3. `DatabaseError` (custom) → 503
4. **NEW: `SAOperationalError | SAInterfaceError` → 503** ← inserted here
5. `SmartShopError` → 500
6. `Exception` (catch-all) → 500

---

### File 3 — `app/main.py`

**Change:** Add an explicit DB probe at startup — separate from the policy-load block — that logs
`CRITICAL` with a masked host if the DB is unreachable.

```python
# Add to startup_event(), before the existing policy-load block:

# --- Explicit DB connectivity probe ---
try:
    from sqlalchemy import text
    from app.core.database import get_engine
    import re

    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Database connectivity check: OK")
except Exception as db_exc:
    try:
        db_url = settings.DATABASE_URL
        match = re.search(r"@([^/]+)", db_url)
        masked_host = match.group(1) if match else "unknown"
    except Exception:
        masked_host = "unknown"
    logger.critical(
        "DATABASE UNREACHABLE at startup — host=%s error=%s — "
        "DB-dependent endpoints will fail until connectivity is restored",
        masked_host,
        str(db_exc),
    )
```

**Key decisions:**
- Keep as a WARNING for missing policy load (existing behaviour) — CRITICAL is reserved for the connectivity probe
- App continues booting even when DB is unreachable (graceful degradation)
- Structured log fields (`host=`, `error=`) help Azure Log Analytics filter queries

---

### File 4 — `app/core/database.py`

**Changes:** Two targeted edits.

**Edit A — `get_engine()`: Add `connect_args` and `pool_recycle`**

```python
_engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10},   # ← NEW
    pool_recycle=1800,                        # ← NEW (recycle after 30 min)
)
```

- `connect_timeout: 10` — prevents health probe / startup from hanging on a paused DB
- `pool_recycle: 1800` — matches session TTL; avoids stale connections after Supabase auto-pause

**Edit B — `get_db()`: Add rollback on exception**

```python
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    except Exception:          # ← NEW
        db.rollback()          # ← NEW — clean up dirty session state
        raise                  # ← NEW — re-raise so middleware handles it
    finally:
        db.close()
```

- `raise` ensures the exception still propagates to `ErrorHandlerMiddleware` — nothing is swallowed
- `rollback()` before `close()` prevents "transaction is already begun" errors on subsequent requests in the pool

---

## File Map

| File | Lines Changed | Change Type |
|------|--------------|-------------|
| `app/api/health.py` | 9–17 → replace + new imports | Modify |
| `app/middleware/error_handler.py` | after line 58 + top of file | Add handler + helper |
| `app/main.py` | after line 64 (before policy block) | Add DB probe block |
| `app/core/database.py` | lines 25–31 (engine), 54–61 (get_db) | Two edits |
| `tests/test_api/test_health.py` | expand existing | Add ~7 tests |
| `tests/test_middleware/test_error_handler.py` | expand existing | Add ~4 tests |
| `tests/test_core/test_database.py` | existing file | Add ~4 tests |

---

## Test Requirements

### `tests/test_api/test_health.py` — 7 new tests

```python
# 1. DB connected → status: healthy, database: connected, HTTP 200
def test_health_db_connected():
    # mock engine.connect().__enter__.execute to succeed
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "connected"
    assert response.status_code == 200

# 2. DB unreachable (OperationalError) → status: degraded, database: unreachable, HTTP 200
def test_health_db_operational_error():
    # mock engine.connect() to raise OperationalError
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unreachable"
    assert response.status_code == 200  # Azure probe must still pass

# 3. DB unreachable (InterfaceError) → same as above
def test_health_db_interface_error():
    ...

# 4. Response always HTTP 200 even when DB is down
def test_health_always_returns_200_when_db_down():
    assert response.status_code == 200

# 5. Response includes expected fields
def test_health_response_fields():
    assert all(k in data for k in ("status", "service", "version", "timestamp", "database"))

# 6. Existing test: status == "healthy" when DB is OK (update existing test_health_check)
# Update test_health_check to mock DB and assert database == "connected"

# 7. Health alerts endpoint unaffected
def test_health_alerts_still_works():
    ...
```

### `tests/test_middleware/test_error_handler.py` — 4 new tests

```python
# 1. OperationalError → 503
def test_sqlalchemy_operational_error_returns_503():
    from sqlalchemy.exc import OperationalError
    exc = OperationalError("connection refused", None, None)
    ...
    assert resp.status_code == 503
    assert resp.json()["error"] == "database_unavailable"

# 2. InterfaceError → 503
def test_sqlalchemy_interface_error_returns_503():
    ...

# 3. SQLAlchemy error records "database" in alerting (not "unhandled")
def test_sqlalchemy_error_records_database_component():
    from app.core.alerting import get_alert_status
    ...
    assert get_alert_status().get("database", 0) == 1
    assert get_alert_status().get("unhandled", 0) == 0

# 4. Response includes request_id
def test_sqlalchemy_error_includes_request_id():
    ...
    assert "request_id" in resp.json()
```

### `tests/test_core/test_database.py` — 4 new tests

```python
# 1. get_db() rolls back on exception
def test_get_db_rollback_on_exception():
    mock_session = MagicMock()
    mock_factory = MagicMock(return_value=mock_session)
    gen = get_db_with_factory(mock_factory)
    next(gen)
    with pytest.raises(ValueError):
        gen.throw(ValueError("boom"))
    mock_session.rollback.assert_called_once()

# 2. get_db() always closes the session
def test_get_db_closes_on_exception():
    ...
    mock_session.close.assert_called_once()

# 3. Engine has pool_recycle set
def test_engine_has_pool_recycle():
    reset_engine()
    engine = get_engine()
    assert engine.pool._recycle == 1800

# 4. Engine connect_args has connect_timeout
def test_engine_has_connect_timeout():
    reset_engine()
    engine = get_engine()
    assert engine.dialect.create_connect_args(engine.url)[1].get("connect_timeout") == 10
```

**Expected new test count: ~15 → total ~445**

---

## Dependencies

- No dependency on other open stories
- SCRUM-67 (SQL optimisation) also touches `app/core/database.py` — coordinate so SCRUM-67 builds on top of this story's `get_db()` rollback change and `connect_args`

---

## Risks & Notes

| Risk | Mitigation |
|------|-----------|
| Health probe adds DB latency (target < 200ms) | `connect_timeout: 10` caps worst case; `pool_pre_ping` means most probes reuse existing connection |
| `connect_args={"connect_timeout": 10}` is PostgreSQL-specific (psycopg2) | All environments use PostgreSQL — acceptable |
| Existing `test_health_check` asserts `status == "healthy"` hardcoded | Update that test to mock DB connection; it will now need `database` field assertion too |
| `pool_recycle` added to existing singleton engine | `reset_engine()` is called in test fixtures — no side effects |
