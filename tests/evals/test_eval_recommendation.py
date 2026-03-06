"""Eval tests for RecommendationAgent — response quality and reasoning.

Tests call the real RecommendationAgent with a mocked DB (no real DB needed)
and judge responses using an LLM judge on relevance, correctness, reasoning
quality, and helpfulness.

Running
-------
    RUN_EVALS=1 pytest tests/evals/test_eval_recommendation.py -v -s
"""

import pytest

from app.agents.dependencies import AgentDependencies
from app.agents.recommendation.agent import RecommendationAgent
from app.core.config import get_settings

from tests.evals.conftest import SAMPLE_PRODUCTS, format_agent_response, make_mock_db
from tests.evals.judge import LLMJudge

pytestmark = pytest.mark.eval


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def agent() -> RecommendationAgent:
    return RecommendationAgent()


@pytest.fixture
def deps() -> AgentDependencies:
    db = make_mock_db(products=SAMPLE_PRODUCTS)
    return AgentDependencies(db=db, settings=get_settings())


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _eval(agent, deps, judge, query, context_extras=None, min_overall=0.65):
    """Run agent, format response, judge it, assert threshold."""
    ctx = {"deps": deps, **(context_extras or {})}
    result = await agent.process(query, context=ctx)
    response_text = format_agent_response(result, "recommendation")

    print(f"\nQuery: {query!r}")
    print(f"Response:\n{response_text}\n")

    score = await judge.evaluate(
        query=query,
        response=response_text,
        agent_type="recommendation",
        context=(
            "The agent should recommend relevant products with prices, ratings, "
            "and clear reasons why each product matches the query."
        ),
    )
    print(f"Score: {score}")

    assert result.success, f"Agent returned failure: {result.error}"
    assert score.overall >= min_overall, (
        f"Response quality below threshold: {score.overall:.2f} (min={min_overall})\n"
        f"Explanation: {score.explanation}\n"
        f"Full response:\n{response_text}"
    )
    return score


# ---------------------------------------------------------------------------
# Core quality tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommendation_budget_smartphones(agent, deps, judge: LLMJudge):
    """Agent should recommend smartphones within the specified budget."""
    await _eval(
        agent,
        deps,
        judge,
        query="Find me budget smartphones under $300",
        context_extras={"max_price": 300.0, "category": "smartphones"},
        min_overall=0.65,
    )


@pytest.mark.asyncio
async def test_recommendation_college_laptop(agent, deps, judge: LLMJudge):
    """Agent should recommend suitable laptops for a college student use case."""
    await _eval(
        agent,
        deps,
        judge,
        query="What is a good laptop for a college student on a budget?",
        context_extras={"category": "laptops"},
        min_overall=0.65,
    )


@pytest.mark.asyncio
async def test_recommendation_premium_headphones(agent, deps, judge: LLMJudge):
    """Agent should recommend high-end headphones when quality is the priority."""
    await _eval(
        agent,
        deps,
        judge,
        query="I want the best noise-cancelling headphones available, price is not a concern",
        context_extras={"category": "headphones"},
        min_overall=0.65,
    )


@pytest.mark.asyncio
async def test_recommendation_provides_reasoning(agent, deps, judge: LLMJudge):
    """Agent reasoning quality should be strong — it should explain why products match."""
    ctx = {"deps": deps, "max_results": 3}
    result = await agent.process(
        "Recommend smartphones with the best camera", context=ctx
    )
    response_text = format_agent_response(result, "recommendation")

    print(f"\nResponse:\n{response_text}")

    score = await judge.evaluate(
        query="Recommend smartphones with the best camera",
        response=response_text,
        agent_type="recommendation",
        context="Response must explain WHY each product has a good camera.",
    )
    print(f"Score: {score}")

    assert result.success
    assert score.reasoning_quality >= 0.55, (
        f"Reasoning quality too low: {score.reasoning_quality:.2f}\n"
        f"Explanation: {score.explanation}"
    )


@pytest.mark.asyncio
async def test_recommendation_relevance_to_query(agent, deps, judge: LLMJudge):
    """Response relevance should be high for a well-specified query."""
    score = await _eval(
        agent,
        deps,
        judge,
        query="Show me headphones under $100",
        context_extras={"category": "headphones", "max_price": 100.0},
        min_overall=0.60,
    )
    assert (
        score.relevance >= 0.60
    ), f"Relevance too low: {score.relevance:.2f}\nExplanation: {score.explanation}"


# ---------------------------------------------------------------------------
# Comparison mode tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommendation_comparison_mode(agent, deps, judge: LLMJudge):
    """In comparison mode, agent should compare multiple products side-by-side."""
    score = await _eval(
        agent,
        deps,
        judge,
        query="Compare the best budget and premium smartphones",
        context_extras={"compare_mode": True, "category": "smartphones"},
        min_overall=0.60,
    )
    # Comparison responses should be particularly relevant and helpful
    assert score.relevance >= 0.55


# ---------------------------------------------------------------------------
# Error / edge case tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommendation_missing_deps_returns_error(agent):
    """Without AgentDependencies in context, agent should return a clean failure."""
    result = await agent.process("Find laptops", context={})
    assert result.success is False
    assert result.error is not None
    assert "AgentDependencies" in result.error


@pytest.mark.asyncio
async def test_recommendation_empty_result_is_handled_gracefully(judge: LLMJudge):
    """When no products match, agent should respond gracefully (not crash)."""
    # DB returns no products
    db = make_mock_db(products=[])
    deps = AgentDependencies(db=db, settings=get_settings())
    agent = RecommendationAgent()

    result = await agent.process(
        "Find gaming laptops under $200",  # unrealistically strict budget
        context={"deps": deps, "max_price": 200.0, "category": "laptops"},
    )
    response_text = format_agent_response(result, "recommendation")
    print(f"\nEmpty-result response:\n{response_text}")

    # Should not raise; response may not be great but should be coherent
    assert isinstance(result.success, bool)
    if result.success:
        score = await judge.evaluate(
            query="Find gaming laptops under $200",
            response=response_text,
            agent_type="recommendation",
            context="No products match this query — response should gracefully inform the user.",
        )
        print(f"Score: {score}")
        # Even an empty-result response should be relevant (it explains why nothing was found)
        assert score.relevance >= 0.50


# ---------------------------------------------------------------------------
# Consistency test: same query → similar response quality
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recommendation_response_consistency(agent, deps, judge: LLMJudge):
    """Same query called twice should produce responses of similar quality (both ≥ threshold)."""
    query = "Find me a smartphone with good battery life"
    ctx = {"deps": deps}

    scores = []
    for _ in range(2):
        result = await agent.process(query, context=ctx)
        response_text = format_agent_response(result, "recommendation")
        score = await judge.evaluate(query, response_text, "recommendation")
        scores.append(score)
        print(f"\nConsistency run → {score}")

    # Both runs should be above minimum quality
    for i, s in enumerate(scores):
        assert (
            s.overall >= 0.55
        ), f"Consistency run {i+1} quality too low: {s.overall:.2f}"
