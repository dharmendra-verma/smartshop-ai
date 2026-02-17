"""Health check endpoints."""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "SmartShop AI",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to SmartShop AI - Your AI-Powered Shopping Assistant",
        "docs": "/docs",
        "health": "/health"
    }
