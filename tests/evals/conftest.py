"""Shared fixtures and configuration for SmartShop AI eval tests.

Running evals
=============
Evals require a valid OPENAI_API_KEY and an explicit opt-in flag to avoid
accidentally incurring LLM costs during regular CI runs.

    # Run all eval tests
    RUN_EVALS=1 pytest tests/evals/ -v -m eval

    # Run a single file
    RUN_EVALS=1 pytest tests/evals/test_eval_recommendation.py -v

    # Run with verbose judge output
    RUN_EVALS=1 pytest tests/evals/ -v -m eval -s

Architecture
============
- judge.py    — LLM-as-judge (EvalScore, LLMJudge, EvalCase)
- conftest.py — skip logic, shared fixtures, mock data helpers
- test_eval_judge.py           — judge calibration (good vs bad response ranking)
- test_eval_intent_classifier.py — intent routing accuracy
- test_eval_recommendation.py  — RecommendationAgent quality
- test_eval_review.py          — ReviewSummarizationAgent quality
- test_eval_price.py           — PriceComparisonAgent quality
- test_eval_policy.py          — PolicyAgent quality
- test_eval_general.py         — GeneralResponseAgent quality
- test_eval_orchestrator.py    — End-to-end orchestrator routing
"""

import os
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from tests.evals.judge import LLMJudge


# ---------------------------------------------------------------------------
# Skip logic — evals only run when explicitly requested
# ---------------------------------------------------------------------------


