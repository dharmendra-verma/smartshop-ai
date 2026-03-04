"""Review API endpoints — v1."""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.review import ReviewSummarizationAgent
from app.models.product import Product
from app.models.review import Review
from app.schemas.review import (
    ReviewSummarizationRequest,
    ReviewSummarizationResponse,
    SentimentTheme,
    RatingDistribution,
    ReviewItem,
    ReviewListResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])

_agent = ReviewSummarizationAgent()


@router.post("/summarize", response_model=ReviewSummarizationResponse)
async def summarize_reviews(
    request: ReviewSummarizationRequest,
    db: Session = Depends(get_db),
):
    """
    Summarize customer reviews for a product using AI.

    The agent fetches review stats and sample texts from the database,
    then extracts sentiment themes and generates a narrative summary.
    """
    deps = AgentDependencies.from_db(db)
    context = {
        "deps": deps,
        "product_id": request.product_id,
        "max_reviews": request.max_reviews,
    }

    response = await _agent.process(request.query, context)

    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)

    data = response.data

    return ReviewSummarizationResponse(
        product_id=data["product_id"],
        product_name=data["product_name"],
        total_reviews=data["total_reviews"],
        sentiment_score=data["sentiment_score"],
        average_rating=data["average_rating"],
        rating_distribution=RatingDistribution(**data["rating_distribution"]),
        positive_themes=[SentimentTheme(**t) for t in data["positive_themes"]],
        negative_themes=[SentimentTheme(**t) for t in data["negative_themes"]],
        overall_summary=data["overall_summary"],
        cached=data.get("cached", False),
        agent=data.get("agent", "review-summarization-agent"),
    )


@router.get("/{product_id}", response_model=ReviewListResponse)
def list_product_reviews(
    product_id: str,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List raw reviews for a product, newest first."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    query = (
        db.query(Review)
        .filter(Review.product_id == product_id)
        .order_by(Review.review_date.desc().nulls_last(), Review.review_id.desc())
    )
    total = query.count()
    reviews = query.offset(offset).limit(limit).all()

    return ReviewListResponse(
        product_id=product_id,
        product_name=product.name,
        average_rating=product.rating,
        reviews=[ReviewItem(**r.to_dict()) for r in reviews],
        total=total,
        limit=limit,
        offset=offset,
    )
