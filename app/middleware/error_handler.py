"""Global error handling middleware."""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import (
    AgentRateLimitError,
    AgentTimeoutError,
    DatabaseError,
    SmartShopError,
)
from app.core.alerting import record_failure

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch-all middleware for unhandled exceptions with custom type mapping."""

    async def dispatch(self, request: Request, call_next):
        request_id = getattr(request.state, "request_id", "unknown")
        try:
            return await call_next(request)
        except AgentRateLimitError as exc:
            logger.warning("RateLimit [%s]: %s", request_id, exc)
            record_failure("rate_limit")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit",
                    "detail": exc.user_message,
                    "request_id": request_id,
                },
            )
        except AgentTimeoutError as exc:
            logger.warning("Timeout [%s]: %s", request_id, exc)
            record_failure("timeout")
            return JSONResponse(
                status_code=504,
                content={
                    "error": "timeout",
                    "detail": exc.user_message,
                    "request_id": request_id,
                },
            )
        except DatabaseError as exc:
            logger.error("Database [%s]: %s", request_id, exc, exc_info=True)
            record_failure("database")
            return JSONResponse(
                status_code=503,
                content={
                    "error": "service_unavailable",
                    "detail": exc.user_message,
                    "request_id": request_id,
                },
            )
        except SmartShopError as exc:
            logger.error("SmartShopError [%s]: %s", request_id, exc, exc_info=True)
            record_failure("smartshop_error")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "detail": exc.user_message,
                    "request_id": request_id,
                },
            )
        except Exception as exc:
            logger.error("Unhandled [%s]: %s", request_id, exc, exc_info=True)
            record_failure("unhandled")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_error",
                    "detail": "An unexpected error occurred. Please try again.",
                    "request_id": request_id,
                },
            )
