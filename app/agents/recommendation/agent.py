"""Product Recommendation Agent using pydantic-ai."""

import logging
from typing import Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from app.agents.base import BaseAgent, AgentResponse
from app.agents.dependencies import AgentDependencies
from app.agents.recommendation.prompts import SYSTEM_PROMPT
from app.agents.recommendation import tools
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class _ProductResult(BaseModel):
    """Internal: a single product the LLM has selected."""
    product_id: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str


class _RecommendationOutput(BaseModel):
    """Internal: the full structured output from pydantic-ai."""
    recommendations: list[_ProductResult]
    reasoning_summary: str


def _build_agent(model_name: str) -> Agent:
    """Build the pydantic-ai Agent. Called once at startup."""
    model = OpenAIModel(model_name)
    agent: Agent[AgentDependencies, _RecommendationOutput] = Agent(
        model=model,
        deps_type=AgentDependencies,
        output_type=_RecommendationOutput,
        instructions=SYSTEM_PROMPT,
    )
    agent.tool(tools.search_products_by_filters)
    agent.tool(tools.get_product_details)
    agent.tool(tools.get_categories)
    return agent


class RecommendationAgent(BaseAgent):
    """
    Product recommendation agent.

    Wraps a pydantic-ai Agent internally while satisfying the BaseAgent
    contract so the Orchestrator can route to it uniformly.
    """

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        model = model_name or settings.OPENAI_MODEL
        super().__init__(name="recommendation-agent")
        self._agent = _build_agent(model)

    async def process(
        self,
        query: str,
        context: dict[str, Any],
    ) -> AgentResponse:
        """
        Process a recommendation query.

        Args:
            query: Natural language query, e.g. "budget smartphones under $500"
            context: Must contain 'deps': AgentDependencies instance.
                     May also contain 'max_results': int (default 5).
        """
        deps: AgentDependencies = context.get("deps")
        if deps is None:
            return AgentResponse(
                success=False,
                data={},
                error="AgentDependencies not provided in context['deps']",
            )

        max_results: int = context.get("max_results", 5)
        structured_hints = context.get("structured_hints", {})
        enriched_query = _build_enriched_query(query, structured_hints, max_results)

        try:
            result = await self._agent.run(enriched_query, deps=deps)
            output: _RecommendationOutput = result.output

            recommendations = _hydrate_recommendations(output, deps)

            return AgentResponse(
                success=True,
                data={
                    "query": query,
                    "recommendations": recommendations,
                    "total_found": len(recommendations),
                    "reasoning_summary": output.reasoning_summary,
                    "agent": self.name,
                },
                metadata={
                    "model": str(self._agent.model),
                },
            )
        except Exception as exc:
            logger.error("RecommendationAgent failed: %s", exc, exc_info=True)
            return AgentResponse(
                success=False,
                data={},
                error=f"Recommendation agent error: {str(exc)}",
            )


def _build_enriched_query(
    query: str,
    hints: dict,
    max_results: int,
) -> str:
    """Append structured hints to the natural language query."""
    parts = [query]
    if hints.get("max_price"):
        parts.append(f"Maximum price: ${hints['max_price']}")
    if hints.get("min_price"):
        parts.append(f"Minimum price: ${hints['min_price']}")
    if hints.get("category"):
        parts.append(f"Category: {hints['category']}")
    if hints.get("min_rating"):
        parts.append(f"Minimum rating: {hints['min_rating']}/5")
    parts.append(f"Return top {max_results} recommendations.")
    return "\n".join(parts)


def _hydrate_recommendations(
    output: _RecommendationOutput,
    deps: AgentDependencies,
) -> list[dict]:
    """
    Fetch full product data from DB for each recommendation.
    Drops any product_id the LLM hallucinated (not in DB).
    """
    from app.models.product import Product
    results = []
    for rec in output.recommendations:
        product = deps.db.query(Product).filter(
            Product.id == rec.product_id
        ).first()
        if product:
            data = product.to_dict()
            data["relevance_score"] = rec.relevance_score
            data["reason"] = rec.reason
            results.append(data)
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results
