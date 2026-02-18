"""API v1 router — aggregates all v1 endpoints."""

from fastapi import APIRouter
from app.api.v1 import products

router = APIRouter()
router.include_router(products.router)
