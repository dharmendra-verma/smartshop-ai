"""Pydantic schemas for data ingestion validation."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProductIngestionSchema(BaseModel):
    """Validates incoming product data before DB insertion."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    brand: Optional[str] = Field(None, max_length=100)
    category: str = Field(..., min_length=1, max_length=100)
    image_url: Optional[str] = Field(None, max_length=500)

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Ensure price is positive and has at most 2 decimal places."""
        if v <= 0:
            raise ValueError("Price must be positive")
        return round(v, 2)

    @field_validator("category")
    @classmethod
    def normalize_category(cls, v: str) -> str:
        """Normalize category to title case."""
        return v.strip().title()


class ReviewIngestionSchema(BaseModel):
    """Validates incoming review data before DB insertion."""

    product_id: int = Field(..., gt=0)
    rating: int = Field(..., ge=1, le=5)
    review_text: Optional[str] = None
    sentiment: Optional[str] = Field(None, pattern=r"^(positive|negative|neutral)$")

    @field_validator("review_text")
    @classmethod
    def clean_review_text(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            return v if len(v) > 0 else None
        return v


class PolicyIngestionSchema(BaseModel):
    """Validates incoming policy data before DB insertion."""

    category: str = Field(..., min_length=1, max_length=100)
    question: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    effective_date: date


class IngestionResult(BaseModel):
    """Tracks the outcome of a data ingestion run."""

    total_records: int = 0
    successful: int = 0
    failed: int = 0
    duplicates_skipped: int = 0
    errors: list[str] = Field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_records == 0:
            return 0.0
        return (self.successful / self.total_records) * 100
