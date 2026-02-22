"""Fallback agent for general / unclassified queries."""
import logging
from typing import Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.usage import UsageLimits
from app.agents.base import BaseAgent, AgentResponse
from app.core.config import get_settings

logger = logging.getLogger(__name__)

GENERAL_PROMPT = """You are a helpful shopping assistant for SmartShop AI.
For queries you cannot handle with specific product data, provide a brief helpful response
and redirect the user toward product search, recommendations, reviews, price comparison,
or policy questions. Keep it to 2-3 sentences."""

class _Answer(BaseModel):
    answer: str = Field(description="Brief helpful response")

class GeneralResponseAgent(BaseAgent):
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        super().__init__(name="general-agent")
        self._llm: Agent = Agent(model=OpenAIModel(model_name or settings.OPENAI_MODEL),
                                  output_type=_Answer, instructions=GENERAL_PROMPT)

    async def process(self, query: str, context: dict[str, Any]) -> AgentResponse:
        try:
            result = await self._llm.run(query, usage_limits=UsageLimits(request_limit=5))
            return AgentResponse(success=True,
                data={"answer": result.output.answer, "agent": self.name})
        except Exception as exc:
            logger.error("GeneralResponseAgent failed: %s", exc)
            return AgentResponse(success=True, data={
                "answer": ("I'm here to help with product recommendations, reviews, "
                           "price comparisons, and store policies. What can I help you with?"),
                "agent": self.name})
