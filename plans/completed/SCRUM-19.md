# SCRUM-19 — Implement Comprehensive Error Handling and Resilience

**Jira:** https://projecttracking.atlassian.net/browse/SCRUM-19
**Priority:** Medium
**Status:** In Progress

---

## Story

> As a developer, I need robust error handling so that the system degrades gracefully when failures occur.

---

## Acceptance Criteria

- [ ] Try-catch blocks around all external API calls
- [ ] Retry logic with exponential backoff
- [ ] Circuit breaker pattern for agent failures
- [ ] Fallback responses for common errors
- [ ] User-friendly error messages (no stack traces in responses)
- [ ] Error logging with context (request ID, session ID, query)
- [ ] Alerting for critical failures
- [ ] Graceful degradation (cached data when APIs fail)

---

## Current State — What Already Exists

| Component | Status | Location |
|-----------|--------|----------|
| `CircuitBreaker` class | ✅ Exists | `app/agents/orchestrator/circuit_breaker.py` — 3 failures → OPEN, 30s recovery |
| `ErrorHandlerMiddleware` | ✅ Exists | `app/middleware/error_handler.py` — catches all unhandled exceptions |
| `RequestLoggingMiddleware` | ✅ Exists | `app/middleware/logging_middleware.py` — logs method/path/status/latency |
| Orchestrator fallback | ✅ Exists | `orchestrator.py` lines 44–55 — agent exception → general agent fallback |
| Agent-level try/except | ✅ Partial | `RecommendationAgent` has try/except but all exceptions treated identically |
| UI retry logic | ✅ Exists | `api_client.py` — 3 retries with exponential back-off (0.5s, 1s, 2s) |
| `setup_logging()` | ✅ Exists | `app/core/logging.py` — configures log level from settings |

**What is missing:**
- No request correlation ID (no way to trace a request across logs)
- No OpenAI-specific error handling (RateLimitError, TimeoutError not differentiated)
- No query-level fallback cache (when LLM fails, return cached prior result)
- Error messages sometimes leak internal details (e.g. raw exception strings)
- No alerting mechanism for critical failure thresholds
- DB errors not specifically caught/handled in API layer
- No structured error context in logs (session_id, query not logged at agent level)

---

## Technical Approach

### 1. Custom Exception Hierarchy — `app/core/exceptions.py` (NEW)

Define a clean exception hierarchy so each error type can be caught and handled appropriately:

```python
class SmartShopError(Exception):
    """Base exception for all SmartShop AI errors."""
    def __init__(self, message: str, user_message: str | None = None, context: dict | None = None):
        super().__init__(message)
        self.user_message = user_message or "Something went wrong. Please try again."
        self.context = context or {}

class AgentTimeoutError(SmartShopError): ...
class AgentRateLimitError(SmartShopError): ...
class AgentResponseError(SmartShopError): ...
class DatabaseError(SmartShopError): ...
class DataQualityError(SmartShopError): ...
class CacheError(SmartShopError): ...
```

### 2. Request ID Middleware — `app/middleware/request_id.py` (NEW)

Add a UUID to every request so all log lines for a single request share a correlation ID:

```python
class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]   # short 8-char ID
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
```

Add to `main.py` (after `ErrorHandlerMiddleware`, before `RequestLoggingMiddleware`).

### 3. Enhanced Error Handler — `app/middleware/error_handler.py` (MODIFY)

Extend to handle custom `SmartShopError` subtypes and return appropriate HTTP status codes:

```python
from app.core.exceptions import AgentRateLimitError, AgentTimeoutError, DatabaseError

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", "unknown")
        try:
            return await call_next(request)
        except AgentRateLimitError as exc:
            logger.warning("RateLimit [%s]: %s", request_id, exc)
            return JSONResponse(status_code=429, content={
                "error": "rate_limit", "detail": exc.user_message, "request_id": request_id
            })
        except AgentTimeoutError as exc:
            logger.warning("Timeout [%s]: %s", request_id, exc)
            return JSONResponse(status_code=504, content={
                "error": "timeout", "detail": exc.user_message, "request_id": request_id
            })
        except DatabaseError as exc:
            logger.error("Database [%s]: %s", request_id, exc, exc_info=True)
            return JSONResponse(status_code=503, content={
                "error": "service_unavailable", "detail": exc.user_message, "request_id": request_id
            })
        except Exception as exc:
            logger.error("Unhandled [%s]: %s", request_id, exc, exc_info=True)
            return JSONResponse(status_code=500, content={
                "error": "internal_error",
                "detail": "An unexpected error occurred. Please try again.",
                "request_id": request_id,
            })
```

