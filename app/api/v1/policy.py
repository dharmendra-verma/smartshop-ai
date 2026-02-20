"""Policy FAQ API endpoint."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.policy.agent import PolicyAgent, get_vector_store
from app.schemas.policy import PolicyAskRequest, PolicyAskResponse

logger = logging.getLogger(__name__)
router = APIRouter()
_agent = PolicyAgent()

@router.post("/policy/ask", response_model=PolicyAskResponse, status_code=200)
async def ask_policy(request: PolicyAskRequest, db: Session = Depends(get_db)) -> PolicyAskResponse:
    """Answer a policy question using RAG (FAISS semantic search + GPT-4o-mini)."""
    deps = AgentDependencies.from_db(db)
    vs   = get_vector_store()

    if vs._index is None:
        from app.models.policy import Policy
        vs.load_or_build(db.query(Policy).all())

    response = await _agent.process(request.query, context={"deps": deps, "vector_store": vs})
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)

    return PolicyAskResponse(
        query=response.data["query"],   answer=response.data["answer"],
        sources=response.data["sources"], confidence=response.data["confidence"],
        agent=response.data["agent"],
    )
