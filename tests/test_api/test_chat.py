import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.agents.base import AgentResponse
from app.schemas.chat import IntentType
from app.agents.orchestrator.orchestrator import reset_orchestrator
from app.services.session.session_manager import get_session_manager, reset_session_manager
from app.services.session.session_store import reset_session_store

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset(): 
    reset_orchestrator()
    reset_session_store()
    reset_session_manager()
    yield
    reset_orchestrator()
    reset_session_store()
    reset_session_manager()

def _ir(intent=IntentType.RECOMMENDATION, **kw):
    from app.agents.orchestrator.intent_classifier import _IntentResult
    return _IntentResult(intent=intent, confidence=0.9, reasoning="test", **kw)

def _mock_orch(intent=IntentType.RECOMMENDATION, agent="rec-agent"):
    o = MagicMock()
    o.handle = AsyncMock(return_value=(
        AgentResponse(success=True, data={"agent": agent, "answer": "ok", "recommendations": []}),
        _ir(intent)))
    return o

def test_chat_creates_session_when_none_provided():
    with patch("app.api.v1.chat.get_orchestrator", return_value=_mock_orch()):
        r = client.post("/api/v1/chat", json={"message": "hello"})
    assert r.status_code == 200
    assert "session_id" in r.json()
    assert len(r.json()["session_id"]) == 36

def test_chat_reuses_existing_session_id():
    with patch("app.api.v1.chat.get_orchestrator", return_value=_mock_orch()):
        sid = "my-test-session"
        r = client.post("/api/v1/chat", json={"message": "hello", "session_id": sid})
    assert r.status_code == 200
    assert r.json()["session_id"] == sid

def test_chat_enriches_query_with_history():
    o = _mock_orch()
    with patch("app.api.v1.chat.get_orchestrator", return_value=o):
        sid = "sess-1"
        client.post("/api/v1/chat", json={"message": "hello 1", "session_id": sid})
        client.post("/api/v1/chat", json={"message": "hello 2", "session_id": sid})
    
    call_args = o.handle.call_args[0]
    enriched = call_args[0]
    assert "[CONVERSATION HISTORY]" in enriched
    assert "user: hello 1" in enriched
    assert "user: hello 2" in enriched

def test_clear_session_returns_204():
    mgr = get_session_manager()
    sid = mgr.create_session()
    mgr.append_turn(sid, "q", "a")
    r = client.delete(f"/api/v1/chat/session/{sid}")
    assert r.status_code == 204
    assert mgr.get_history(sid) == []

def test_clear_session_idempotent_on_missing_id():
    r = client.delete("/api/v1/chat/session/missing-session-id")
    assert r.status_code == 204

def test_chat_endpoint_integration_with_session_store():
    # Use real TTLCache implicitly (reset fixtures clear memory)
    with patch("app.api.v1.chat.get_orchestrator", return_value=_mock_orch()):
        r = client.post("/api/v1/chat", json={"message": "hello"})
        sid = r.json()["session_id"]
        mgr = get_session_manager()
        h = mgr.get_history(sid)
        assert len(h) == 2
        assert h[0].content == "hello"

def test_chat_history_grows_then_clears():
    with patch("app.api.v1.chat.get_orchestrator", return_value=_mock_orch()):
        r = client.post("/api/v1/chat", json={"message": "first"})
        sid = r.json()["session_id"]
        client.post("/api/v1/chat", json={"message": "second", "session_id": sid})
    
    mgr = get_session_manager()
    assert len(mgr.get_history(sid)) == 4
    
    client.delete(f"/api/v1/chat/session/{sid}")
    assert len(mgr.get_history(sid)) == 0

def test_chat_empty_message(): assert client.post("/api/v1/chat", json={"message": ""}).status_code == 422
def test_chat_missing_message(): assert client.post("/api/v1/chat", json={}).status_code == 422
