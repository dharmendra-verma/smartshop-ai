"""Global error handling middleware."""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catch-all middleware for unhandled exceptions."""

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error(
                "Unhandled exception: %s %s — %s",
                request.method,
                request.url.path,
                str(exc),
                exc_info=True,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "detail": "An unexpected error occurred. Please try again.",
                    "path": str(request.url.path),
                },
            )
