"""Review Summarization Agent using pydantic-ai."""

import logging
from typing import Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.usage import UsageLimits

from app.agents.base import BaseAgent, AgentResponse
from app.agents.dependencies import AgentDependencies
from app.agents.review.prompts import SYSTEM_PROMPT
from app.agents.review import tools
from app.core.cache import get_review_cache
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class _ThemeResult(BaseModel):
    theme: str
    confidence: float = Field(ge=0.0, le=1.0)
    example_quote: str | None = None


class _ReviewSummaryOutput(BaseModel):
    """Typed output from pydantic-ai for review summarization."""
    product_id: str
    product_name: str
    total_reviews: int
    sentiment_score: float = Field(ge=0.0, le=1.0)
    average_rating: float
    rating_distribution: dict[str, int]
    positive_themes: list[_ThemeResult]
    negative_themes: list[_ThemeResult]
    overall_summary: str


def _build_agent(model_name: str) -> Agent:
    """Build the pydantic-ai Agent. Called once at module load."""
    model = OpenAIModel(model_name)
    agent: Agent[AgentDependencies, _ReviewSummaryOutput] = Agent(
        model=model,
        deps_type=AgentDependencies,
        output_type=_ReviewSummaryOutput,
        instructions=SYSTEM_PROMPT,
    )
    agent.tool(tools.find_product)
    agent.tool(tools.get_review_stats)
    agent.tool(tools.get_review_samples)
    return agent


class ReviewSummarizationAgent(BaseAgent):
    """
    Review summarization agent.

    Two-stage: fast DB stats (always fresh) + GPT theme extraction (cached per product).
    Follows the BaseAgent contract established in SCRUM-10 for Orchestrator compatibility.
    """

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        model = model_name or settings.OPENAI_MODEL
        super().__init__(name="review-summarization-agent")
        self._agent = _build_agent(model)
        self._cache = get_review_cache()

    def _cache_key(self, product_id: str) -> str:
        return f"review_summary:{product_id}"

    async def process(
        self,
        query: str,
        context: dict[str, Any],
    ) -> AgentResponse:
        """
        Summarize reviews for a product.

        Args:
            query: Natural language query, e.g. "Summarize reviews for iPhone 15"
            context: Must contain 'deps': AgentDependencies.
                     Optional 'product_id': str to skip name resolution.
                     Optional 'max_reviews': int (default 20).
        """
        deps: AgentDependencies = context.get("deps")
        if deps is None:
            return AgentResponse(
                success=False,
                data={},
                error="AgentDependencies not provided in context['deps']",
            )

        product_id: str | None = context.get("product_id")
        max_reviews: int = context.get("max_reviews", 20)

        enriched = _build_enriched_query(query, product_id, max_reviews)

        # Check cache (only when product_id known upfront)
        if product_id:
            cached = self._cache.get(self._cache_key(product_id))
            if cached:
                logger.debug("Cache hit for product_id=%s", product_id)
                cached["cached"] = True
                return AgentResponse(success=True, data=cached)

        try:
            result = await self._agent.run(enriched, deps=deps, usage_limits=UsageLimits(request_limit=15))
            output: _ReviewSummaryOutput = result.output

            data = {
                "product_id": output.product_id,
                "product_name": output.product_name,
                "total_reviews": output.total_reviews,
                "sentiment_score": output.sentiment_score,
                "average_rating": output.average_rating,
                "rating_distribution": output.rating_distribution,
                "positive_themes": [t.model_dump() for t in output.positive_themes],
                "negative_themes": [t.model_dump() for t in output.negative_themes],
                "overall_summary": output.overall_summary,
                "cached": False,
                "agent": self.name,
            }

            # Store in cache using resolved product_id
            cache_key = self._cache_key(output.product_id)
            self._cache.set(
                cache_key,
                data,
                ttl=deps.settings.CACHE_TTL_SECONDS,
            )

            return AgentResponse(
                success=True,
                data=data,
                metadata={"model": str(self._agent.model)},
            )

        except Exception as exc:
            logger.error("ReviewSummarizationAgent failed: %s", exc, exc_info=True)
            return AgentResponse(
                success=False,
                data={},
                error=f"Review summarization error: {str(exc)}",
            )


def _build_enriched_query(
    query: str,
    product_id: str | None,
    max_reviews: int,
) -> str:
    parts = [query]
    if product_id:
        parts.append(f"Product ID (use directly, skip find_product): {product_id}")
    parts.append(f"Fetch up to {max_reviews // 2} positive and {max_reviews // 2} negative reviews.")
    return "\n".join(parts)
