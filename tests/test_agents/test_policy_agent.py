import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.policy.agent import PolicyAgent
from app.agents.base import AgentResponse

@pytest.fixture
def mock_deps(db_session):
    from app.agents.dependencies import AgentDependencies
    from app.core.config import get_settings
    return AgentDependencies(db=db_session, settings=get_settings())

@pytest.fixture
def mock_vs():
    from app.agents.policy.vector_store import PolicyChunk
    vs = MagicMock()
    vs._index = MagicMock()
    vs.search.return_value = [
        PolicyChunk(policy_id=1, policy_type="return_policy",
            text="return_policy: 30 days\nOriginal receipt required.",
            score=0.95, description="30 days", conditions="Original receipt required.")
    ]
    return vs

@pytest.mark.asyncio
async def test_process_success(mock_deps, mock_vs):
    agent = PolicyAgent()
    with patch.object(agent._agent, "run", new_callable=AsyncMock) as m:
        r = MagicMock()
        r.output.answer = "30 days return window."
        r.output.sources = ["return_policy"]
        r.output.confidence = "high"
        m.return_value = r
        resp = await agent.process("Return policy?", {"deps": mock_deps, "vector_store": mock_vs})
    assert resp.success is True
    assert resp.data["confidence"] == "high"
    assert "return_policy" in resp.data["sources"]

@pytest.mark.asyncio
async def test_process_missing_deps():
    agent = PolicyAgent()
    resp = await agent.process("Return policy?", context={})
    assert resp.success is False
    assert "AgentDependencies not provided" in resp.error

@pytest.mark.asyncio
async def test_process_exception_handled(mock_deps, mock_vs):
    agent = PolicyAgent()
    with patch.object(agent._agent, "run", side_effect=Exception("LLM failure")):
        resp = await agent.process("Warranty?", {"deps": mock_deps, "vector_store": mock_vs})
    assert resp.success is False
    assert "Policy agent error" in resp.error

def test_agent_name():
    assert PolicyAgent().name == "policy-agent"

@pytest.mark.asyncio
async def test_policy_dependencies_constructed(mock_deps, mock_vs):
    from app.agents.policy.agent import PolicyDependencies
    agent = PolicyAgent()
    captured = []
    async def capture(query, deps):
        captured.append(deps)
        r = MagicMock()
        r.output.answer = "30 days."
        r.output.sources = ["return_policy"]
        r.output.confidence = "high"
        return r
    with patch.object(agent._agent, "run", side_effect=capture):
        await agent.process("Return policy?", {"deps": mock_deps, "vector_store": mock_vs})
    assert isinstance(captured[0], PolicyDependencies)
    assert captured[0].vector_store is mock_vs

@pytest.mark.asyncio
async def test_low_confidence_returned(mock_deps, mock_vs):
    agent = PolicyAgent()
    with patch.object(agent._agent, "run", new_callable=AsyncMock) as m:
        r = MagicMock()
        r.output.answer = "Not sure, but..."
        r.output.sources = []
        r.output.confidence = "low"
        m.return_value = r
        resp = await agent.process("Can I return opened software?",
                                   {"deps": mock_deps, "vector_store": mock_vs})
    assert resp.data["confidence"] == "low"
