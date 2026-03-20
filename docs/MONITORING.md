# Monitoring & Observability

---

## Health Endpoints

### GET `/health`

Service health check with database connectivity probe.

```json
{"status": "healthy", "service": "SmartShop AI", "version": "1.0.0", "timestamp": "...", "database": "connected"}
```

When the database is unreachable, returns `"status": "degraded"` and `"database": "unreachable"` (HTTP 200).

### GET `/health/metrics`

Per-endpoint latency statistics from a rolling window of 200 samples.

```json
{
  "metrics": {
    "/api/v1/recommendations": {"p50_ms": 145.3, "p95_ms": 890.2, "sample_count": 200},
    "/api/v1/chat": {"p50_ms": 200.1, "p95_ms": 1200.5, "sample_count": 150}
  }
}
```

**Implementation:** `app/core/metrics.py` — `record_latency()` called by `RequestLoggingMiddleware`.

### GET `/health/alerts`

Component failure counts within a rolling 5-minute window.

```json
{
  "alerts": {
    "recommendation-agent": 2,
    "database": 0
  }
}
```

**Implementation:** `app/core/alerting.py` — `record_failure()` called by agents and middleware on errors.

---

## Metrics System

**File:** `app/core/metrics.py`

| Function | Description |
|----------|-------------|
| `record_latency(endpoint, latency_ms)` | Record a latency sample |
| `get_p95(endpoint)` | Get 95th percentile for an endpoint |
| `get_metrics_summary()` | Get all endpoint stats (P50, P95, count) |
| `reset_metrics()` | Clear all samples (for tests) |

- **Window:** 200 samples per endpoint (deque-based)
- **Computation:** Sorted percentile calculation
- **Collection:** Automatic via `RequestLoggingMiddleware` on every request

---

## Alerting System

**File:** `app/core/alerting.py`

| Setting | Value |
|---------|-------|
| Threshold | 10 failures |
| Window | 5 minutes (300 seconds) |
| Action | `CRITICAL` log message |

| Function | Description |
|----------|-------------|
| `record_failure(component)` | Record failure timestamp |
| `get_alert_status()` | Get current failure counts per component |
| `reset_alerts()` | Clear all records (for tests) |

When a component exceeds 10 failures in 5 minutes, a `CRITICAL` log is emitted:
```
CRITICAL - ALERT: component has N failures in 5min window
```

---

## Request Logging

**Middleware:** `app/middleware/logging_middleware.py`

Every request is logged with:

```
[a1b2c3d4] POST /api/v1/recommendations → 200 (145.3 ms)
```

Fields: request_id, method, path, status code, latency.

An `X-Process-Time-Ms` header is added to every response.

---

## Request Tracing

**Middleware:** `app/middleware/request_id.py`

Every request gets an 8-character UUID stored in:
- `request.state.request_id`
- `X-Request-Id` response header

Use this ID to correlate logs across a single request's lifecycle.

---

## Error Tracking

**Middleware:** `app/middleware/error_handler.py`

All exceptions are caught, mapped to HTTP status codes, and logged:

| Exception | Status | Triggers Alert |
|-----------|--------|---------------|
| `AgentRateLimitError` | 429 | Yes |
| `AgentTimeoutError` | 504 | Yes |
| `DatabaseError` | 503 | Yes |
| `SQLAlchemy OperationalError` | 503 | Yes (`database` component) |
| `SQLAlchemy InterfaceError` | 503 | Yes (`database` component) |
| `SmartShopError` | 500 | Yes |
| Unhandled | 500 | Yes |

---

## Performance Targets

| Endpoint | Target P95 | Notes |
|----------|-----------|-------|
| `GET /health` | < 10ms | Static response |
| `GET /api/v1/products` | < 100ms | DB query only |
| `POST /api/v1/chat` | < 3000ms | Includes LLM call |
| `POST /api/v1/recommendations` | < 3000ms | Includes LLM call |
| `POST /api/v1/reviews/summarize` | < 3000ms | Includes LLM call |
| `POST /api/v1/price/compare` | < 3000ms | Includes LLM call |
| `POST /api/v1/policy/ask` | < 3000ms | Includes embedding + LLM |

LLM-backed endpoints benefit from the 24-hour LLM cache — cached responses serve in < 50ms.

---

## Caching Layer Monitoring

| Cache | TTL | Key Prefix | Backend |
|-------|-----|------------|---------|
| LLM responses | 24h | `llm:` | Redis → TTLCache |
| Price data | 1h | `price:` | Redis → TTLCache |
| Session data | 30min | `session:` | Redis → TTLCache |
| Query fallback | 24h | in-memory | dict (process-local) |

No built-in cache hit/miss metrics endpoint yet — check logs for `LLM cache hit/miss` debug messages.

---

## File Logging

**Configuration:** Set `LOG_FILE` environment variable to enable file logging alongside console output.

| Setting | Value |
|---------|-------|
| Handler | `RotatingFileHandler` |
| Max size | 10 MB per file |
| Backup count | 5 files |
| Format | Same as console (with request IDs) |

When `LOG_FILE` is not set, only console logging is active (default behaviour).

---

## Database Connectivity Monitoring

| Check | Location | Behaviour |
|-------|----------|-----------|
| Startup probe | `app/main.py` (lifespan) | `SELECT 1` on startup; `CRITICAL` log with masked DB host on failure |
| Health endpoint | `GET /health` | Live DB probe; returns `"degraded"` status if unreachable |
| Error middleware | `ErrorHandlerMiddleware` | Catches `OperationalError`/`InterfaceError` → 503 + `record_failure("database")` |
| Connection pool | `get_engine()` | `connect_timeout=10s`, `pool_recycle=1800s` |
| Session safety | `get_db()` | `rollback()` before `close()` on exceptions |

---

## Agent Routing Observability

| Feature | Detail |
|---------|--------|
| Confidence gating | Intent classifications below 0.6 confidence route to general agent |
| Hallucination tracking | Recommendation agent logs hallucinated product IDs and records `record_failure("hallucination")` |
| Classification failure flag | `classification_failed: bool` on `_IntentResult` distinguishes "classified as general" from "couldn't classify" |
| Session parse alerting | JSON parse failures on session data trigger `record_failure("session_parse")` |
