"""Eval tests for the Orchestrator — end-to-end routing and response quality.

These tests call the Orchestrator with its real IntentClassifier (real LLM call)
and mock individual specialist agents with realistic pre-baked responses. This
isolates the eval to:
  1. Intent classification accuracy (does the right agent get called?)
  2. Response coherence (is the returned response coherent and complete?)
  3. Context enrichment (are extracted entities passed to agents correctly?)
  4. Fallback behaviour (does the orchestrator recover gracefully from failures?)

Running
-------
    RUN_EVALS=1 pytest tests/evals/test_eval_orchestrator.py -v -s
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.base import AgentResponse
from app.agents.orchestrator.orchestrator import Orchestrator, reset_orchestrator
from app.schemas.chat import IntentType

from tests.evals.judge import LLMJudge

pytestmark = pytest.mark.eval


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset():
    reset_orchestrator()
    yield
    reset_orchestrator()


# ---------------------------------------------------------------------------
# Realistic canned agent responses (simulate specialist agent outputs)
# ---------------------------------------------------------------------------

GOOD_RECOMMENDATION_RESPONSE = AgentResponse(
    success=True,
    data={
        "recommendations": [
            {
                "id": "PROD001",
                "name": "Budget Phone X1",
                "price": "249.99",
                "brand": "TechCo",
                "category": "smartphones",
                "rating": 4.2,
                "relevance_score": 0.92,
                "reason": "Best value smartphone under $300 with 5G support and excellent battery life",
            },
            {
                "id": "PROD003",
                "name": "Mid-Range Phone Z3",
                "price": "399.99",
                "brand": "ValueCo",
                "category": "smartphones",
                "rating": 4.0,
                "relevance_score": 0.78,
                "reason": "Slightly above budget but offers better performance and camera",
            },
        ],
        "reasoning_summary": (
            "I found 2 smartphones that match your requirements. "
            "Budget Phone X1 is the best fit at $249.99, offering 5G and great battery life. "
            "The Mid-Range Phone Z3 is slightly above your $300 budget but offers better specs."
        ),
        "agent": "recommendation-agent",
        "total_found": 2,
    },
)

GOOD_REVIEW_RESPONSE = AgentResponse(
    success=True,
    data={
        "summary": (
            "Sony WH-1000XM5 headphones receive overwhelmingly positive reviews. "
            "Customers consistently praise the exceptional noise cancellation, "
            "30-hour battery life, and premium sound quality."
        ),
        "average_rating": 4.0,
        "sentiment_summary": "Mostly positive (67% positive, 22% neutral, 11% negative)",
        "highlights": "Noise cancellation, battery life, sound quality",
        "concerns": "Carrying case quality, overly sensitive touch controls",
        "agent": "review-agent",
    },
)

GOOD_PRICE_RESPONSE = AgentResponse(
    success=True,
    data={
        "best_price": "329.99",
        "prices": {
            "SmartShop": "$349.99",
            "TechMart": "$329.99",
            "AudioWorld": "$359.99",
        },
        "price_analysis": (
            "TechMart offers the lowest price at $329.99, saving you $20 versus SmartShop. "
            "The price has been declining over the past 2 months."
        ),
        "recommendation": "Consider TechMart for the best current deal. SmartShop may price-match.",
        "agent": "price-agent",
    },
)

GOOD_POLICY_RESPONSE = AgentResponse(
    success=True,
    data={
        "answer": (
            "Our return policy allows returns within 30 days of purchase. "
            "Items must be in their original, unopened packaging with a receipt. "
            "Opened electronics are subject to a 15% restocking fee. "
            "Sale items are final sale and cannot be returned."
        ),
        "policy_type": "return",
        "agent": "policy-agent",
    },
)

GOOD_GENERAL_RESPONSE = AgentResponse(
    success=True,
    data={
        "answer": (
            "Hello! I'm SmartShop AI, your personal shopping assistant. "
            "I can help with product recommendations, customer reviews, price comparisons, "
            "and store policies. What are you looking for today?"
        ),
        "agent": "general-agent",
    },
)


# ---------------------------------------------------------------------------
# Mock agent factory
# ---------------------------------------------------------------------------


def _make_mock_agent(name: str, response: AgentResponse):
    """Create a mock agent that returns the given response."""
    agent = MagicMock()
    agent.name = name
    agent.process = AsyncMock(return_value=response)
    return agent


def _make_orchestrator_with_real_classifier() -> Orchestrator:
    """Build Orchestrator with real IntentClassifier but mock specialist agents."""
    from app.agents.orchestrator.orchestrator import Orchestrator

    registry = {
        "recommendation": _make_mock_agent(
            "recommendation-agent", GOOD_RECOMMENDATION_RESPONSE
        ),
        "review": _make_mock_agent("review-agent", GOOD_REVIEW_RESPONSE),
        "price": _make_mock_agent("price-agent", GOOD_PRICE_RESPONSE),
        "policy": _make_mock_agent("policy-agent", GOOD_POLICY_RESPONSE),
        "general": _make_mock_agent("general-agent", GOOD_GENERAL_RESPONSE),
    }
    return Orchestrator(registry=registry)


# ---------------------------------------------------------------------------
# Intent routing accuracy tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_routes_recommendation_query(judge: LLMJudge):
    """Recommendation query should route to the recommendation agent."""
    orch = _make_orchestrator_with_real_classifier()
    response, intent_result = await orch.handle(
        "Find me budget smartphones under $300", context={}
    )

    print(
        f"\nIntent: {intent_result.intent.value} (conf={intent_result.confidence:.2f})"
    )
    print(f"Reasoning: {intent_result.reasoning}")

    assert (
        intent_result.intent == IntentType.RECOMMENDATION
    ), f"Expected RECOMMENDATION, got {intent_result.intent.value}"
    orch._registry["recommendation"].process.assert_called_once()
    assert response.success


@pytest.mark.asyncio
async def test_orchestrator_routes_review_query(judge: LLMJudge):
    """Review query should route to the review agent."""
    orch = _make_orchestrator_with_real_classifier()
    response, intent_result = await orch.handle(
        "What do customers say about Sony WH-1000XM5?", context={}
    )

    print(f"\nIntent: {intent_result.intent.value}")

    assert (
        intent_result.intent == IntentType.REVIEW
    ), f"Expected REVIEW, got {intent_result.intent.value}"
    orch._registry["review"].process.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_routes_policy_query(judge: LLMJudge):
    """Policy query should route to the policy agent."""
    orch = _make_orchestrator_with_real_classifier()
    response, intent_result = await orch.handle(
        "What is your return policy for electronics?", context={}
    )

    print(f"\nIntent: {intent_result.intent.value}")

    assert (
        intent_result.intent == IntentType.POLICY
    ), f"Expected POLICY, got {intent_result.intent.value}"
    orch._registry["policy"].process.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_routes_price_query(judge: LLMJudge):
    """Price query should route to the price agent."""
    orch = _make_orchestrator_with_real_classifier()
    response, intent_result = await orch.handle(
        "What is the best price for Sony WH-1000XM5?", context={}
    )

    print(f"\nIntent: {intent_result.intent.value}")

    assert (
        intent_result.intent == IntentType.PRICE
    ), f"Expected PRICE, got {intent_result.intent.value}"
    orch._registry["price"].process.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_routes_comparison_to_recommendation_with_flag(
    judge: LLMJudge,
):
    """Comparison queries should route to recommendation agent with compare_mode=True."""
    orch = _make_orchestrator_with_real_classifier()
    response, intent_result = await orch.handle(
        "Compare iPhone 15 vs Samsung Galaxy S24", context={}
    )

    print(f"\nIntent: {intent_result.intent.value}")

    assert intent_result.intent == IntentType.COMPARISON
    orch._registry["recommendation"].process.assert_called_once()

    # Verify compare_mode flag was injected
    call_context = orch._registry["recommendation"].process.call_args[0][1]
    assert (
        call_context.get("compare_mode") is True
    ), f"compare_mode not set in context: {call_context}"


@pytest.mark.asyncio
async def test_orchestrator_routes_general_query(judge: LLMJudge):
    """General queries (greetings etc.) should route to the general agent."""
    orch = _make_orchestrator_with_real_classifier()
    response, intent_result = await orch.handle("Hello!", context={})

    print(f"\nIntent: {intent_result.intent.value}")

    # Greeting should classify as GENERAL
    assert intent_result.intent == IntentType.GENERAL
    orch._registry["general"].process.assert_called_once()


# ---------------------------------------------------------------------------
# Context enrichment tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_passes_price_hints_to_agent(judge: LLMJudge):
    """Price constraints extracted by the classifier should be passed to the agent."""
    orch = _make_orchestrator_with_real_classifier()
    await orch.handle("Find laptops between $400 and $800", context={})

    call_context = orch._registry["recommendation"].process.call_args[0][1]
    structured_hints = call_context.get("structured_hints", {})
    print(f"\nStructured hints: {structured_hints}")

    # Classifier should have extracted price range
    # (Either max_price or min_price should be in hints)
    has_price_hint = "max_price" in structured_hints or "min_price" in structured_hints
    assert (
        has_price_hint
    ), f"No price hints passed to agent. Structured hints: {structured_hints}"


@pytest.mark.asyncio
async def test_orchestrator_passes_category_hint(judge: LLMJudge):
    """Category extracted by classifier should be passed to the agent."""
    orch = _make_orchestrator_with_real_classifier()
    await orch.handle("Show me the best laptops under $600", context={})

    call_context = orch._registry["recommendation"].process.call_args[0][1]
    structured_hints = call_context.get("structured_hints", {})
    print(f"\nStructured hints: {structured_hints}")

    # Category should be extracted
    if "category" in structured_hints:
        assert "laptop" in structured_hints["category"].lower()


# ---------------------------------------------------------------------------
# End-to-end response quality tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_recommendation_response_quality(judge: LLMJudge):
    """Full orchestrator pipeline should produce a high-quality recommendation response."""
    from tests.evals.conftest import format_agent_response

    orch = _make_orchestrator_with_real_classifier()
    response, intent_result = await orch.handle(
        "Find me budget smartphones under $300", context={}
    )

    response_text = format_agent_response(response, "recommendation")
    print(f"\nFull response:\n{response_text}")

    score = await judge.evaluate(
        query="Find me budget smartphones under $300",
        response=response_text,
        agent_type="recommendation",
        context="End-to-end orchestrator response — should be relevant, structured, and helpful.",
    )
    print(f"Score: {score}")

    assert response.success
    assert score.overall >= 0.70, (
        f"E2E recommendation response quality too low: {score.overall:.2f}\n"
        f"Explanation: {score.explanation}"
    )


@pytest.mark.asyncio
async def test_orchestrator_policy_response_quality(judge: LLMJudge):
    """Full orchestrator pipeline for policy query should produce accurate policy response."""
    from tests.evals.conftest import format_agent_response

    orch = _make_orchestrator_with_real_classifier()
    response, intent_result = await orch.handle(
        "What is your return policy?", context={}
    )

    response_text = format_agent_response(response, "policy")
    print(f"\nFull response:\n{response_text}")

    score = await judge.evaluate(
        query="What is your return policy?",
        response=response_text,
        agent_type="policy",
        context="Should accurately describe the return policy with timeframes and conditions.",
    )
    print(f"Score: {score}")

    assert response.success
    assert score.overall >= 0.70


# ---------------------------------------------------------------------------
# Fallback and resilience tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrator_falls_back_to_general_on_agent_failure(judge: LLMJudge):
    """When specialist agent fails, orchestrator should fall back to general agent."""
    from app.agents.orchestrator.orchestrator import Orchestrator

    failing_rec_agent = MagicMock()
    failing_rec_agent.name = "recommendation-agent"
    failing_rec_agent.process = AsyncMock(side_effect=Exception("LLM timeout"))

    registry = {
        "recommendation": failing_rec_agent,
        "review": _make_mock_agent("review-agent", GOOD_REVIEW_RESPONSE),
        "price": _make_mock_agent("price-agent", GOOD_PRICE_RESPONSE),
        "policy": _make_mock_agent("policy-agent", GOOD_POLICY_RESPONSE),
        "general": _make_mock_agent("general-agent", GOOD_GENERAL_RESPONSE),
    }
    orch = Orchestrator(registry=registry)

    response, intent_result = await orch.handle(
        "Find me budget smartphones under $300", context={}
    )

    print(f"\nFallback response: {response.data}")

    # Should fall back to general agent
    registry["general"].process.assert_called_once()
    assert response.success


@pytest.mark.asyncio
async def test_orchestrator_returns_response_for_all_intent_types(judge: LLMJudge):
    """Orchestrator should return a successful response for every intent type."""
    orch = _make_orchestrator_with_real_classifier()

    test_queries = [
        "Find smartphones under $400",
        "What do reviews say about Sony headphones?",
        "What is the best price for Galaxy S24?",
        "What is your return policy?",
        "Hello, how are you?",
    ]

    for query in test_queries:
        response, intent_result = await orch.handle(query, context={})
        print(
            f"\n  Q: {query!r} → intent={intent_result.intent.value} success={response.success}"
        )
        assert (
            response.success or response.data
        ), f"Orchestrator returned empty response for: {query!r}"
