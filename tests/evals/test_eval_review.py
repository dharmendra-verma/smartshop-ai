"""Eval tests for ReviewSummarizationAgent — summary quality and sentiment accuracy.

Tests call the real agent with a mocked DB seeded with SAMPLE_REVIEWS and judge
responses on relevance (addresses the product asked about), correctness (sentiment
and ratings are accurate), reasoning quality (summary is structured and balanced),
and helpfulness (user can make an informed decision).

Running
-------
    RUN_EVALS=1 pytest tests/evals/test_eval_review.py -v -s
"""

import pytest

from app.agents.dependencies import AgentDependencies
from app.agents.review.agent import ReviewSummarizationAgent
from app.core.config import get_settings

from tests.evals.conftest import (
    SAMPLE_PRODUCTS,
    SAMPLE_REVIEWS,
    format_agent_response,
    make_mock_db,
)
from tests.evals.judge import LLMJudge

pytestmark = pytest.mark.eval


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def agent() -> ReviewSummarizationAgent:
    return ReviewSummarizationAgent()


@pytest.fixture
def deps() -> AgentDependencies:
    """DB seeded with both products and reviews."""
    db = make_mock_db(products=SAMPLE_PRODUCTS, reviews=SAMPLE_REVIEWS)
    return AgentDependencies(db=db, settings=get_settings())


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _eval(agent, deps, judge, query, context_extras=None, min_overall=0.65):
    ctx = {"deps": deps, **(context_extras or {})}
    result = await agent.process(query, context=ctx)
    response_text = format_agent_response(result, "review")

    print(f"\nQuery: {query!r}")
    print(f"Response:\n{response_text}\n")

    score = await judge.evaluate(
        query=query,
        response=response_text,
        agent_type="review",
        context=(
            "The agent should summarise customer reviews, cite sentiment (positive/negative/neutral), "
            "mention average rating, list pros and cons, and give a clear recommendation."
        ),
    )
    print(f"Score: {score}")

    assert result.success, f"Agent returned failure: {result.error}"
    assert score.overall >= min_overall, (
        f"Review summary quality below threshold: {score.overall:.2f} (min={min_overall})\n"
        f"Explanation: {score.explanation}\n"
        f"Full response:\n{response_text}"
    )
    return score


# ---------------------------------------------------------------------------
# Core quality tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_summary_sony_headphones(agent, deps, judge: LLMJudge):
    """Agent should produce a balanced summary for Sony WH-1000XM5 reviews."""
    score = await _eval(
        agent, deps, judge,
        query="What do customers say about the Sony WH-1000XM5 headphones?",
        context_extras={"product_id": "PROD006"},
        min_overall=0.65,
    )
    assert score.relevance >= 0.60


@pytest.mark.asyncio
async def test_review_mentions_both_positives_and_negatives(agent, deps, judge: LLMJudge):
    """Agent should surface both pros and cons, not just praise."""
    ctx = {"deps": deps, "product_id": "PROD006"}
    result = await agent.process(
        "Are there any complaints about the Sony WH-1000XM5?",
        context=ctx,
    )
    response_text = format_agent_response(result, "review")
    print(f"\nResponse:\n{response_text}")

    score = await judge.evaluate(
        query="Are there any complaints about the Sony WH-1000XM5?",
        response=response_text,
        agent_type="review",
        context=(
            "Response must mention negative feedback (e.g. cheap case, sensitive touch controls) "
            "while being balanced."
        ),
    )
    print(f"Score: {score}")
    assert result.success
    assert score.overall >= 0.60
    # Helpfulness is key here — user wants to know what's wrong with the product
    assert score.helpfulness >= 0.55


@pytest.mark.asyncio
async def test_review_addresses_battery_query(agent, deps, judge: LLMJudge):
    """When user asks about battery, summary should highlight battery-related feedback."""
    score = await _eval(
        agent, deps, judge,
        query="What do reviewers say about the battery life of the Budget Phone X1?",
        context_extras={"product_id": "PROD001"},
        min_overall=0.60,
    )
    assert score.relevance >= 0.55


@pytest.mark.asyncio
async def test_review_correctness_matches_mock_data(agent, deps, judge: LLMJudge):
    """Agent's sentiment and rating summary should be consistent with the seeded reviews."""
    ctx = {"deps": deps, "product_id": "PROD006"}
    result = await agent.process(
        "Summarise all reviews for the Sony WH-1000XM5",
        context=ctx,
    )
    response_text = format_agent_response(result, "review")
    print(f"\nResponse:\n{response_text}")

    score = await judge.evaluate(
        query="Summarise all reviews for the Sony WH-1000XM5",
        response=response_text,
        agent_type="review",
        context=(
            "The seeded data has 3 reviews: ratings 5.0, 4.0, 3.0 — average ~4.0★. "
            "Most reviews are positive. One mentions touch control issues and cheap case. "
            "Response should be broadly consistent with this data."
        ),
    )
    print(f"Score: {score}")
    assert result.success
    assert score.correctness >= 0.55


@pytest.mark.asyncio
async def test_review_reasoning_is_structured(agent, deps, judge: LLMJudge):
    """Review summaries should show structured reasoning, not just raw sentences."""
    ctx = {"deps": deps, "product_id": "PROD006"}
    result = await agent.process(
        "Give me a detailed review analysis of Sony WH-1000XM5",
        context=ctx,
    )
    response_text = format_agent_response(result, "review")
    print(f"\nResponse:\n{response_text}")

    score = await judge.evaluate(
        query="Give me a detailed review analysis of Sony WH-1000XM5",
        response=response_text,
        agent_type="review",
        context="A structured analysis should have clear sections: pros, cons, rating, verdict.",
    )
    print(f"Score: {score}")
    assert result.success
    assert score.reasoning_quality >= 0.55


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_no_reviews_handled_gracefully(judge: LLMJudge):
    """Agent should handle product with no reviews gracefully."""
    db = make_mock_db(products=SAMPLE_PRODUCTS, reviews=[])
    deps = AgentDependencies(db=db, settings=get_settings())
    agent = ReviewSummarizationAgent()

    result = await agent.process(
        "What do customers say about the UltraBook Pro 15?",
        context={"deps": deps, "product_id": "PROD004"},
    )
    response_text = format_agent_response(result, "review")
    print(f"\nNo-reviews response:\n{response_text}")

    # Should not crash — may return success or a graceful error
    assert isinstance(result.success, bool)
    if result.success:
        score = await judge.evaluate(
            query="What do customers say about the UltraBook Pro 15?",
            response=response_text,
            agent_type="review",
            context="No reviews available — response should gracefully inform the user.",
        )
        print(f"Score: {score}")
        assert score.relevance >= 0.45  # Should at least address the query


@pytest.mark.asyncio
async def test_review_missing_deps_returns_error(agent):
    """Without deps, agent should return a clean failure."""
    result = await agent.process("Summarise reviews for Sony headphones", context={})
    assert result.success is False
    assert result.error is not None
