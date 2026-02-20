# SCRUM-16: Develop Intent Router & Multi-Agent Orchestration Layer

## Story
**As the system**, I need intelligent routing so that user queries are directed to the appropriate specialized agent.

## Dependencies
- `app/agents/base.py` — `BaseAgent`, `AgentResponse`
- `app/agents/dependencies.py` — `AgentDependencies`
- `app/agents/recommendation/agent.py` — `RecommendationAgent` (existing)
- `app/agents/review/agent.py` — `ReviewSummarizationAgent` (existing)
- `app/agents/price/agent.py` — `PriceComparisonAgent` (added in SCRUM-14) ✅
- `app/agents/policy/agent.py` — `PolicyAgent` (added in SCRUM-15, may be stubbed if not yet merged)
- `app/core/config.py` — `OPENAI_MODEL`, `AGENT_TIMEOUT_SECONDS`
- `app/ui/streamlit_app.py` — line 99: `# TODO SCRUM-16: Replace detect_intent() with POST /api/v1/chat`
- `app/ui/api_client.py` — add `chat()` function
- **No new pip dependencies**

## Complexity Estimate
**High** — LLM classifier, orchestrator registry, circuit breaker, new unified endpoint, Streamlit wiring, 20 new tests

---

## Acceptance Criteria
- [ ] LLM-based intent classifier implemented (pydantic-ai structured output)
- [ ] Detects intents: recommendation, comparison, review, policy, price, general
- [ ] Extracts key entities (product_name, category, max_price, min_price)
- [ ] Routes to correct agent with enriched parameters
- [ ] Falls back gracefully for ambiguous queries → GeneralResponseAgent
- [ ] Circuit breaker per agent (opens after 3 consecutive failures)
- [ ] Intent classification accuracy ≥90%
- [ ] Routing latency under 500ms (classification step only)

---

## Technical Approach

### Architecture
```
POST /api/v1/chat  {message, session_id, max_results}
    │
    ▼
Orchestrator.handle(query, context)
    │
    ├──► IntentClassifier.classify(query)  → _IntentResult
    │        (GPT-4o-mini structured output, <500ms)
    │
    ├── "recommendation" → RecommendationAgent
    ├── "comparison"     → RecommendationAgent  (compare_mode=True)
    ├── "review"         → ReviewSummarizationAgent
    ├── "policy"         → PolicyAgent
    ├── "price"          → PriceComparisonAgent  ← NEW (SCRUM-14)
    └── "general"        → GeneralResponseAgent  (fallback)
         │
         ▼
    ChatResponse {message, intent, confidence, entities, agent_used, response}
```

### Intent Categories (6 total — includes "price" for SCRUM-14)
| Intent | Example query |
|---|---|
| recommendation | "Find smartphones under $500" |
| comparison | "Compare iPhone vs Samsung" |
| review | "What do customers say about Sony?" |
| policy | "What's the return policy?" |
| price | "Show me price comparison for Galaxy S24" |
| general | "Hello" / "Tell me about your service" |

### Circuit Breaker
- Per-agent `CircuitBreaker` instance in orchestrator
- `CLOSED → OPEN` after 3 consecutive failures
- `OPEN → HALF_OPEN` after 30s recovery timeout
- `HALF_OPEN → CLOSED` on next success

---

## File Structure

### New Files (8)
```
app/agents/orchestrator/
    __init__.py
    intent_classifier.py   # IntentClassifier — pydantic-ai + gpt-4o-mini
    circuit_breaker.py     # CircuitBreaker state machine
    general_agent.py       # GeneralResponseAgent (LLM fallback)
    orchestrator.py        # Orchestrator — registry + routing + fallback

app/api/v1/chat.py         # POST /api/v1/chat
app/schemas/chat.py        # ChatRequest, ChatResponse, IntentType

tests/test_agents/test_intent_classifier.py  # 6 tests
tests/test_agents/test_orchestrator.py       # 7 tests
tests/test_api/test_chat.py                  # 7 tests
```

### Modified Files (3)
```
app/main.py                # Include chat router
app/ui/api_client.py       # Add chat() function
app/ui/streamlit_app.py    # Replace detect_intent() with POST /api/v1/chat
```

---

## Task Breakdown

