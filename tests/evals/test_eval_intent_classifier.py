"""Eval tests for IntentClassifier — routing accuracy and entity extraction.

These tests call the real IntentClassifier (uses GPT-4o-mini) and assert that:
  1. The classified intent matches the expected intent for each query.
  2. Confidence scores are appropriately calibrated (>0.70 for clear queries).
  3. Entity extraction works correctly (price ranges, product names, categories).
  4. The fallback to GENERAL on ambiguous queries works as expected.

Running
-------
    RUN_EVALS=1 pytest tests/evals/test_eval_intent_classifier.py -v -s
"""

import pytest

from app.agents.orchestrator.intent_classifier import IntentClassifier
from app.schemas.chat import IntentType

pytestmark = pytest.mark.eval


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def classifier() -> IntentClassifier:
    """Module-scoped IntentClassifier — creates one LLM agent for all tests."""
    return IntentClassifier()


# ---------------------------------------------------------------------------
# Intent routing accuracy tests
# ---------------------------------------------------------------------------


INTENT_CASES = [
    # (query, expected_intent, min_confidence, description)
    (
        "Find me budget smartphones under $300",
        IntentType.RECOMMENDATION,
        0.75,
        "Clear recommendation with price constraint",
    ),
    (
        "Can you recommend a good laptop for university students?",
        IntentType.RECOMMENDATION,
        0.70,
        "Recommendation for a specific use case",
    ),
    (
        "Compare iPhone 15 vs Samsung Galaxy S24",
        IntentType.COMPARISON,
        0.75,
        "Direct product comparison",
    ),
    (
        "Which is better: Sony WH-1000XM5 or Bose QuietComfort 45?",
        IntentType.COMPARISON,
        0.70,
        "Implicit comparison request",
    ),
    (
        "What do customers say about the Sony WH-1000XM5 headphones?",
        IntentType.REVIEW,
        0.75,
        "Clear review intent",
    ),
    (
        "Are there any complaints about the UltraBook Pro 15?",
        IntentType.REVIEW,
        0.70,
        "Review intent focusing on negatives",
    ),
    (
        "What is your return policy for electronics?",
        IntentType.POLICY,
        0.80,
        "Clear policy question",
    ),
    (
        "How long does standard shipping take?",
        IntentType.POLICY,
        0.75,
        "Shipping policy question",
    ),
    (
        "What is the best price for Samsung Galaxy S24 right now?",
        IntentType.PRICE,
        0.75,
        "Clear price intent",
    ),
    (
        "Where can I get the cheapest Sony headphones?",
        IntentType.PRICE,
        0.70,
        "Price-focused query",
    ),
    (
        "Hello! How are you?",
        IntentType.GENERAL,
        0.70,
        "Greeting — should be GENERAL",
    ),
    (
        "What time does your store close?",
        IntentType.GENERAL,
        0.60,
        "General store question",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query,expected_intent,min_confidence,description",
    INTENT_CASES,
    ids=[desc for _, _, _, desc in INTENT_CASES],
)
async def test_intent_classification_accuracy(
    classifier: IntentClassifier,
    query: str,
    expected_intent: IntentType,
    min_confidence: float,
    description: str,
):
    """Classifier should correctly identify the intent of common shopping queries."""
    result = await classifier.classify(query)
    print(
        f"\n[{description}]\n"
        f"  Query: {query!r}\n"
        f"  Got:      {result.intent.value} (conf={result.confidence:.2f})\n"
        f"  Expected: {expected_intent.value} (min_conf={min_confidence})\n"
        f"  Reasoning: {result.reasoning}"
    )
    assert result.intent == expected_intent, (
        f"Intent mismatch for [{description}]:\n"
        f"  Query: {query!r}\n"
        f"  Expected: {expected_intent.value}\n"
        f"  Got:      {result.intent.value} (confidence={result.confidence:.2f})\n"
        f"  Reasoning: {result.reasoning}"
    )
    assert result.confidence >= min_confidence, (
        f"Confidence too low for [{description}]: "
        f"{result.confidence:.2f} (min={min_confidence})"
    )


# ---------------------------------------------------------------------------
# Entity extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extracts_max_price_from_query(classifier: IntentClassifier):
    """Classifier should extract the maximum price from budget constraints."""
    result = await classifier.classify("Find smartphones under $500")
    print(f"\n  max_price={result.max_price}, min_price={result.min_price}")
    assert result.intent == IntentType.RECOMMENDATION
    assert result.max_price is not None, "Should extract max_price"
    assert 450 <= result.max_price <= 550, f"max_price={result.max_price} not near $500"


@pytest.mark.asyncio
async def test_extracts_price_range(classifier: IntentClassifier):
    """Classifier should extract both min and max price from a range query."""
    result = await classifier.classify("Show me laptops between $400 and $800")
    print(f"\n  min_price={result.min_price}, max_price={result.max_price}")
    assert result.intent == IntentType.RECOMMENDATION
    assert result.min_price is not None, "Should extract min_price"
    assert result.max_price is not None, "Should extract max_price"
    assert result.min_price < result.max_price, "min_price should be less than max_price"
    assert 350 <= result.min_price <= 450, f"min_price={result.min_price} not near $400"
    assert 750 <= result.max_price <= 850, f"max_price={result.max_price} not near $800"


@pytest.mark.asyncio
async def test_extracts_category(classifier: IntentClassifier):
    """Classifier should extract the product category when mentioned."""
    result = await classifier.classify("What are the best laptops you have?")
    print(f"\n  category={result.category!r}")
    assert result.intent in (IntentType.RECOMMENDATION, IntentType.GENERAL)
    if result.category:
        assert "laptop" in result.category.lower(), (
            f"Category should mention laptop: {result.category!r}"
        )


@pytest.mark.asyncio
async def test_extracts_product_name(classifier: IntentClassifier):
    """Classifier should extract a specific product name when mentioned."""
    result = await classifier.classify("What do reviews say about Sony WH-1000XM5?")
    print(f"\n  product_name={result.product_name!r}")
    assert result.intent == IntentType.REVIEW
    assert result.product_name is not None, "Should extract product name"
    assert "sony" in result.product_name.lower() or "wh-1000" in result.product_name.lower(), (
        f"Product name should mention Sony/WH-1000: {result.product_name!r}"
    )


@pytest.mark.asyncio
async def test_comparison_extracts_no_price_for_brand_comparison(classifier: IntentClassifier):
    """Brand-level comparison queries should not extract spurious prices."""
    result = await classifier.classify("Compare Apple and Samsung smartphones")
    print(f"\n  intent={result.intent.value}, max_price={result.max_price}")
    assert result.intent in (IntentType.COMPARISON, IntentType.RECOMMENDATION)
    # No price should be extracted from a brand comparison
    assert result.max_price is None, f"Should not extract price: {result.max_price}"


# ---------------------------------------------------------------------------
# Confidence calibration tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_high_confidence_for_unambiguous_queries(classifier: IntentClassifier):
    """Very clear queries should yield high confidence (≥ 0.80)."""
    unambiguous = [
        ("What is your refund policy?", IntentType.POLICY),
        ("Find me headphones under $100", IntentType.RECOMMENDATION),
        ("Compare iPhone 15 vs Pixel 8", IntentType.COMPARISON),
    ]
    for query, expected_intent in unambiguous:
        result = await classifier.classify(query)
        print(f"\n  {query!r} → {result.intent.value} conf={result.confidence:.2f}")
        assert result.intent == expected_intent
        assert result.confidence >= 0.75, (
            f"Expected high confidence for clear query {query!r}: {result.confidence:.2f}"
        )


@pytest.mark.asyncio
async def test_fallback_to_general_on_very_ambiguous_query(classifier: IntentClassifier):
    """Very ambiguous or completely off-topic queries should classify as GENERAL."""
    ambiguous_queries = [
        "Can you help me?",
        "I have a question.",
        "asdfghjkl",  # gibberish
    ]
    for query in ambiguous_queries:
        result = await classifier.classify(query)
        print(f"\n  {query!r} → {result.intent.value} (conf={result.confidence:.2f})")
        # These should either be GENERAL or have low confidence
        is_general = result.intent == IntentType.GENERAL
        is_low_confidence = result.confidence < 0.70
        assert is_general or is_low_confidence, (
            f"Ambiguous query {query!r} got unexpected high-confidence non-GENERAL: "
            f"{result.intent.value} conf={result.confidence:.2f}"
        )


# ---------------------------------------------------------------------------
# Reasoning quality tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classifier_provides_reasoning(classifier: IntentClassifier):
    """Every classification result should include a non-empty reasoning string."""
    queries = [
        "Find budget smartphones under $300",
        "What is your shipping policy?",
        "Compare Sony vs Bose headphones",
    ]
    for query in queries:
        result = await classifier.classify(query)
        assert result.reasoning, f"Missing reasoning for query: {query!r}"
        assert len(result.reasoning) > 10, (
            f"Reasoning too short for {query!r}: {result.reasoning!r}"
        )
