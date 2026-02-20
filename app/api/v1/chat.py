"""Unified chat endpoint."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.orchestrator.orchestrator import get_orchestrator
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.session.session_manager import get_session_manager, build_enriched_query

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse, status_code=200)
async def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """
    Unified chat endpoint. Classifies intent and routes to the appropriate agent.
    """
    manager = get_session_manager()

    # Resolve or create session
    session_id = request.session_id or manager.create_session()

    # Retrieve history and build enriched query
    history = manager.get_history(session_id)
    enriched_query = build_enriched_query(request.message, history)

    # Orchestrate (SCRUM-16)
    deps = AgentDependencies.from_db(db)
    context = {"deps": deps, "max_results": request.max_results or 5, "session_id": session_id}

    orchestrator = get_orchestrator()
    agent_response, intent_result = await orchestrator.handle(enriched_query, context)

    if not agent_response.success:
        raise HTTPException(status_code=500, detail=agent_response.error)

    # Persist turn (store original user query, not enriched)
    answer = agent_response.data.get("answer") or str(agent_response.data)
    manager.append_turn(session_id, request.message, answer)

    return ChatResponse(
        session_id=session_id,
        message=request.message,
        intent=intent_result.intent.value,
        confidence=intent_result.confidence,
        entities={"product_name": intent_result.product_name, "category": intent_result.category,
                  "max_price": intent_result.max_price, "min_price": intent_result.min_price},
        agent_used=agent_response.data.get("agent", "unknown"),
        response=agent_response.data,
        success=True,
    )

@router.delete("/chat/session/{session_id}", status_code=204)
async def clear_session(session_id: str):
    """Clear conversation history for a session."""
    manager = get_session_manager()
    manager.clear(session_id)
