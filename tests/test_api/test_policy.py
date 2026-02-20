import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.agents.base import AgentResponse

client = TestClient(app)

def _ok(answer="30 days.", sources=None, confidence="high"):
    return AgentResponse(success=True, data={
        "query": "return policy", "answer": answer,
        "sources": sources or ["return_policy"],
        "confidence": confidence, "agent": "policy-agent",
    })

def test_ask_success():
    with patch("app.api.v1.policy._agent.process", new_callable=AsyncMock) as m, \
         patch("app.api.v1.policy.get_vector_store", return_value=MagicMock(_index=MagicMock())):
        m.return_value = _ok()
        r = client.post("/api/v1/policy/ask", json={"query": "What is the return policy?"})
    assert r.status_code == 200
    assert r.json()["answer"] == "30 days."

def test_empty_query(): assert client.post("/api/v1/policy/ask", json={"query": ""}).status_code == 422
def test_short_query(): assert client.post("/api/v1/policy/ask", json={"query": "hi"}).status_code == 422
def test_missing_query(): assert client.post("/api/v1/policy/ask", json={}).status_code == 422

def test_agent_failure():
    with patch("app.api.v1.policy._agent.process", new_callable=AsyncMock) as m, \
         patch("app.api.v1.policy.get_vector_store", return_value=MagicMock(_index=MagicMock())):
        m.return_value = AgentResponse(success=False, data={}, error="LLM unavailable")
        r = client.post("/api/v1/policy/ask", json={"query": "What is the shipping policy?"})
    assert r.status_code == 500
    assert "LLM unavailable" in r.json()["detail"]

def test_custom_k():
    with patch("app.api.v1.policy._agent.process", new_callable=AsyncMock) as m, \
         patch("app.api.v1.policy.get_vector_store", return_value=MagicMock(_index=MagicMock())):
        m.return_value = _ok()
        assert client.post("/api/v1/policy/ask", json={"query": "warranty info?", "k": 5}).status_code == 200

def test_low_confidence_still_200():
    with patch("app.api.v1.policy._agent.process", new_callable=AsyncMock) as m, \
         patch("app.api.v1.policy.get_vector_store", return_value=MagicMock(_index=MagicMock())):
        m.return_value = _ok(answer="Unsure...", confidence="low")
        r = client.post("/api/v1/policy/ask", json={"query": "can I return opened software?"})
    assert r.status_code == 200
    assert r.json()["confidence"] == "low"
