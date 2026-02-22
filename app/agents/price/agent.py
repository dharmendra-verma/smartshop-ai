"""Price Comparison Agent using pydantic-ai."""

import logging
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.usage import UsageLimits

from app.agents.base import BaseAgent, AgentResponse
from app.agents.dependencies import AgentDependencies
from app.agents.price.prompts import SYSTEM_PROMPT
from app.agents.price import tools
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class _PricePoint(BaseModel):
    """Price at a specific source."""
    source: str
    price: float
    is_best: bool = False


class _ProductComparison(BaseModel):
    """Comparison data for one product."""
    product_id: str
    name: str
    our_price: float
    competitor_prices: list[_PricePoint]
    best_price: float
    best_source: str
    savings_pct: float = Field(ge=0.0, description="Savings vs. highest price (%)")
    rating: float | None = None
    brand: str | None = None
    category: str | None = None
    is_cached: bool = False


class _ComparisonOutput(BaseModel):
    """Full structured output from the price comparison LLM."""
    products: list[_ProductComparison]
    best_deal: str = Field(description="Name of the product offering best overall value")
    recommendation: str = Field(description="2-3 sentence summary of the best deal and why")


def _build_agent(model_name: str) -> Agent:
    model = OpenAIModel(model_name)
    agent: Agent[AgentDependencies, _ComparisonOutput] = Agent(
        model=model,
        deps_type=AgentDependencies,
        output_type=_ComparisonOutput,
        instructions=SYSTEM_PROMPT,
    )
    agent.tool(tools.search_products_by_name)
    agent.tool(tools.get_competitor_prices)
    return agent


class PriceComparisonAgent(BaseAgent):
    """
    Price comparison agent.

    Looks up products in the catalog, fetches multi-source competitor prices
    (mock for MVP, swappable with live APIs), and uses GPT-4o-mini to produce
    a structured side-by-side comparison with best-deal identification.
    """

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        model = model_name or settings.OPENAI_MODEL
        super().__init__(name="price-comparison-agent")
        self._agent = _build_agent(model)

    async def process(self, query: str, context: dict[str, Any]) -> AgentResponse:
        deps: AgentDependencies = context.get("deps")
        if deps is None:
            return AgentResponse(
                success=False,
                data={},
                error="AgentDependencies not provided in context['deps']",
            )

        try:
            result = await self._agent.run(query, deps=deps, usage_limits=UsageLimits(request_limit=15))
            output: _ComparisonOutput = result.output

            return AgentResponse(
                success=True,
                data={
                    "query": query,
                    "products": [p.model_dump() for p in output.products],
                    "best_deal": output.best_deal,
                    "recommendation": output.recommendation,
                    "total_compared": len(output.products),
                    "agent": self.name,
                },
                metadata={"model": str(self._agent.model)},
            )
        except Exception as exc:
            logger.error("PriceComparisonAgent failed: %s", exc, exc_info=True)
            return AgentResponse(
                success=False,
                data={},
                error=f"Price comparison error: {str(exc)}",
            )
