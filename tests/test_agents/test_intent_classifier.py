import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.orchestrator.intent_classifier import IntentClassifier
from app.schemas.chat import IntentType

@pytest.mark.asyncio
async def test_classify_recommendation():
    clf = IntentClassifier()
    with patch.object(clf._agent, "run", new_callable=AsyncMock) as m:
        r = MagicMock(); r.output.intent = IntentType.RECOMMENDATION
        r.output.confidence = 0.95; r.output.max_price = 500.0
        r.output.product_name = r.output.category = r.output.min_price = None
        r.output.reasoning = "rec"
        m.return_value = r
        result = await clf.classify("Find me a smartphone under $500")
    assert result.intent == IntentType.RECOMMENDATION and result.max_price == 500.0

@pytest.mark.asyncio
async def test_classify_price():
    clf = IntentClassifier()
    with patch.object(clf._agent, "run", new_callable=AsyncMock) as m:
        r = MagicMock(); r.output.intent = IntentType.PRICE
        r.output.confidence = 0.92; r.output.product_name = "Galaxy S24"
        r.output.category = r.output.max_price = r.output.min_price = None
        r.output.reasoning = "price"
        m.return_value = r
        result = await clf.classify("Best price for Galaxy S24 across stores?")
    assert result.intent == IntentType.PRICE

@pytest.mark.asyncio
async def test_classify_policy():
    clf = IntentClassifier()
    with patch.object(clf._agent, "run", new_callable=AsyncMock) as m:
        r = MagicMock(); r.output.intent = IntentType.POLICY
        r.output.confidence = 0.88
        r.output.product_name = r.output.category = r.output.max_price = r.output.min_price = None
        r.output.reasoning = "policy"
        m.return_value = r
        result = await clf.classify("What is the return policy for electronics?")
    assert result.intent == IntentType.POLICY

@pytest.mark.asyncio
async def test_classify_falls_back_on_failure():
    clf = IntentClassifier()
    with patch.object(clf._agent, "run", side_effect=Exception("timeout")):
        result = await clf.classify("some query")
    assert result.intent == IntentType.GENERAL and result.confidence == 0.0

@pytest.mark.asyncio
async def test_classify_review():
    clf = IntentClassifier()
    with patch.object(clf._agent, "run", new_callable=AsyncMock) as m:
        r = MagicMock(); r.output.intent = IntentType.REVIEW
        r.output.confidence = 0.90; r.output.product_name = "Sony WH-1000XM5"
        r.output.category = r.output.max_price = r.output.min_price = None
        r.output.reasoning = "review"
        m.return_value = r
        result = await clf.classify("What do customers say about Sony WH-1000XM5?")
    assert result.intent == IntentType.REVIEW and result.product_name == "Sony WH-1000XM5"

@pytest.mark.asyncio
async def test_classify_extracts_price_range():
    clf = IntentClassifier()
    with patch.object(clf._agent, "run", new_callable=AsyncMock) as m:
        r = MagicMock(); r.output.intent = IntentType.RECOMMENDATION
        r.output.confidence = 0.93; r.output.category = "laptops"
        r.output.max_price = 800.0; r.output.min_price = 500.0
        r.output.product_name = None; r.output.reasoning = "rec"
        m.return_value = r
        result = await clf.classify("Laptops between $500 and $800")
    assert result.max_price == 800.0 and result.min_price == 500.0
