"""Judge calibration tests — verify the LLM judge scores correctly.

These tests do NOT call any SmartShop agent. They feed pre-defined synthetic
responses (good and bad) to the judge and verify:

  1. Good responses score above the minimum thresholds.
  2. Bad responses score below maximum thresholds.
  3. For every pair, good_score.overall > bad_score.overall.

Running
-------
    RUN_EVALS=1 pytest tests/evals/test_eval_judge.py -v -s
"""

import pytest

from tests.evals.judge import EvalCase, LLMJudge

pytestmark = pytest.mark.eval


# ---------------------------------------------------------------------------
# Good / bad response pairs (agent-type → (query, good_response, bad_response))
# ---------------------------------------------------------------------------

CALIBRATION_PAIRS = [
    # ---- Recommendation -------------------------------------------------------
    (
        "recommendation",
        "Find me budget smartphones under $300",
        # GOOD — relevant, structured, explains reasoning
        (
            "Recommended Products:\n"
            "  1. Budget Phone X1 (TechCo) — $249.99 | Rating: 4.2★\n"
            "     Reason: Best-value 5G smartphone under $300 with 4200mAh battery\n"
            "  2. ValuePhone V1 (ValueCo) — $279.99 | Rating: 3.9★\n"
            "     Reason: Reliable option with good camera for the price\n\n"
            "Overall Reasoning: Both phones are under your $300 budget, offer 5G connectivity, "
            "and have above-average ratings. Budget Phone X1 is the stronger choice for battery life."
        ),
        # BAD — off-topic, unhelpful
        (
            "I'm not sure what you're looking for. "
            "The weather today is sunny and 22°C. Have a great day!"
        ),
    ),
    # ---- Review ---------------------------------------------------------------
    (
        "review",
        "What do customers say about Sony WH-1000XM5 headphones?",
        # GOOD — summarises actual feedback with balanced view
        (
            "Review Summary for Sony WH-1000XM5:\n"
            "Average Rating: 4.0★ from 150+ reviews\n"
            "Positives: Exceptional noise cancellation; 30-hour battery life; premium sound quality\n"
            "Concerns: Carrying case feels cheap; touch controls overly sensitive; ear pads could be softer\n"
            "Overall Sentiment: Strongly positive — most users rate it among the best ANC headphones available."
        ),
        # BAD — fabricated irrelevant content
        (
            "Sony is a Japanese company founded in 1946. "
            "They make televisions, cameras, and gaming consoles. "
            "The PlayStation 5 is their latest console."
        ),
    ),
    # ---- Price ----------------------------------------------------------------
    (
        "price",
        "What is the best price for Samsung Galaxy S24?",
        # GOOD — price-focused, comparative, actionable
        (
            "Price Comparison — Samsung Galaxy S24:\n"
            "  SmartShop:    $799.99 (in stock)\n"
            "  Market range: $749 – $849 across major retailers\n"
            "Best Price Found: $749 at CompetitorStore (limited time)\n"
            "Price Assessment: SmartShop's price is competitive, 5% above the lowest market price.\n"
            "Recommendation: Check if SmartShop price-matches — you may save $50."
        ),
        # BAD — does not address price at all
        (
            "The Samsung Galaxy S24 is a great phone. It has a 50MP camera and 8GB of RAM. "
            "It comes in Phantom Black, Marble Gray, and Cobalt Violet."
        ),
    ),
    # ---- Policy ---------------------------------------------------------------
    (
        "policy",
        "Can I return an opened phone after 20 days?",
        # GOOD — accurate to policy, specific, actionable
        (
            "Return Policy Answer:\n"
            "Yes, you can return an opened phone within our 30-day return window. However, "
            "please note that opened electronics are subject to a 15% restocking fee. "
            "You will need your original receipt and the product should be in its original packaging "
            "where possible. Sale items are final sale and cannot be returned.\n"
            "Policy Type: Return Policy | Timeframe: 30 days"
        ),
        # BAD — wrong policy detail, unhelpful
        (
            "Returns are not allowed for any electronics. All sales are final. "
            "Please contact the manufacturer directly for any product issues."
        ),
    ),
    # ---- General --------------------------------------------------------------
    (
        "general",
        "Hello! What can you help me with?",
        # GOOD — on-brand, clear, redirects to shopping
        (
            "Hello! I'm SmartShop AI, your personal shopping assistant. I can help you with:\n"
            "• Product recommendations tailored to your needs and budget\n"
            "• Customer review summaries so you can shop with confidence\n"
            "• Price comparisons across our product catalog\n"
            "• Store policies on returns, shipping, and warranties\n\n"
            "What are you looking for today?"
        ),
        # BAD — confusing, claims unrelated capabilities
        (
            "I can book flights, manage your calendar, write code, "
            "and answer questions about history or science. "
            "Just tell me what you need and I'll handle everything."
        ),
    ),
]