### Task 1 — `app/schemas/chat.py`
```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class IntentType(str, Enum):
    RECOMMENDATION = "recommendation"
    COMPARISON     = "comparison"
    REVIEW         = "review"
    POLICY         = "policy"
    PRICE          = "price"
    GENERAL        = "general"

class ChatRequest(BaseModel):
    message:     str = Field(..., min_length=1, max_length=1000)
    session_id:  Optional[str] = None
    max_results: int = Field(default=5, ge=1, le=20)

class ChatResponse(BaseModel):
    message:    str
    intent:     IntentType
    confidence: float
    entities:   dict
    agent_used: str
    response:   dict
    success:    bool
    error:      Optional[str] = None
```

### Task 2 — `app/agents/orchestrator/intent_classifier.py`
```python
"""LLM-based intent classifier with structured output."""
import logging
from dataclasses import dataclass
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from app.core.config import get_settings
from app.schemas.chat import IntentType

logger = logging.getLogger(__name__)

CLASSIFIER_PROMPT = """Classify user queries for a shopping assistant into one of:
- recommendation: wants product suggestions ("Find laptops under $800")
- comparison:     wants to compare products ("Compare iPhone vs Samsung")
- review:         wants customer opinion ("What do reviews say about X?")
- policy:         asks about store policies ("What's the return policy?")
- price:          wants price comparison across retailers ("Best price for Galaxy S24?")
- general:        anything else (greetings, service questions)

Extract entities: product_name, category, max_price (USD float), min_price (USD float).
Be accurate and concise."""

@dataclass
class _ClassifierDeps:
    pass

class _IntentResult(BaseModel):
    intent:       IntentType
    confidence:   float = Field(ge=0.0, le=1.0)
    product_name: Optional[str] = None
    category:     Optional[str] = None
    max_price:    Optional[float] = None
    min_price:    Optional[float] = None
    reasoning:    str = Field(description="One-sentence explanation")

class IntentClassifier:
    """Classifies intent using GPT-4o-mini. Falls back to GENERAL on any failure."""

    def __init__(self, model_name: str | None = None):
        s = get_settings()
        self._agent: Agent[_ClassifierDeps, _IntentResult] = Agent(
            model=OpenAIModel(model_name or s.OPENAI_MODEL),
            deps_type=_ClassifierDeps,
            output_type=_IntentResult,
            instructions=CLASSIFIER_PROMPT,
        )

    async def classify(self, query: str) -> _IntentResult:
        try:
            result = await self._agent.run(query, deps=_ClassifierDeps())
            logger.info("Intent: '%s' → %s (%.2f)", query[:60], result.output.intent, result.output.confidence)
            return result.output
        except Exception as exc:
            logger.error("IntentClassifier failed: %s — defaulting to GENERAL", exc)
            return _IntentResult(intent=IntentType.GENERAL, confidence=0.0,
                                 reasoning=f"Classification failed: {exc}")
```

### Task 3 — `app/agents/orchestrator/circuit_breaker.py`
```python
"""Per-agent circuit breaker."""
import time, logging
from enum import Enum

logger = logging.getLogger(__name__)

class CircuitState(str, Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, agent_name: str, failure_threshold: int = 3,
                 recovery_timeout: float = 30.0):
        self.agent_name        = agent_name
        self._threshold        = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._state            = CircuitState.CLOSED
        self._failures         = 0
        self._last_failure: float = 0.0

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure > self._recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("CircuitBreaker[%s]: OPEN → HALF_OPEN", self.agent_name)
        return self._state

    def is_available(self) -> bool:
        return self.state != CircuitState.OPEN

    def record_success(self):
        if self._state != CircuitState.CLOSED:
            logger.info("CircuitBreaker[%s]: → CLOSED", self.agent_name)
        self._state = CircuitState.CLOSED; self._failures = 0

    def record_failure(self):
        self._failures += 1; self._last_failure = time.time()
        if self._failures >= self._threshold or self._state == CircuitState.HALF_OPEN:
            if self._state != CircuitState.OPEN:
                logger.warning("CircuitBreaker[%s]: → OPEN (failures=%d)",
                               self.agent_name, self._failures)
            self._state = CircuitState.OPEN
```

