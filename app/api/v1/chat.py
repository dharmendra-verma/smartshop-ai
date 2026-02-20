"""Unified chat endpoint."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.orchestrator.orchestrator import get_orchestrator
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse, status_code=200)
async def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """
    Unified chat endpoint. Classifies intent and routes to the appropriate agent:
    recommendation/comparison → RecommendationAgent,
    review → ReviewSummarizationAgent,
    price → PriceComparisonAgent,
    policy → PolicyAgent,
    general → GeneralResponseAgent (fallback).
    """
    deps = AgentDependencies.from_db(db)
    context = {"deps": deps, "max_results": request.max_results, "session_id": request.session_id}

    orchestrator = get_orchestrator()
    response, intent_result = await orchestrator.handle(request.message, context)

    return ChatResponse(
        message=request.message,
        intent=intent_result.intent,
        confidence=intent_result.confidence,
        entities={"product_name": intent_result.product_name, "category": intent_result.category,
                  "max_price": intent_result.max_price, "min_price": intent_result.min_price},
        agent_used=response.data.get("agent", "unknown"),
        response=response.data,
        success=response.success,
        error=response.error,
    )
