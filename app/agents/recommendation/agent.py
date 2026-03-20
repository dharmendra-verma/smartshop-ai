"""Product Recommendation Agent using pydantic-ai."""

import logging
from typing import Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.usage import UsageLimits

from app.agents.base import BaseAgent, AgentResponse
from app.agents.dependencies import AgentDependencies
from app.agents.recommendation.prompts import SYSTEM_PROMPT
from app.agents.recommendation import tools
from app.agents.price.tools import search_products_by_name
from app.agents.utils import build_recommendation_query
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
    agent.tool(search_products_by_name)
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
        logger.info("RecommendationAgent invoked | query=%r", query[:100])
        deps: AgentDependencies = context.get("deps")
        if deps is None:
            return AgentResponse(
                success=False,
                data={},
                error="AgentDependencies not provided in context['deps']",
            )

        from app.core.llm_cache import get_cached_llm_response, set_cached_llm_response

        cached = get_cached_llm_response(self.name, query)
        if cached:
            logger.info("RecommendationAgent LLM cache hit | query=%r", query[:80])
            return cached

        max_results: int = context.get("max_results", 5)
        compare_mode: bool = context.get("compare_mode", False)
        structured_hints = context.get("structured_hints", {})
        enriched_query = build_recommendation_query(
            query, structured_hints, max_results
        )
        if compare_mode:
            enriched_query += (
                "\n\nCOMPARISON MODE: Focus on side-by-side comparison of the "
                "named products. Highlight differences in price, features, ratings, "
                "and value. Score each product relative to the others."
            )

        try:
            result = await self._agent.run(
                enriched_query, deps=deps, usage_limits=UsageLimits(request_limit=5)
            )
            self.log_usage(result)
            output: _RecommendationOutput = result.output

            recommendations, hallucinated_ids = _hydrate_recommendations(output, deps)
            requested_count = len(output.recommendations)
            returned_count = len(recommendations)

            if hallucinated_ids:
                from app.core.alerting import record_failure

                for pid in hallucinated_ids:
                    record_failure("hallucination")
                logger.warning(
                    "RecommendationAgent: %d hallucinated product IDs dropped: %s",
                    len(hallucinated_ids),
                    hallucinated_ids,
                )

            response = AgentResponse(
                success=True,
                data={
                    "query": query,
                    "recommendations": recommendations,
                    "total_found": returned_count,
                    "requested_count": requested_count,
                    "returned_count": returned_count,
                    "reasoning_summary": output.reasoning_summary,
                    "agent": self.name,
                },
                metadata={
                    "model": str(self._agent.model),
                    "hallucinated_ids": hallucinated_ids,
                },
            )
            set_cached_llm_response(self.name, query, response)
            return response
        except Exception as exc:
            return self._handle_agent_error(exc, query=query)


def _hydrate_recommendations(
    output: _RecommendationOutput,
    deps: AgentDependencies,
) -> tuple[list[dict], list[str]]:
    """
    Fetch full product data from DB for each recommendation.
    Drops any product_id the LLM hallucinated (not in DB).

    Returns:
        Tuple of (hydrated results, list of hallucinated product IDs).
    """
    from app.models.product import Product

    results = []
    hallucinated_ids = []
    for rec in output.recommendations:
        product = deps.db.query(Product).filter(Product.id == rec.product_id).first()
        if product:
            data = product.to_dict()
            data["relevance_score"] = rec.relevance_score
            data["reason"] = rec.reason
            results.append(data)
        else:
            hallucinated_ids.append(rec.product_id)
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results, hallucinated_ids