### Task 4 — `app/agents/orchestrator/general_agent.py`
```python
"""Fallback agent for general / unclassified queries."""
import logging
from typing import Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from app.agents.base import BaseAgent, AgentResponse
from app.core.config import get_settings

logger = logging.getLogger(__name__)

GENERAL_PROMPT = """You are a helpful shopping assistant for SmartShop AI.
For queries you cannot handle with specific product data, provide a brief helpful response
and redirect the user toward product search, recommendations, reviews, price comparison,
or policy questions. Keep it to 2-3 sentences."""

class _Answer(BaseModel):
    answer: str = Field(description="Brief helpful response")

class GeneralResponseAgent(BaseAgent):
    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        super().__init__(name="general-agent")
        self._llm: Agent = Agent(model=OpenAIModel(model_name or settings.OPENAI_MODEL),
                                  output_type=_Answer, instructions=GENERAL_PROMPT)

    async def process(self, query: str, context: dict[str, Any]) -> AgentResponse:
        try:
            result = await self._llm.run(query)
            return AgentResponse(success=True,
                data={"answer": result.output.answer, "agent": self.name})
        except Exception as exc:
            logger.error("GeneralResponseAgent failed: %s", exc)
            return AgentResponse(success=True, data={
                "answer": ("I'm here to help with product recommendations, reviews, "
                           "price comparisons, and store policies. What can I help you with?"),
                "agent": self.name})
```

### Task 5 — `app/agents/orchestrator/orchestrator.py`
```python
"""Multi-agent orchestrator."""
import logging
from typing import Any
from app.agents.base import BaseAgent, AgentResponse
from app.agents.orchestrator.intent_classifier import IntentClassifier, _IntentResult
from app.agents.orchestrator.circuit_breaker import CircuitBreaker
from app.schemas.chat import IntentType

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, registry: dict[str, BaseAgent | None]):
        self._registry  = registry
        self._classifier = IntentClassifier()
        self._breakers   = {name: CircuitBreaker(name) for name in registry}

    async def handle(self, query: str, context: dict[str, Any]
                     ) -> tuple[AgentResponse, _IntentResult]:
        intent_result = await self._classifier.classify(query)
        intent_name   = intent_result.intent.value

        # Enrich context with extracted entities
        ctx = {**context}
        hints = {}
        if intent_result.category:    hints["category"]  = intent_result.category
        if intent_result.max_price:   hints["max_price"] = intent_result.max_price
        if intent_result.min_price:   hints["min_price"] = intent_result.min_price
        if hints: ctx["structured_hints"] = hints

        # "comparison" routes to recommendation with compare flag
        agent_key = intent_name
        if intent_name == "comparison":
            agent_key = "recommendation"; ctx["compare_mode"] = True

        agent   = self._registry.get(agent_key)
        breaker = self._breakers.get(agent_key)

        if agent is None or (breaker and not breaker.is_available()):
            logger.warning("Orchestrator: '%s' unavailable → general", agent_key)
            agent_key = "general"
            agent   = self._registry["general"]
            breaker = self._breakers["general"]

        try:
            response = await agent.process(query, ctx)
            if breaker:
                breaker.record_success() if response.success else breaker.record_failure()
            return response, intent_result
        except Exception as exc:
            logger.error("Orchestrator: '%s' raised: %s", agent_key, exc)
            if breaker: breaker.record_failure()
            fallback = self._registry.get("general")
            if fallback:
                return await fallback.process(query, context), intent_result
            return AgentResponse(success=False, data={}, error=str(exc)), intent_result


def build_orchestrator() -> "Orchestrator":
    from app.agents.recommendation.agent import RecommendationAgent
    from app.agents.review.agent import ReviewSummarizationAgent
    from app.agents.price.agent import PriceComparisonAgent
    from app.agents.orchestrator.general_agent import GeneralResponseAgent

    registry: dict[str, BaseAgent | None] = {
        "recommendation": RecommendationAgent(),
        "review":         ReviewSummarizationAgent(),
        "price":          PriceComparisonAgent(),
        "general":        GeneralResponseAgent(),
        "policy":         None,  # populated when SCRUM-15 is merged
    }
    try:
        from app.agents.policy.agent import PolicyAgent
        registry["policy"] = PolicyAgent()
        logger.info("Orchestrator: PolicyAgent registered")
    except ImportError:
        logger.info("Orchestrator: PolicyAgent not yet available (SCRUM-15 pending)")
    return Orchestrator(registry=registry)

_orchestrator: "Orchestrator | None" = None

def get_orchestrator() -> "Orchestrator":
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = build_orchestrator()
    return _orchestrator

def reset_orchestrator():
    global _orchestrator
    _orchestrator = None
```

