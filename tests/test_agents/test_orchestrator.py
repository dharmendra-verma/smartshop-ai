import pytest, time
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.orchestrator.orchestrator import Orchestrator, reset_orchestrator
from app.agents.orchestrator.circuit_breaker import CircuitBreaker, CircuitState
from app.agents.base import AgentResponse
from app.schemas.chat import IntentType

@pytest.fixture(autouse=True)
def reset(): reset_orchestrator(); yield; reset_orchestrator()

def _agent(name="mock", success=True):
    a = MagicMock(); a.name = name
    a.process = AsyncMock(return_value=AgentResponse(
        success=success, data={"agent": name, "answer": "ok"},
        error=None if success else "fail"))
    return a

def _orch(registry=None):
    reg = registry or {
        "recommendation": _agent("rec"), "review": _agent("rev"),
        "price": _agent("price"), "policy": _agent("pol"),
        "general": _agent("gen"),
    }
    return Orchestrator(registry=reg)

def _intent(intent: IntentType, **kw):
    from app.agents.orchestrator.intent_classifier import _IntentResult
    return _IntentResult(intent=intent, confidence=0.9, reasoning="test", **kw)

@pytest.mark.asyncio
async def test_routes_recommendation():
    o = _orch()
    with patch.object(o._classifier, "classify", new_callable=AsyncMock,
                      return_value=_intent(IntentType.RECOMMENDATION)):
        resp, ir = await o.handle("Find laptops", {})
    assert ir.intent == IntentType.RECOMMENDATION
    o._registry["recommendation"].process.assert_called_once()

@pytest.mark.asyncio
async def test_routes_price():
    o = _orch()
    with patch.object(o._classifier, "classify", new_callable=AsyncMock,
                      return_value=_intent(IntentType.PRICE)):
        resp, ir = await o.handle("Compare Galaxy S24 prices", {})
    assert ir.intent == IntentType.PRICE
    o._registry["price"].process.assert_called_once()

@pytest.mark.asyncio
async def test_comparison_routes_to_recommendation_with_flag():
    o = _orch()
    with patch.object(o._classifier, "classify", new_callable=AsyncMock,
                      return_value=_intent(IntentType.COMPARISON)):
        await o.handle("Compare iPhone vs Samsung", {})
    ctx = o._registry["recommendation"].process.call_args[0][1]
    assert ctx.get("compare_mode") is True

@pytest.mark.asyncio
async def test_falls_back_when_agent_none():
    o = _orch({"recommendation": None, "review": _agent("rev"),
               "price": _agent("p"), "policy": None, "general": _agent("gen")})
    with patch.object(o._classifier, "classify", new_callable=AsyncMock,
                      return_value=_intent(IntentType.RECOMMENDATION)):
        await o.handle("Find laptops", {})
    o._registry["general"].process.assert_called_once()

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    failing = _agent("rec", success=False)
    failing.process.side_effect = Exception("crash")
    o = _orch({"recommendation": failing, "general": _agent("gen"),
               "review": _agent("rev"), "price": _agent("p"), "policy": None})
    o._breakers["recommendation"]._threshold = 2
    for _ in range(2):
        with patch.object(o._classifier, "classify", new_callable=AsyncMock,
                          return_value=_intent(IntentType.RECOMMENDATION)):
            await o.handle("Find laptops", {})
    assert o._breakers["recommendation"].state == CircuitState.OPEN

def test_circuit_breaker_state_transitions():
    cb = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.01)
    assert cb.state == CircuitState.CLOSED
    cb.record_failure(); assert cb.state == CircuitState.CLOSED
    cb.record_failure(); assert cb.state == CircuitState.OPEN
    time.sleep(0.02);    assert cb.state == CircuitState.HALF_OPEN
    cb.record_success(); assert cb.state == CircuitState.CLOSED

def test_circuit_breaker_unavailable_when_open():
    cb = CircuitBreaker("test", failure_threshold=1)
    cb.record_failure(); assert not cb.is_available()
