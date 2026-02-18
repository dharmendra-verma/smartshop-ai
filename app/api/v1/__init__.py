"""API v1 router — aggregates all v1 endpoints."""

from fastapi import APIRouter
from app.api.v1 import products, recommendations, reviews

router = APIRouter()
router.include_router(products.router)
router.include_router(recommendations.router)
router.include_router(reviews.router)
