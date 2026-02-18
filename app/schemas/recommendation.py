"""Pydantic schemas for Recommendation API."""

from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional


class RecommendationRequest(BaseModel):
    """POST /api/v1/recommendations request body."""
    query: str = Field(
        ...,
        description="Natural language query, e.g. 'budget smartphones under $500'",
        min_length=3,
        max_length=500,
    )
    max_results: int = Field(default=5, ge=1, le=20)
    max_price: Optional[float] = Field(default=None, ge=0)
    min_price: Optional[float] = Field(default=None, ge=0)
    category: Optional[str] = Field(default=None, max_length=100)
    min_rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)


class ProductRecommendation(BaseModel):
    """A single recommended product with relevance context."""
    id: str
    name: str
    price: Decimal
    brand: Optional[str] = None
    category: str
    rating: Optional[float] = None
    stock: Optional[int] = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(description="Why this product was recommended")


class RecommendationResponse(BaseModel):
    """POST /api/v1/recommendations response."""
    query: str
    recommendations: list[ProductRecommendation]
    total_found: int
    reasoning_summary: str = Field(description="Agent's overall reasoning")
    agent: str = "recommendation-agent"
