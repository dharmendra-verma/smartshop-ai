"""Review Summarization API endpoint — v1."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.review import ReviewSummarizationAgent
from app.schemas.review import (
    ReviewSummarizationRequest,
    ReviewSummarizationResponse,
    SentimentTheme,
    RatingDistribution,
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