def _has_api_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _evals_enabled() -> bool:
    return os.environ.get("RUN_EVALS", "").lower() in ("1", "true", "yes")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "eval: LLM-as-judge evaluation tests — require OPENAI_API_KEY and RUN_EVALS=1",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip every test in tests/evals/ unless opt-in flags are present."""
    reason = None
    if not _has_api_key():
        reason = "OPENAI_API_KEY not set — skipping eval tests"
    elif not _evals_enabled():
        reason = "Set RUN_EVALS=1 to run eval tests (they make real LLM API calls)"

    if reason:
        skip = pytest.mark.skip(reason=reason)
        for item in items:
            if "evals" in str(item.fspath):
                item.add_marker(skip)


# ---------------------------------------------------------------------------
# Shared judge fixture (session-scoped to avoid recreating the agent)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def judge() -> LLMJudge:
    """Session-scoped LLM judge. Reused across all eval tests."""
    return LLMJudge()


# ---------------------------------------------------------------------------
# Mock DB factory
# ---------------------------------------------------------------------------


def make_mock_db(
    products: list[dict] | None = None,
    reviews: list[dict] | None = None,
    policies: list[dict] | None = None,
) -> MagicMock:
    """Create a mock SQLAlchemy session with optional seeded data.

    Mirrors the ``make_mock_db`` helper in the agent unit-test files so eval
    tests can reuse the same DB-mocking pattern.
    """
    db = MagicMock()

    def _make_mocks(items: list[dict]) -> list[MagicMock]:
        mocks = []
        for item in items:
            m = MagicMock()
            for k, v in item.items():
                setattr(m, k, v)
            m.to_dict.return_value = item
            mocks.append(m)
        return mocks

    all_items = (
        _make_mocks(products or [])
        or _make_mocks(reviews or [])
        or _make_mocks(policies or [])
    )

    q = db.query.return_value
    q.filter.return_value = q
    q.filter_by.return_value = q
    q.order_by.return_value = q
    q.limit.return_value = q
    q.offset.return_value = q
    q.all.return_value = all_items
    q.first.return_value = all_items[0] if all_items else None
    q.count.return_value = len(all_items)
    return db


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

SAMPLE_PRODUCTS = [
    {
        "id": "PROD001",
        "name": "Budget Phone X1",
        "price": Decimal("249.99"),
        "brand": "TechCo",
        "category": "smartphones",
        "stock": 50,
        "rating": 4.2,
        "description": "Affordable smartphone with great battery life and 5G support",
        "image_url": None,
        "created_at": None,
        "updated_at": None,
    },
    {
        "id": "PROD002",
        "name": "Premium Phone Y2",
        "price": Decimal("799.99"),
        "brand": "PremiumBrand",
        "category": "smartphones",
        "stock": 20,
        "rating": 4.8,
        "description": "High-end smartphone with 200MP camera and 12GB RAM",
        "image_url": None,
        "created_at": None,
        "updated_at": None,
    },
    {
        "id": "PROD003",
        "name": "Mid-Range Phone Z3",
        "price": Decimal("399.99"),
        "brand": "ValueCo",
        "category": "smartphones",
        "stock": 35,
        "rating": 4.0,
        "description": "Balanced performance and price, 64MP camera, 8GB RAM",
        "image_url": None,
        "created_at": None,
        "updated_at": None,
    },
    {
        "id": "PROD004",
        "name": "UltraBook Pro 15",
        "price": Decimal("1299.99"),
        "brand": "LaptopCo",
        "category": "laptops",
        "stock": 15,
        "rating": 4.6,
        "description": "Professional laptop: Intel i7, 16GB RAM, 512GB SSD, 15-inch display",
        "image_url": None,
        "created_at": None,
        "updated_at": None,
    },
    {
        "id": "PROD005",
        "name": "Budget Laptop B1",
        "price": Decimal("449.99"),
        "brand": "EcoTech",
        "category": "laptops",
        "stock": 30,
        "rating": 3.8,
        "description": "Entry-level laptop for basic computing: Intel i3, 8GB RAM, 256GB SSD",
        "image_url": None,
        "created_at": None,
        "updated_at": None,
    },
    {
        "id": "PROD006",
        "name": "Sony WH-1000XM5",
        "price": Decimal("349.99"),
        "brand": "Sony",
        "category": "headphones",
        "stock": 25,
        "rating": 4.7,
        "description": "Industry-leading noise-cancelling headphones, 30h battery, LDAC",
        "image_url": None,
        "created_at": None,
        "updated_at": None,
    },
    {
        "id": "PROD007",
        "name": "Budget Headphones H1",
        "price": Decimal("49.99"),
        "brand": "AudioCo",
        "category": "headphones",
        "stock": 100,
        "rating": 3.5,
        "description": "Basic wired headphones, comfortable fit, no noise cancellation",
        "image_url": None,
        "created_at": None,
        "updated_at": None,
    },
]

SAMPLE_REVIEWS = [
    {
        "id": 1,
        "product_id": "PROD006",
        "rating": 5.0,
        "text": (
            "Best headphones I've ever owned. The noise cancellation is phenomenal — "
            "I can work in a busy cafe without any distraction. Battery lasts 30 hours easily."
        ),
        "sentiment": "positive",
        "review_date": "2025-01-15",
    },
    {
        "id": 2,
        "product_id": "PROD006",
        "rating": 4.0,
        "text": (
            "Sound quality is excellent and they're comfortable for long sessions. "
            "The ear cushions could be softer. Touch controls are great but occasionally finicky."
        ),
        "sentiment": "positive",
        "review_date": "2025-02-01",
    },
    {
        "id": 3,
        "product_id": "PROD006",
        "rating": 3.0,
        "text": (
            "The audio quality is great but the carrying case feels cheap for the price. "
            "Also the touch controls are too sensitive — kept pausing music accidentally."
        ),
        "sentiment": "neutral",
        "review_date": "2025-02-20",
    },
    {
        "id": 4,
        "product_id": "PROD001",
        "rating": 4.0,
        "text": (
            "Good battery life, charges fast with USB-C. Camera is average but fine for the price. "
            "5G connectivity works perfectly."
        ),
        "sentiment": "positive",
        "review_date": "2025-01-10",
    },
    {
        "id": 5,
        "product_id": "PROD001",
        "rating": 2.0,
        "text": (
            "Screen cracked after 3 months of careful use. Customer service was unhelpful "
            "and refused to honour the warranty. Very disappointed."
        ),
        "sentiment": "negative",
        "review_date": "2025-03-01",
    },
]

SAMPLE_POLICIES = [
    {
        "id": 1,
        "policy_type": "return",
        "description": "30-Day Return Policy",
        "conditions": (
            "Items must be unopened and in original packaging|"
            "Receipt or proof of purchase required|"
            "Electronics subject to a 15% restocking fee if opened|"
            "Sale items are final and non-returnable"
        ),
        "timeframe": 30,
    },
    {
        "id": 2,
        "policy_type": "shipping",
        "description": "Standard and Express Shipping",
        "conditions": (
            "Free standard shipping on orders over $50|"
            "Standard delivery: 5–7 business days|"
            "Express delivery: 1–2 business days for $9.99|"
            "Same-day delivery available in select cities"
        ),
        "timeframe": 7,
    },
    {
        "id": 3,
        "policy_type": "warranty",
        "description": "1-Year Manufacturer Warranty",
        "conditions": (
            "Covers manufacturing defects and component failures|"
            "Does not cover accidental damage or water damage|"
            "Proof of purchase required for all warranty claims|"
            "Warranty void if device has been modified"
        ),
        "timeframe": 365,
    },
]


# ---------------------------------------------------------------------------
# Response formatting helpers (used by individual eval test modules)
# ---------------------------------------------------------------------------


def format_agent_response(result, agent_type: str = "") -> str:
    """Convert an AgentResponse into readable text for the LLM judge.

    Handles the varying data shapes returned by different agents.
    """
    if not result.success:
        return f"[AGENT ERROR] {result.error or 'Unknown error'}"

    data = result.data
    parts: list[str] = []

    # --- Recommendation / comparison ---
    if "recommendations" in data:
        recs = data["recommendations"]
        if isinstance(recs, list):
            parts.append("Recommended Products:")
            for i, rec in enumerate(recs[:6], 1):
                if isinstance(rec, dict):
                    name = rec.get("name", "Unknown")
                    price = rec.get("price", "N/A")
                    rating = rec.get("rating", "N/A")
                    reason = rec.get("reason", "")
                    parts.append(f"  {i}. {name} — ${price} | Rating: {rating}★")
                    if reason:
                        parts.append(f"     Reason: {reason}")
                else:
                    parts.append(f"  {i}. {rec}")
        if "reasoning_summary" in data:
            parts.append(f"\nOverall Reasoning: {data['reasoning_summary']}")

    # --- Review summary ---
    elif "summary" in data or "sentiment_summary" in data:
        if "summary" in data:
            parts.append(f"Review Summary:\n{data['summary']}")
        if "sentiment_summary" in data:
            parts.append(f"Sentiment: {data['sentiment_summary']}")
        if "average_rating" in data:
            parts.append(f"Average Rating: {data['average_rating']}★")
        if "highlights" in data:
            parts.append(f"Highlights: {data['highlights']}")
        if "concerns" in data:
            parts.append(f"Concerns: {data['concerns']}")

    # --- Price comparison ---
    elif "prices" in data or "price_analysis" in data or "best_price" in data:
        if "prices" in data:
            parts.append(f"Price Comparison: {data['prices']}")
        if "best_price" in data:
            parts.append(f"Best Price Found: ${data['best_price']}")
        if "price_analysis" in data:
            parts.append(f"Analysis: {data['price_analysis']}")
        if "recommendation" in data:
            parts.append(f"Recommendation: {data['recommendation']}")

    # --- Policy answer ---
    elif "answer" in data and agent_type == "policy":
        parts.append(f"Policy Answer:\n{data['answer']}")
        if "policy_type" in data:
            parts.append(f"Policy Type: {data['policy_type']}")
        if "sources" in data:
            parts.append(f"Sources: {data['sources']}")

    # --- General / fallback ---
    elif "answer" in data:
        parts.append(data["answer"])

    # --- Catch-all ---
    if not parts:
        parts.append(str(data))

    return "\n".join(parts)