### 4. OpenAI-Specific Error Handling in Agents (MODIFY each agent)

Each agent's `process()` method should catch OpenAI-specific exceptions and map them to SmartShop types. Pattern to apply to all agents:

```python
from openai import RateLimitError, APITimeoutError, APIError
from app.core.exceptions import AgentRateLimitError, AgentTimeoutError, AgentResponseError

try:
    result = await self._agent.run(...)
    ...
except RateLimitError as exc:
    logger.warning("%s: OpenAI rate limited — %s", self.name, exc)
    raise AgentRateLimitError(
        f"OpenAI rate limit: {exc}",
        user_message="I'm experiencing high demand. Please try again in a moment.",
        context={"agent": self.name, "query": query[:100]},
    )
except APITimeoutError as exc:
    logger.warning("%s: OpenAI timeout — %s", self.name, exc)
    raise AgentTimeoutError(
        f"OpenAI timeout: {exc}",
        user_message="The AI assistant is taking too long. Please try again.",
        context={"agent": self.name},
    )
except Exception as exc:
    logger.error("%s failed: %s", self.name, exc, exc_info=True)
    return AgentResponse(success=False, data={}, error=f"Service temporarily unavailable.")
```

Apply to: `RecommendationAgent`, `ReviewSummarizationAgent`, `PriceComparisonAgent`, `PolicyAgent`, `GeneralResponseAgent`.

### 5. Query-Level Fallback Cache — `app/core/query_cache.py` (NEW)

A simple cache keyed by `(agent_name, normalized_query)` that stores the last successful response. When an agent fails, return the cached result with a warning flag:

```python
_query_cache: dict[str, tuple[AgentResponse, float]] = {}
_QUERY_CACHE_TTL = 86400  # 24 hours

def get_cached_response(agent: str, query: str) -> AgentResponse | None:
    key = f"{agent}:{hashlib.md5(query.strip().lower().encode()).hexdigest()}"
    entry = _query_cache.get(key)
    if entry and time.time() < entry[1]:
        resp = entry[0]
        resp.metadata["from_cache"] = True
        resp.metadata["cache_warning"] = "Live data unavailable — showing cached result."
        return resp
    return None

def cache_response(agent: str, query: str, response: AgentResponse) -> None:
    key = f"{agent}:{hashlib.md5(query.strip().lower().encode()).hexdigest()}"
    _query_cache[key] = (response, time.time() + _QUERY_CACHE_TTL)
```

Integrate in Orchestrator: on agent exception, call `get_cached_response()` before falling back to general agent.

### 6. Critical Failure Alerting — `app/core/alerting.py` (NEW)

A lightweight in-process alerting module using a rolling counter. In production this would call PagerDuty/Slack, but for now logs a CRITICAL entry and exposes a `/health/alerts` endpoint:

```python
from collections import defaultdict, deque

_failure_counts: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
ALERT_THRESHOLD = 10   # more than 10 failures in 5 minutes → critical alert
ALERT_WINDOW_SECONDS = 300

def record_failure(component: str) -> None:
    _failure_counts[component].append(time.time())
    recent = [t for t in _failure_counts[component] if t > time.time() - ALERT_WINDOW_SECONDS]
    if len(recent) >= ALERT_THRESHOLD:
        logger.critical(
            "ALERT: %s has %d failures in the last %ds — check immediately!",
            component, len(recent), ALERT_WINDOW_SECONDS,
        )

def get_alert_status() -> dict:
    now = time.time()
    return {
        component: len([t for t in times if t > now - ALERT_WINDOW_SECONDS])
        for component, times in _failure_counts.items()
    }
```

