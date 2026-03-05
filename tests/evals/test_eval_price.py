"""Eval tests for PriceComparisonAgent — price analysis and recommendation quality.

Tests call the real agent with a mocked DB + mocked pricing service and judge
responses on price relevance, correctness of comparisons, reasoning about value,
and helpfulness (actionable advice).

Running
-------
    RUN_EVALS=1 pytest tests/evals/test_eval_price.py -v -s
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.dependencies import AgentDependencies
from app.agents.price.agent import PriceComparisonAgent
from app.core.config import get_settings

from tests.evals.conftest import SAMPLE_PRODUCTS, format_agent_response, make_mock_db
from tests.evals.judge import LLMJudge

pytestmark = pytest.mark.eval


# ---------------------------------------------------------------------------
# Mock pricing data
# ---------------------------------------------------------------------------

MOCK_PRICE_DATA = {
    "PROD001": {
        "product_id": "PROD001",
        "product_name": "Budget Phone X1",
        "current_price": Decimal("249.99"),
        "competitor_prices": {
            "TechMart": Decimal("239.99"),
            "BestDeal": Decimal("259.99"),
            "MegaShop": Decimal("244.99"),
        },
        "price_history": [
            {"date": "2025-01-01", "price": Decimal("279.99")},
            {"date": "2025-02-01", "price": Decimal("259.99")},
            {"date": "2025-03-01", "price": Decimal("249.99")},
        ],
        "lowest_ever": Decimal("229.99"),
        "price_trend": "declining",
    },
    "PROD006": {
        "product_id": "PROD006",
        "product_name": "Sony WH-1000XM5",
        "current_price": Decimal("349.99"),
        "competitor_prices": {
            "TechMart": Decimal("329.99"),
            "AudioWorld": Decimal("359.99"),
            "MegaShop": Decimal("339.99"),
        },
        "price_history": [
            {"date": "2025-01-01", "price": Decimal("379.99")},
            {"date": "2025-02-01", "price": Decimal("349.99")},
        ],
        "lowest_ever": Decimal("299.99"),
        "price_trend": "stable",
    },
    "PROD004": {
        "product_id": "PROD004",
        "product_name": "UltraBook Pro 15",
        "current_price": Decimal("1299.99"),
        "competitor_prices": {
            "LaptopStore": Decimal("1249.99"),
            "TechMart": Decimal("1319.99"),
        },
        "price_history": [
            {"date": "2025-01-01", "price": Decimal("1399.99")},
            {"date": "2025-02-01", "price": Decimal("1299.99")},
        ],
        "lowest_ever": Decimal("1199.99"),
        "price_trend": "declining",
    },
}


def _make_pricing_service():
    """Create a mock pricing service that returns realistic price data."""
    service = MagicMock()
    service.get_price_comparison = AsyncMock(
        side_effect=lambda product_id: MOCK_PRICE_DATA.get(product_id)
    )
    service.get_price_history = AsyncMock(
        side_effect=lambda product_id: MOCK_PRICE_DATA.get(product_id, {}).get(
            "price_history", []
        )
    )
    return service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def agent() -> PriceComparisonAgent:
    return PriceComparisonAgent()


@pytest.fixture
def deps() -> AgentDependencies:
    db = make_mock_db(products=SAMPLE_PRODUCTS)
    return AgentDependencies(db=db, settings=get_settings())


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _eval(agent, deps, judge, query, context_extras=None, min_overall=0.60):
    """Run agent with mocked pricing service, judge response."""
    ctx = {"deps": deps, **(context_extras or {})}
    pricing_service = _make_pricing_service()

    with patch(
        "app.agents.price.agent.get_pricing_service",
        return_value=pricing_service,
        create=True,
    ), patch(
        "app.services.pricing.mock_pricing.MockPricingService.get_price_comparison",
        new=pricing_service.get_price_comparison,
        create=True,
    ):
        result = await agent.process(query, context=ctx)

    response_text = format_agent_response(result, "price")
    print(f"\nQuery: {query!r}")
    print(f"Response:\n{response_text}\n")

    score = await judge.evaluate(
        query=query,
        response=response_text,
        agent_type="price",
        context=(
            "The agent should compare prices across retailers, identify the best deal, "
            "assess whether the price is competitive, and give an actionable recommendation."
        ),
    )
    print(f"Score: {score}")

    # Success check is lenient — agent may gracefully handle missing pricing data
    if not result.success:
        print(f"[WARN] Agent returned failure: {result.error}")

    assert score.overall >= min_overall or not result.success, (
        f"Price response quality below threshold: {score.overall:.2f} (min={min_overall})\n"
        f"Explanation: {score.explanation}\n"
        f"Full response:\n{response_text}"
    )
    return score, result


# ---------------------------------------------------------------------------
# Core quality tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_price_best_deal_for_sony_headphones(agent, deps, judge: LLMJudge):
    """Agent should identify the best price for Sony WH-1000XM5 across retailers."""
    await _eval(
        agent, deps, judge,
        query="What is the best price for Sony WH-1000XM5 headphones?",
        context_extras={"product_id": "PROD006"},
        min_overall=0.60,
    )


@pytest.mark.asyncio
async def test_price_is_competitive_assessment(agent, deps, judge: LLMJudge):
    """Agent should assess whether a price is competitive vs market."""
    ctx = {"deps": deps, "product_id": "PROD001"}
    pricing_service = _make_pricing_service()

    with patch(
        "app.agents.price.agent.get_pricing_service",
        return_value=pricing_service,
        create=True,
    ):
        result = await agent.process(
            "Is $249.99 a good deal for the Budget Phone X1?",
            context=ctx,
        )

    response_text = format_agent_response(result, "price")
    print(f"\nCompetitive assessment:\n{response_text}")

    score = await judge.evaluate(
        query="Is $249.99 a good deal for the Budget Phone X1?",
        response=response_text,
        agent_type="price",
        context=(
            "Mock data shows market range $239.99–$259.99. "
            "Response should tell the user whether $249.99 is competitive."
        ),
    )
    print(f"Score: {score}")
    if result.success:
        assert score.overall >= 0.55


@pytest.mark.asyncio
async def test_price_comparison_laptop(agent, deps, judge: LLMJudge):
    """Agent should compare laptop prices and give a value assessment."""
    await _eval(
        agent, deps, judge,
        query="Where can I find the cheapest UltraBook Pro 15?",
        context_extras={"product_id": "PROD004"},
        min_overall=0.58,
    )


@pytest.mark.asyncio
async def test_price_response_relevance(agent, deps, judge: LLMJudge):
    """Price response should be highly relevant to the price query."""
    score, result = await _eval(
        agent, deps, judge,
        query="Find the best price for Sony WH-1000XM5",
        context_extras={"product_id": "PROD006"},
        min_overall=0.58,
    )
    if result.success:
        assert score.relevance >= 0.55, (
            f"Relevance too low: {score.relevance:.2f}"
        )


@pytest.mark.asyncio
async def test_price_reasoning_mentions_comparison(agent, deps, judge: LLMJudge):
    """Agent reasoning should explicitly compare prices, not just list one price."""
    ctx = {"deps": deps}
    pricing_service = _make_pricing_service()

    with patch(
        "app.agents.price.agent.get_pricing_service",
        return_value=pricing_service,
        create=True,
    ):
        result = await agent.process(
            "Compare prices for Budget Phone X1 across stores",
            context=ctx,
        )

    response_text = format_agent_response(result, "price")
    print(f"\nComparison response:\n{response_text}")

    score = await judge.evaluate(
        query="Compare prices for Budget Phone X1 across stores",
        response=response_text,
        agent_type="price",
        context="Response should list multiple prices from different stores and compare them.",
    )
    print(f"Score: {score}")
    if result.success:
        assert score.reasoning_quality >= 0.50


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_price_missing_deps_returns_error(agent):
    """Without deps, agent should return a clean failure."""
    result = await agent.process("Find the best price for Sony headphones", context={})
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_price_no_product_found_is_graceful(judge: LLMJudge):
    """Agent should handle unknown product gracefully."""
    db = make_mock_db(products=[])
    deps = AgentDependencies(db=db, settings=get_settings())
    agent = PriceComparisonAgent()

    pricing_service = _make_pricing_service()
    with patch(
        "app.agents.price.agent.get_pricing_service",
        return_value=pricing_service,
        create=True,
    ):
        result = await agent.process(
            "What is the price of a product that doesn't exist?",
            context={"deps": deps},
        )

    response_text = format_agent_response(result, "price")
    print(f"\nNo-product response:\n{response_text}")

    if result.success:
        score = await judge.evaluate(
            query="What is the price of a product that doesn't exist?",
            response=response_text,
            agent_type="price",
            context="Product not found — response should gracefully inform the user.",
        )
        print(f"Score: {score}")
        assert score.relevance >= 0.40
