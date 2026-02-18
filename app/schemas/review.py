"""Pydantic schemas for Review Summarization API."""

from pydantic import BaseModel, Field
from typing import Optional


class ReviewSummarizationRequest(BaseModel):
    """POST /api/v1/reviews/summarize request body."""
    query: str = Field(
        ...,
        description="Natural language query, e.g. 'Summarize reviews for iPhone 15'",
        min_length=3,
        max_length=500,
    )
    product_id: Optional[str] = Field(
        default=None,
        description="Optional: supply product_id directly to skip name resolution",
        max_length=20,
    )
    max_reviews: int = Field(
        default=20,
        ge=5,
        le=50,
        description="Max review samples sent to LLM (5-50)",
    )


class SentimentTheme(BaseModel):
    """A single extracted theme with confidence score."""
    theme: str = Field(description="Short theme description, e.g. 'Battery life'")
    confidence: float = Field(ge=0.0, le=1.0, description="0.0-1.0 confidence score")
    example_quote: Optional[str] = Field(
        default=None,
        description="Representative quote from reviews supporting this theme",
    )


class RatingDistribution(BaseModel):
    """Count of reviews per star rating."""
    one_star: int = 0
    two_star: int = 0
    three_star: int = 0
    four_star: int = 0
    five_star: int = 0


class ReviewSummarizationResponse(BaseModel):
    """POST /api/v1/reviews/summarize response."""
    product_id: str
    product_name: str
    total_reviews: int
    sentiment_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall sentiment: 0.0 (very negative) to 1.0 (very positive)",
    )
    average_rating: float = Field(ge=0.0, le=5.0)
    rating_distribution: RatingDistribution
    positive_themes: list[SentimentTheme] = Field(
        description="Top 3 positive themes extracted from reviews",
    )
    negative_themes: list[SentimentTheme] = Field(
        description="Top 3 negative themes extracted from reviews",
    )
    overall_summary: str = Field(
        description="2-3 sentence narrative summary of what customers say",
    )
    cached: bool = Field(
        default=False,
        description="True if result was served from cache",
    )
    agent: str = "review-summarization-agent"
