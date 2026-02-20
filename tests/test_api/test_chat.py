import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.agents.base import AgentResponse
from app.schemas.chat import IntentType
from app.agents.orchestrator.orchestrator import reset_orchestrator

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset(): reset_orchestrator(); yield; reset_orchestrator()

def _ir(intent=IntentType.RECOMMENDATION, **kw):
    from app.agents.orchestrator.intent_classifier import _IntentResult
    return _IntentResult(intent=intent, confidence=0.9, reasoning="test", **kw)

def _mock_orch(intent=IntentType.RECOMMENDATION, agent="rec-agent"):
    o = MagicMock()
    o.handle = AsyncMock(return_value=(
        AgentResponse(success=True, data={"agent": agent, "answer": "ok", "recommendations": []}),
        _ir(intent)))
    return o

def test_chat_recommendation_success():
    with patch("app.api.v1.chat.get_orchestrator", return_value=_mock_orch()):
        r = client.post("/api/v1/chat", json={"message": "Find laptops under $800"})
    assert r.status_code == 200 and r.json()["intent"] == "recommendation"

def test_chat_price_intent():
    with patch("app.api.v1.chat.get_orchestrator",
               return_value=_mock_orch(IntentType.PRICE, "price-agent")):
        r = client.post("/api/v1/chat", json={"message": "Compare Galaxy S24 prices"})
    assert r.status_code == 200 and r.json()["intent"] == "price"

def test_chat_empty_message(): assert client.post("/api/v1/chat", json={"message": ""}).status_code == 422
def test_chat_missing_message(): assert client.post("/api/v1/chat", json={}).status_code == 422

def test_chat_with_session_id():
    with patch("app.api.v1.chat.get_orchestrator", return_value=_mock_orch()):
        r = client.post("/api/v1/chat", json={"message": "Show phones", "session_id": "sess-123"})
    assert r.status_code == 200

def test_chat_entities_returned():
    from app.agents.orchestrator.intent_classifier import _IntentResult
    ir = _IntentResult(intent=IntentType.RECOMMENDATION, confidence=0.92,
                       category="smartphones", max_price=500.0, min_price=None,
                       product_name=None, reasoning="test")
    o = MagicMock()
    o.handle = AsyncMock(return_value=(
        AgentResponse(success=True, data={"agent": "rec", "recommendations": []}), ir))
    with patch("app.api.v1.chat.get_orchestrator", return_value=o):
        r = client.post("/api/v1/chat", json={"message": "Smartphones under $500"})
    entities = r.json()["entities"]
    assert entities["category"] == "smartphones" and entities["max_price"] == 500.0

def test_chat_agent_failure_propagated():
    o = MagicMock()
    o.handle = AsyncMock(return_value=(
        AgentResponse(success=False, data={}, error="All agents failed"),
        _ir(IntentType.GENERAL)))
    with patch("app.api.v1.chat.get_orchestrator", return_value=o):
        r = client.post("/api/v1/chat", json={"message": "What time is it?"})
    assert r.json()["success"] is False and "All agents failed" in r.json()["error"]