Expose via `GET /health/alerts` in `app/api/health.py`.

### 7. DB Error Handling in API Layer

Wrap database operations in API routers with try/except to catch `sqlalchemy.exc.OperationalError` and return a clean 503 response rather than a 500 stack trace.

---

## File Map

| File | Action | What Changes |
|------|--------|-------------|
| `app/core/exceptions.py` | **CREATE** | Custom exception hierarchy |
| `app/core/query_cache.py` | **CREATE** | 24h query-level fallback cache |
| `app/core/alerting.py` | **CREATE** | Rolling-window failure counter + CRITICAL log alerting |
| `app/middleware/request_id.py` | **CREATE** | UUID request ID middleware |
| `app/middleware/error_handler.py` | **MODIFY** | Handle custom exception types; include request_id in response |
| `app/middleware/logging_middleware.py` | **MODIFY** | Include request_id in access log line |
| `app/main.py` | **MODIFY** | Add `RequestIdMiddleware` |
| `app/agents/recommendation/agent.py` | **MODIFY** | OpenAI-specific exception handling + query cache |
| `app/agents/review/agent.py` | **MODIFY** | OpenAI-specific exception handling + query cache |
| `app/agents/price/agent.py` | **MODIFY** | OpenAI-specific exception handling + query cache |
| `app/agents/policy/agent.py` | **MODIFY** | OpenAI-specific exception handling + query cache |
| `app/agents/orchestrator/orchestrator.py` | **MODIFY** | Use query cache as first fallback before general agent |
| `app/api/health.py` | **MODIFY** | Add `GET /health/alerts` endpoint |
| `app/api/v1/products.py` | **MODIFY** | Wrap DB calls with `DatabaseError` |
| `tests/test_agents/test_orchestrator.py` | **MODIFY** | Add tests for fallback cache + rate limit handling |
| `tests/test_middleware/test_error_handler.py` | **CREATE** | Test each exception type → correct HTTP status |
| `tests/test_middleware/test_request_id.py` | **CREATE** | Test request ID header presence |
| `tests/test_core/test_query_cache.py` | **CREATE** | Test cache hit/miss/expiry |
| `tests/test_core/test_alerting.py` | **CREATE** | Test alert threshold triggering |

---

## Test Requirements

**New test files (~18 tests total):**

`tests/test_middleware/test_error_handler.py` (~5 tests):
```
test_rate_limit_error_returns_429()
test_timeout_error_returns_504()
test_database_error_returns_503()
test_unhandled_exception_returns_500_no_stack_trace()
test_request_id_in_error_response()
```

`tests/test_middleware/test_request_id.py` (~3 tests):
```
test_request_id_header_added_to_response()
test_request_id_is_8_chars()
test_request_id_unique_per_request()
```

`tests/test_core/test_query_cache.py` (~5 tests):
```
test_cache_returns_none_on_miss()
test_cache_returns_response_on_hit()
test_cache_marks_response_with_from_cache_flag()
test_cache_expires_after_ttl()
test_cache_keyed_by_agent_and_query()
```

`tests/test_core/test_alerting.py` (~5 tests):
```
test_no_alert_below_threshold()
test_alert_logged_at_threshold()
test_get_alert_status_returns_counts()
test_old_failures_excluded_from_window()
test_multiple_components_tracked_independently()
```

**Expected new tests:** ~18
**Total after story:** ~330 (312 base + 18)

---

## Dependencies

- Depends on SCRUM-16 (Orchestrator in place) ✅
- Depends on SCRUM-17 (Session store in place) ✅
- No new Python packages needed (`openai` SDK already imported by pydantic-ai)
- `app/middleware/` already exists ✅

---

## Implementation Order

1. `exceptions.py` → foundation for everything else
2. `request_id.py` middleware + `main.py` registration
3. `error_handler.py` enhancement
4. `query_cache.py` + `alerting.py`
5. Agent modifications (all 4 agents)
6. Orchestrator modification
7. `health.py` alerts endpoint
8. API DB error wrapping
9. Tests