# ---------------------------------------------------------------------------
# Judge calibration: good responses should score high
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_type,query,good_response,_bad",
    [(a, q, g, b) for a, q, g, b in CALIBRATION_PAIRS],
    ids=[a for a, _, _, _ in CALIBRATION_PAIRS],
)
async def test_judge_scores_good_response_above_threshold(
    judge: LLMJudge, agent_type, query, good_response, _bad
):
    """Good, relevant, well-reasoned responses should score ≥ 0.70 overall."""
    score = await judge.evaluate(
        query=query,
        response=good_response,
        agent_type=agent_type,
        context="This is a well-crafted, relevant response.",
    )
    print(f"\n[{agent_type}] GOOD → {score}")
    assert score.relevance >= 0.65, f"Relevance too low: {score.relevance:.2f}"
    assert score.overall >= 0.70, (
        f"Overall quality too low for a good response: {score.overall:.2f}\n"
        f"Explanation: {score.explanation}"
    )


# ---------------------------------------------------------------------------
# Judge calibration: bad responses should score low
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_type,query,_good,bad_response",
    [(a, q, g, b) for a, q, g, b in CALIBRATION_PAIRS],
    ids=[a for a, _, _, _ in CALIBRATION_PAIRS],
)
async def test_judge_scores_bad_response_below_threshold(
    judge: LLMJudge, agent_type, query, _good, bad_response
):
    """Off-topic, incorrect, or unhelpful responses should score ≤ 0.45 overall."""
    score = await judge.evaluate(
        query=query,
        response=bad_response,
        agent_type=agent_type,
        context="This response may be off-topic or incorrect.",
    )
    print(f"\n[{agent_type}] BAD → {score}")
    assert score.overall <= 0.45, (
        f"Bad response scored too high: {score.overall:.2f} — judge may be miscalibrated.\n"
        f"Explanation: {score.explanation}"
    )


# ---------------------------------------------------------------------------
# Judge calibration: good must rank higher than bad
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "agent_type,query,good_response,bad_response",
    CALIBRATION_PAIRS,
    ids=[a for a, _, _, _ in CALIBRATION_PAIRS],
)
async def test_judge_ranks_good_above_bad(
    judge: LLMJudge, agent_type, query, good_response, bad_response
):
    """For every pair, good response overall score must exceed bad response overall score."""
    good_score, bad_score = await judge.compare(query, good_response, bad_response, agent_type)
    print(f"\n[{agent_type}] GOOD={good_score.overall:.2f} BAD={bad_score.overall:.2f}")
    assert good_score.overall > bad_score.overall, (
        f"Judge failed to rank good > bad for [{agent_type}]:\n"
        f"  good={good_score.overall:.2f} ({good_score.explanation})\n"
        f"  bad={bad_score.overall:.2f} ({bad_score.explanation})"
    )


# ---------------------------------------------------------------------------
# Edge cases: error responses, empty responses
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_judge_handles_agent_error_response(judge: LLMJudge):
    """An agent error message should score very low on all dimensions."""
    score = await judge.evaluate(
        query="Find me a laptop under $500",
        response="[AGENT ERROR] Service temporarily unavailable. Please try again later.",
        agent_type="recommendation",
    )
    print(f"\n[error-response] → {score}")
    assert score.overall < 0.50, f"Error response scored too high: {score.overall:.2f}"
    assert score.helpfulness < 0.50


@pytest.mark.asyncio
async def test_judge_returns_structured_score(judge: LLMJudge):
    """Judge should always return a complete EvalScore with all fields."""
    score = await judge.evaluate(
        query="What headphones do you recommend?",
        response="I recommend the Sony WH-1000XM5 for its outstanding noise cancellation.",
        agent_type="recommendation",
    )
    # Verify all fields are present and in range
    assert 0.0 <= score.relevance <= 1.0
    assert 0.0 <= score.correctness <= 1.0
    assert 0.0 <= score.reasoning_quality <= 1.0
    assert 0.0 <= score.helpfulness <= 1.0
    assert 0.0 <= score.overall <= 1.0
    assert isinstance(score.explanation, str)
    assert len(score.explanation) > 10


@pytest.mark.asyncio
async def test_judge_average_property(judge: LLMJudge):
    """EvalScore.average should equal mean of four primary dimensions."""
    score = await judge.evaluate(
        query="Tell me about your return policy",
        response="We offer a 30-day return policy on all items. Opened items may have a restocking fee.",
        agent_type="policy",
    )
    expected_avg = (
        score.relevance + score.correctness + score.reasoning_quality + score.helpfulness
    ) / 4
    assert abs(score.average - expected_avg) < 1e-9, (
        f"average property mismatch: {score.average:.4f} vs {expected_avg:.4f}"
    )
