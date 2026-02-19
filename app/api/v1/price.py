"""Price comparison API endpoint."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.price.agent import PriceComparisonAgent
from app.schemas.price import PriceCompareRequest, PriceCompareResponse, ProductComparison, PricePoint

logger = logging.getLogger(__name__)
router = APIRouter()

_agent = PriceComparisonAgent()


@router.post("/price/compare", response_model=PriceCompareResponse, status_code=200)
async def compare_prices(
    request: PriceCompareRequest,
    db: Session = Depends(get_db),
) -> PriceCompareResponse:
    """
    Compare prices for products across multiple sources.

    Accepts a natural language query (e.g. "Compare Samsung S24 and Google Pixel 8"),
    looks up matching products, fetches competitor prices (with 1-hour cache),
    and returns a structured side-by-side comparison with best-deal identification.
    """
    deps = AgentDependencies.from_db(db)
    context = {
        "deps": deps,
        "max_results": request.max_results,
    }

    response = await _agent.process(request.query, context)

    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)

    data = response.data
    products = [
        ProductComparison(
            product_id=p["product_id"],
            name=p["name"],
            our_price=p["our_price"],
            competitor_prices=[PricePoint(**pp) for pp in p["competitor_prices"]],
            best_price=p["best_price"],
            best_source=p["best_source"],
            savings_pct=p["savings_pct"],
            rating=p.get("rating"),
            brand=p.get("brand"),
            category=p.get("category"),
            is_cached=p.get("is_cached", False),
        )
        for p in data["products"]
    ]

    return PriceCompareResponse(
        query=data["query"],
        products=products,
        best_deal=data["best_deal"],
        recommendation=data["recommendation"],
        total_compared=data["total_compared"],
        agent=data["agent"],
    )
