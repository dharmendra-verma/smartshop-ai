"""FAQ & Policy Agent with RAG."""
import logging
from dataclasses import dataclass
from typing import Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from app.agents.base import BaseAgent, AgentResponse
from app.agents.dependencies import AgentDependencies
from app.agents.policy.prompts import SYSTEM_PROMPT
from app.agents.policy import tools
from app.core.config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class PolicyDependencies(AgentDependencies):
    """Extends AgentDependencies with the FAISS vector store."""
    vector_store: Any = None  # PolicyVectorStore

class _PolicyAnswer(BaseModel):
    answer:     str = Field(description="Direct answer to the policy question")
    sources:    list[str] = Field(description="Policy section names/types cited")
    confidence: str = Field(description="'high', 'medium', or 'low'")

def _build_agent(model_name: str) -> Agent:
    agent: Agent[PolicyDependencies, _PolicyAnswer] = Agent(
        model=OpenAIModel(model_name),
        deps_type=PolicyDependencies,
        output_type=_PolicyAnswer,
        instructions=SYSTEM_PROMPT,
    )
    agent.tool(tools.retrieve_policy_sections)
    return agent

_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        from app.agents.policy.vector_store import PolicyVectorStore
        _vector_store = PolicyVectorStore()
    return _vector_store

class PolicyAgent(BaseAgent):
    """FAQ & Policy agent — RAG over store policies via FAISS + GPT-4o-mini."""

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        super().__init__(name="policy-agent")
        self._agent = _build_agent(model_name or settings.OPENAI_MODEL)

    async def process(self, query: str, context: dict[str, Any]) -> AgentResponse:
        deps: AgentDependencies = context.get("deps")
        if deps is None:
            return AgentResponse(success=False, data={},
                error="AgentDependencies not provided in context['deps']")

        vector_store = context.get("vector_store") or get_vector_store()
        policy_deps  = PolicyDependencies(db=deps.db, settings=deps.settings,
                                          vector_store=vector_store)
        try:
            result = await self._agent.run(query, deps=policy_deps)
            ans: _PolicyAnswer = result.output
            return AgentResponse(success=True, data={
                "query": query, "answer": ans.answer, "sources": ans.sources,
                "confidence": ans.confidence, "agent": self.name,
            })
        except Exception as exc:
            logger.error("PolicyAgent failed: %s", exc, exc_info=True)
            return AgentResponse(success=False, data={},
                error=f"Policy agent error: {str(exc)}")
