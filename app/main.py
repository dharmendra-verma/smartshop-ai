"""SmartShop AI - Main FastAPI Application."""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api import health
from app.api.v1 import router as v1_router
from app.middleware.error_handler import ErrorHandlerMiddleware

# Initialize logging first
setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Driven Multi-Agent E-commerce Assistant",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware (order matters — error handler wraps everything)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router, tags=["health"])
app.include_router(v1_router)


@app.on_event("startup")
async def startup_event():
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Docs: http://%s:%s/docs", settings.API_HOST, settings.API_PORT)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down %s", settings.APP_NAME)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
