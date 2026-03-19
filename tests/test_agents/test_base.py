"""Tests for BaseAgent._handle_agent_error()."""

import pytest
from unittest.mock import patch
from app.agents.base import BaseAgent, AgentResponse
from app.core.exceptions import AgentRateLimitError, AgentTimeoutError


class _ConcreteAgent(BaseAgent):
    async def process(self, query, context):
        return AgentResponse(success=True, data={})


# Fake exception classes whose __name__ matches the string checks in _handle_agent_error
class _FakeRateLimitError(Exception):
    pass


class _FakeTimeoutError(Exception):
    pass


# Patch their class names so type(exc).__name__ contains the expected substring
_FakeRateLimitError.__name__ = "RateLimitError"
_FakeTimeoutError.__name__ = "TimeoutError"


@pytest.fixture
def agent():
    return _ConcreteAgent("test-agent")


def test_handle_rate_limit_raises(agent):
    exc = _FakeRateLimitError("quota exceeded")
    with pytest.raises(AgentRateLimitError):
        agent._handle_agent_error(exc, query="test query")


def test_handle_timeout_raises(agent):
    exc = _FakeTimeoutError("timed out")
    with pytest.raises(AgentTimeoutError):
        agent._handle_agent_error(exc)


def test_handle_generic_returns_failure(agent):
    exc = ValueError("something broke")
    resp = agent._handle_agent_error(exc)
    assert resp.success is False
    assert resp.error == "Service temporarily unavailable."


def test_handle_rate_limit_records_failure(agent):
    exc = _FakeRateLimitError("quota")
    with patch("app.core.alerting.record_failure") as mock_rf:
        with pytest.raises(AgentRateLimitError):
            agent._handle_agent_error(exc, query="q")
        mock_rf.assert_called_once_with("test-agent")


def test_handle_generic_records_failure(agent):
    exc = ValueError("oops")
    with patch("app.core.alerting.record_failure") as mock_rf:
        agent._handle_agent_error(exc)
        mock_rf.assert_called_once_with("test-agent")