### Task 6 — `app/api/v1/chat.py`
```python
"""Unified chat endpoint."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.orchestrator.orchestrator import get_orchestrator
from app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/chat", response_model=ChatResponse, status_code=200)
async def chat(request: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    """
    Unified chat endpoint. Classifies intent and routes to the appropriate agent:
    recommendation/comparison → RecommendationAgent,
    review → ReviewSummarizationAgent,
    price → PriceComparisonAgent,
    policy → PolicyAgent,
    general → GeneralResponseAgent (fallback).
    """
    deps = AgentDependencies.from_db(db)
    context = {"deps": deps, "max_results": request.max_results, "session_id": request.session_id}

    orchestrator = get_orchestrator()
    response, intent_result = await orchestrator.handle(request.message, context)

    return ChatResponse(
        message=request.message,
        intent=intent_result.intent,
        confidence=intent_result.confidence,
        entities={"product_name": intent_result.product_name, "category": intent_result.category,
                  "max_price": intent_result.max_price, "min_price": intent_result.min_price},
        agent_used=response.data.get("agent", "unknown"),
        response=response.data,
        success=response.success,
        error=response.error,
    )
```

### Task 7 — `app/main.py`, `app/ui/api_client.py`, `app/ui/streamlit_app.py`

**`app/main.py`** — add after existing v1 routers:
```python
from app.api.v1.chat import router as chat_router
app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
```

**`app/ui/api_client.py`** — add function:
```python
def chat(api_url: str, message: str, session_id: str | None = None,
         max_results: int = 5) -> dict[str, Any]:
    """Call POST /api/v1/chat."""
    payload: dict = {"message": message, "max_results": max_results}
    if session_id:
        payload["session_id"] = session_id
    return _post(f"{api_url}/api/v1/chat", payload)
```

**`app/ui/streamlit_app.py`** — replace the `detect_intent()` block (~lines 99-116) with:
```python
from app.ui.api_client import chat as chat_api

result = chat_api(api_url, message=prompt,
                  session_id=st.session_state.get("session_id"), max_results=5)
if result["success"]:
    data   = result["data"]
    intent = data.get("intent", "general")
    agent_resp = data.get("response", {})
    if intent == "review":
        reply = format_review_message(agent_resp)
    elif intent in ("recommendation", "comparison"):
        reply = format_recommendation_message(agent_resp)
    elif intent == "price":
        best  = agent_resp.get("best_deal", "")
        rec   = agent_resp.get("recommendation", "")
        reply = f"🏆 **Best Deal:** {best}\n\n{rec}" if best else rec or "No comparison data."
    elif intent == "policy":
        answer  = agent_resp.get("answer", "")
        sources = ", ".join(f"_{s}_" for s in agent_resp.get("sources", []))
        reply   = f"{answer}\n\n📋 **Source:** {sources}" if sources else answer
    else:
        reply = agent_resp.get("answer", "I'm not sure how to help with that.")
else:
    reply = f"⚠️ {result['error']}"
```

### Task 8 — Tests

#### `tests/test_agents/test_intent_classifier.py` (6 tests)
```python
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
```

#### `tests/test_agents/test_orchestrator.py` (7 tests)
```python
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
```

#### `tests/test_api/test_chat.py` (7 tests)
```python
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
```

---

## Testing Requirements
- **+20 new tests** (6 classifier + 7 orchestrator + 7 API)
- All 235 tests from SCRUM-15 must pass
- Target: **255 total**

## Key Notes for Claude Code
1. `IntentType.PRICE` is a new intent added for SCRUM-14's `PriceComparisonAgent` — include it in the classifier prompt
2. `build_orchestrator()` uses try/except for `PolicyAgent` so it's optional (SCRUM-15 dependency)
3. `reset_orchestrator()` must be called in test `autouse` fixtures to avoid singleton pollution
4. The Streamlit `detect_intent()` in `chat_helpers.py` is kept as-is (used for offline fallback); only its usage in `streamlit_app.py` is replaced
5. `compare_prices` import in `streamlit_app.py` was already added in SCRUM-14 — do not duplicate
