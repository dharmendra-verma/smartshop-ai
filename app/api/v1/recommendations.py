"""Recommendation API endpoint — v1."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.recommendation import RecommendationAgent
from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    ProductRecommendation,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])

_agent = RecommendationAgent()


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
):
    """
    Get AI-powered product recommendations for a natural language query.

    The agent reasons over the product catalog and returns ranked recommendations
    with relevance scores and explanations.
    """
    deps = AgentDependencies.from_db(db)
    context = {
        "deps": deps,
        "max_results": request.max_results,
        "structured_hints": {
            "max_price": request.max_price,
            "min_price": request.min_price,
            "category": request.category,
            "min_rating": request.min_rating,
        },
    }

    response = await _agent.process(request.query, context)

    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)

    data = response.data
    recommendations = [
        ProductRecommendation(
            id=r["id"],
            name=r["name"],
            price=Decimal(str(r["price"])),
            brand=r.get("brand"),
            category=r["category"],
            rating=r.get("rating"),
            stock=r.get("stock"),
            relevance_score=r["relevance_score"],
            reason=r["reason"],
        )
        for r in data["recommendations"]
    ]

    return RecommendationResponse(
        query=data["query"],
        recommendations=recommendations,
        total_found=data["total_found"],
        reasoning_summary=data["reasoning_summary"],
        agent=data["agent"],
    )
