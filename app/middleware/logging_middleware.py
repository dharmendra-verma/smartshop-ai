"""Per-request access logging middleware — logs method, path, status, latency."""

import logging
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request with method, path, status code, and latency in ms."""

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000

        request_id = getattr(request.state, "request_id", "—")
        logger.info(
            "[%s] %s %s → %d (%.1f ms)",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
        )

        response.headers["X-Process-Time-Ms"] = f"{latency_ms:.1f}"

        from app.core.metrics import record_latency
        record_latency(request.url.path, latency_ms)

        return response
