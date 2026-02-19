"""Request/response schemas for the Price Comparison API."""

from typing import Optional
from pydantic import BaseModel, Field


class PriceCompareRequest(BaseModel):
    """Request body for POST /api/v1/price/compare."""
    query: str = Field(
        ..., min_length=3, max_length=500,
        description="Comparison query, e.g. 'Compare Samsung S24 and Google Pixel 8'"
    )
    max_results: int = Field(default=4, ge=1, le=10,
                              description="Max products to include in comparison")


class PricePoint(BaseModel):
    source: str
    price: float
    is_best: bool = False


class ProductComparison(BaseModel):
    product_id: str
    name: str
    our_price: float
    competitor_prices: list[PricePoint]
    best_price: float
    best_source: str
    savings_pct: float
    rating: Optional[float] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    is_cached: bool = False


class PriceCompareResponse(BaseModel):
    """Response body for POST /api/v1/price/compare."""
    query: str
    products: list[ProductComparison]
    best_deal: str
    recommendation: str
    total_compared: int
    agent: str
