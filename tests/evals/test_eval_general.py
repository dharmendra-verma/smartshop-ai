"""Eval tests for GeneralResponseAgent — fallback response quality.

GeneralResponseAgent handles all queries that don't match a specific agent
(greetings, off-topic questions, ambiguous queries). Tests check that the agent:
  - Redirects users to relevant shopping capabilities
  - Stays on-topic (does not pretend to be a general-purpose AI)
  - Provides helpful and friendly responses
  - Does NOT hallucinate capabilities it doesn't have

Running
-------
    RUN_EVALS=1 pytest tests/evals/test_eval_general.py -v -s
"""

import pytest

from app.agents.orchestrator.general_agent import GeneralResponseAgent

from tests.evals.conftest import format_agent_response
from tests.evals.judge import LLMJudge

pytestmark = pytest.mark.eval


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def agent() -> GeneralResponseAgent:
    return GeneralResponseAgent()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _eval(agent, judge, query, context=None, min_overall=0.65):
    result = await agent.process(query, context=context or {})
    response_text = format_agent_response(result, "general")

    print(f"\nQuery: {query!r}")
    print(f"Response:\n{response_text}\n")

    score = await judge.evaluate(
        query=query,
        response=response_text,
        agent_type="general",
        context=(
            "SmartShop AI is a shopping assistant. The general agent handles off-topic / greeting "
            "queries and should (a) be friendly and helpful, (b) redirect users to shopping "
            "capabilities (recommendations, reviews, price comparison, policies), "
            "(c) NOT pretend to handle topics outside shopping."
        ),
    )
    print(f"Score: {score}")

    assert result.success, f"Agent returned failure: {result.error}"
    assert score.overall >= min_overall, (
        f"General response quality below threshold: {score.overall:.2f} (min={min_overall})\n"
        f"Explanation: {score.explanation}\n"
        f"Response: {response_text}"
    )
    return score


# ---------------------------------------------------------------------------
# Greeting and on-boarding tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_general_greeting_redirects_to_shopping(agent, judge: LLMJudge):
    """Greeting should receive a friendly, shopping-focused response."""
    score = await _eval(
        agent, judge,
        query="Hello! What can you help me with?",
        min_overall=0.70,
    )
    assert score.relevance >= 0.65
    assert score.helpfulness >= 0.65


@pytest.mark.asyncio
async def test_general_casual_hi(agent, judge: LLMJudge):
    """Simple 'hi' should still get a helpful redirect to shopping features."""
    await _eval(agent, judge, query="Hi!", min_overall=0.65)


@pytest.mark.asyncio
async def test_general_introductory_question(agent, judge: LLMJudge):
    """User asking what the assistant does should get a clear overview."""
    score = await _eval(
        agent, judge,
        query="What kind of things can you help me with?",
        min_overall=0.70,
    )
    assert score.helpfulness >= 0.65


# ---------------------------------------------------------------------------
# Off-topic query handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_general_off_topic_query_stays_on_brand(agent, judge: LLMJudge):
    """Off-topic queries should be politely redirected to shopping."""
    result = await agent.process("What is the capital of France?", context={})
    response_text = format_agent_response(result, "general")

    print(f"\nOff-topic response:\n{response_text}")

    score = await judge.evaluate(
        query="What is the capital of France?",
        response=response_text,
        agent_type="general",
        context=(
            "This is off-topic for a shopping assistant. "
            "The response should politely acknowledge the question is outside its scope "
            "and redirect the user to shopping-related help."
        ),
    )
    print(f"Score: {score}")

    assert result.success
    # Should be relevant to being a shopping assistant (redirects)
    assert score.overall >= 0.55
    # Should NOT just answer as if it's a general-purpose AI
    # (we can't assert this structurally, but a good judge score implies appropriate redirect)


@pytest.mark.asyncio
async def test_general_weather_query_redirects(agent, judge: LLMJudge):
    """Weather queries should be redirected, not answered."""
    result = await agent.process("What's the weather like in London?", context={})
    response_text = format_agent_response(result, "general")

    print(f"\nWeather query response:\n{response_text}")

    score = await judge.evaluate(
        query="What's the weather like in London?",
        response=response_text,
        agent_type="general",
        context="Shopping assistant should redirect, not answer weather questions.",
    )
    print(f"Score: {score}")
    assert result.success
    assert score.overall >= 0.55


# ---------------------------------------------------------------------------
# Tone and helpfulness tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_general_response_is_concise(agent, judge: LLMJudge):
    """General agent responses should be brief (2-3 sentences per the system prompt)."""
    result = await agent.process("Hello!", context={})
    response_text = format_agent_response(result, "general")

    print(f"\nResponse:\n{response_text}")

    assert result.success
    # Rough length check — should not be an essay
    word_count = len(response_text.split())
    assert word_count <= 120, (
        f"Response too long ({word_count} words): {response_text}"
    )


@pytest.mark.asyncio
async def test_general_response_mentions_shopping_capabilities(agent, judge: LLMJudge):
    """Greeting response should mention at least one shopping capability."""
    result = await agent.process("Hi, who are you?", context={})
    response_text = format_agent_response(result, "general")

    print(f"\nResponse:\n{response_text}")

    # Check that the response mentions shopping-related topics
    keywords = [
        "recommend", "product", "review", "price", "policy",
        "shop", "compari", "budget", "help",
    ]
    response_lower = response_text.lower()
    matches = [kw for kw in keywords if kw in response_lower]

    assert result.success
    assert len(matches) >= 2, (
        f"Response doesn't mention shopping capabilities. "
        f"Keywords found: {matches}\nResponse: {response_text}"
    )


@pytest.mark.asyncio
async def test_general_helpfulness_score(agent, judge: LLMJudge):
    """Helpfulness should be at least 0.65 for an intro greeting."""
    score = await _eval(
        agent, judge,
        query="What can I do here?",
        min_overall=0.65,
    )
    assert score.helpfulness >= 0.60


# ---------------------------------------------------------------------------
# Fallback error response quality
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_general_fallback_message_quality(judge: LLMJudge):
    """The hardcoded fallback message (on agent error) should score reasonably."""
    # This simulates what the agent returns when it catches an exception
    fallback_message = (
        "I'm here to help with product recommendations, reviews, "
        "price comparisons, and store policies. What can I help you with?"
    )
    score = await judge.evaluate(
        query="Hello",
        response=fallback_message,
        agent_type="general",
        context="This is the hardcoded fallback message shown when the agent fails.",
    )
    print(f"\nFallback score: {score}")
    assert score.overall >= 0.60, (
        f"Fallback message quality too low: {score.overall:.2f}"
    )
    assert score.helpfulness >= 0.55


# ---------------------------------------------------------------------------
# Robustness: empty / minimal queries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["...", "???", "ok", "cool"])
async def test_general_handles_minimal_queries(agent, query, judge: LLMJudge):
    """Agent should not crash on minimal or punctuation-only queries."""
    result = await agent.process(query, context={})
    response_text = format_agent_response(result, "general")

    print(f"\nQuery: {query!r} → {response_text[:100]}...")

    # Should return a valid response (success or graceful failure)
    assert isinstance(result.success, bool)
    if result.success:
        assert len(response_text.strip()) > 0, "Response should not be empty"
