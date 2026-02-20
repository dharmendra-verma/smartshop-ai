"""Pydantic schemas for Product API responses."""

from pydantic import BaseModel, ConfigDict
from decimal import Decimal
from datetime import datetime
from typing import Optional


class ProductResponse(BaseModel):
    """Single product API response schema."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    price: Decimal
    brand: Optional[str] = None
    category: str
    stock: Optional[int] = None
    rating: Optional[float] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None


class ProductListResponse(BaseModel):
    """Paginated product list response."""
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    pages: int
