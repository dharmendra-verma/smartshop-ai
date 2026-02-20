# SCRUM-15: Build FAQ & Policy Agent with RAG Implementation

## Story
**As a customer**, I want quick answers to store policy questions so that I don't have to search through lengthy policy documents.

## Dependencies
- `app/models/policy.py` — `Policy` model (policy_id, policy_type, description, conditions, timeframe)
- `app/agents/base.py` — `BaseAgent`, `AgentResponse`
- `app/agents/dependencies.py` — `AgentDependencies` (to be extended with vector_store)
- `app/core/cache.py` — existing TTLCache/RedisCache pattern (reuse for PolicyVectorStore)
- `app/core/config.py` — `VECTOR_STORE_PATH`, `EMBEDDING_MODEL` ("text-embedding-3-small"), `EMBEDDING_DIMENSION` (1536), `OPENAI_API_KEY`
- `app/main.py` — register new policy router
- `tests/conftest.py` — existing `db_session`, `sample_policy` fixtures
- **New pip dependency**: `faiss-cpu` (install if not present)

## Complexity Estimate
**Medium-High** — FAISS vector store, OpenAI embeddings, new agent + API endpoint + 13 tests

---

## Acceptance Criteria
- [ ] RAG system implemented with FAISS vector database
- [ ] Store policies embedded using OpenAI Embeddings (`text-embedding-3-small`)
- [ ] Agent retrieves relevant policy sections via semantic search
- [ ] Provides contextual answers with source citations (policy_type + section)
- [ ] Handles queries like "What is the return policy for electronics?"
- [ ] Cites specific policy sections in response
- [ ] Response time under 2 seconds
- [ ] Accuracy verified against actual policy documents

---

## Technical Approach

### Architecture
```
User Query
    │
    ▼
POST /api/v1/policy/ask
    │
    ▼
PolicyAgent.process(query, context)
    │
    ├──► Tool: retrieve_policy_sections(query, k=3)
    │        → PolicyVectorStore.search(query)  [FAISS cosine similarity]
    │        → returns top-k PolicyChunk objects
    │
    └──► pydantic-ai Agent (gpt-4o-mini)
             Output: _PolicyAnswer(answer, sources, confidence)
             │
             ▼
    AgentResponse → PolicyAskResponse
```

### FAISS Vector Store Design
- **Index type**: `IndexFlatIP` (inner product) with L2-normalised vectors → cosine similarity
- **Chunk unit**: one chunk = one `Policy` DB row; text = `f"{policy_type}: {description}\n{conditions}"`
- **Persistence**: `./data/embeddings/faiss_index.bin` + `./data/embeddings/faiss_metadata.json`
- **Rebuild trigger**: on startup if saved metadata count ≠ current DB row count
- **Top-k**: 3 chunks per query

---

## File Structure

### New Files (7)
```
app/agents/policy/
    __init__.py
    agent.py          # PolicyAgent(BaseAgent) + PolicyDependencies + get_vector_store()
    prompts.py        # SYSTEM_PROMPT for policy QA
    tools.py          # retrieve_policy_sections() pydantic-ai tool
    vector_store.py   # PolicyVectorStore — FAISS + OpenAI embeddings

app/api/v1/policy.py  # POST /api/v1/policy/ask
app/schemas/policy.py # PolicyAskRequest, PolicyAskResponse

tests/test_agents/test_policy_agent.py  # 6 unit tests
tests/test_api/test_policy.py           # 7 TestClient tests
```

---

## Task Breakdown

### Task 1 — `app/agents/policy/vector_store.py`
```python
"""FAISS vector store for store policies."""
import json, logging, numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import faiss
from openai import OpenAI
from app.core.config import get_settings

logger = logging.getLogger(__name__)
FAISS_INDEX_PATH = Path("./data/embeddings/faiss_index.bin")
FAISS_META_PATH  = Path("./data/embeddings/faiss_metadata.json")
TOP_K = 3

@dataclass
class PolicyChunk:
    policy_id: int
    policy_type: str
    text: str
    score: float
    description: str
    conditions: str

class PolicyVectorStore:
    def __init__(self):
        s = get_settings()
        self._client = OpenAI(api_key=s.OPENAI_API_KEY)
        self._model  = s.EMBEDDING_MODEL       # "text-embedding-3-small"
        self._dim    = s.EMBEDDING_DIMENSION   # 1536
        self._index: Optional[faiss.IndexFlatIP] = None
        self._metadata: list[dict] = []

    # ── Build / Load ──────────────────────────────────────────────────
    def build(self, policies: list) -> None:
        if not policies:
            return
        texts = [self._to_text(p) for p in policies]
        vecs  = self._embed_batch(texts)
        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(vecs)
        self._metadata = [
            {"policy_id": p.policy_id, "policy_type": p.policy_type,
             "text": texts[i], "description": p.description, "conditions": p.conditions}
            for i, p in enumerate(policies)
        ]
        self._save()
        logger.info("PolicyVectorStore: indexed %d policies", len(policies))

    def load_or_build(self, policies: list) -> None:
        if FAISS_INDEX_PATH.exists() and FAISS_META_PATH.exists():
            meta = json.loads(FAISS_META_PATH.read_text())
            if len(meta) == len(policies):
                self._load(); return
        self.build(policies)

    # ── Search ────────────────────────────────────────────────────────
    def search(self, query: str, k: int = TOP_K) -> list[PolicyChunk]:
        if self._index is None or self._index.ntotal == 0:
            return []
        q   = self._embed_batch([query])
        scores, idxs = self._index.search(q, min(k, self._index.ntotal))
        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0: continue
            m = self._metadata[idx]
            results.append(PolicyChunk(policy_id=m["policy_id"], policy_type=m["policy_type"],
                text=m["text"], score=float(score), description=m["description"], conditions=m["conditions"]))
        return results

    # ── Private ───────────────────────────────────────────────────────
    @staticmethod
    def _to_text(p) -> str:
        return f"{p.policy_type}: {p.description}\n{p.conditions}"

    def _embed_batch(self, texts: list[str]) -> np.ndarray:
        resp = self._client.embeddings.create(model=self._model, input=texts)
        vecs = np.array([e.embedding for e in resp.data], dtype=np.float32)
        faiss.normalize_L2(vecs)
        return vecs

    def _save(self):
        FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(FAISS_INDEX_PATH))
        FAISS_META_PATH.write_text(json.dumps(self._metadata))

    def _load(self):
        self._index    = faiss.read_index(str(FAISS_INDEX_PATH))
        self._metadata = json.loads(FAISS_META_PATH.read_text())
        logger.info("PolicyVectorStore: loaded %d policies from disk", len(self._metadata))
```

### Task 2 — `app/agents/policy/prompts.py`
```python
SYSTEM_PROMPT = """You are a store policy expert for SmartShop AI.

Answer customer questions about store policies accurately using only the provided policy sections.

Rules:
1. Answer ONLY based on the provided policy sections — do not invent details.
2. Always cite the specific policy_type(s) you used as sources.
3. Be concise and direct.
4. If the sections do not fully answer the question, say so clearly.
5. Confidence: "high" if sections directly answer the question, "medium" if partial, "low" if tangential.
"""
```

### Task 3 — `app/agents/policy/tools.py`
```python
"""pydantic-ai tools for PolicyAgent."""
import logging
from pydantic_ai import RunContext
from app.agents.dependencies import AgentDependencies

logger = logging.getLogger(__name__)

async def retrieve_policy_sections(ctx: RunContext[AgentDependencies], query: str, k: int = 3) -> str:
    """
    Retrieve the most relevant policy sections for the query using semantic search.
    Returns formatted text ready for the LLM.
    Args:
        query: The user's policy question
        k: Number of sections to retrieve (default 3)
    """
    vector_store = getattr(ctx.deps, "vector_store", None)
    if vector_store is None:
        return _db_fallback(ctx.deps.db, query)

    chunks = vector_store.search(query, k=k)
    if not chunks:
        return "No relevant policy sections found."

    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(f"[Section {i} — {c.policy_type} (score: {c.score:.2f})]:\n{c.text}")
    return "\n\n".join(parts)


def _db_fallback(db, query: str) -> str:
    from app.models.policy import Policy
    policies = db.query(Policy).limit(5).all()
    kws = query.lower().split()
    results = [f"{p.policy_type}: {p.description}\n{p.conditions}"
               for p in policies if any(k in f"{p.description} {p.conditions}".lower() for k in kws)]
    return "\n\n".join(results[:3]) if results else "No matching policies found."
```

### Task 4 — `app/agents/policy/agent.py`
```python
"""FAQ & Policy Agent with RAG."""
import logging
from dataclasses import dataclass
from typing import Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from app.agents.base import BaseAgent, AgentResponse
from app.agents.dependencies import AgentDependencies
from app.agents.policy.prompts import SYSTEM_PROMPT
from app.agents.policy import tools
from app.core.config import get_settings

logger = logging.getLogger(__name__)

@dataclass
class PolicyDependencies(AgentDependencies):
    """Extends AgentDependencies with the FAISS vector store."""
    vector_store: Any = None  # PolicyVectorStore

class _PolicyAnswer(BaseModel):
    answer:     str = Field(description="Direct answer to the policy question")
    sources:    list[str] = Field(description="Policy section names/types cited")
    confidence: str = Field(description="'high', 'medium', or 'low'")

def _build_agent(model_name: str) -> Agent:
    agent: Agent[PolicyDependencies, _PolicyAnswer] = Agent(
        model=OpenAIModel(model_name),
        deps_type=PolicyDependencies,
        output_type=_PolicyAnswer,
        instructions=SYSTEM_PROMPT,
    )
    agent.tool(tools.retrieve_policy_sections)
    return agent

_vector_store = None

def get_vector_store():
    global _vector_store
    if _vector_store is None:
        from app.agents.policy.vector_store import PolicyVectorStore
        _vector_store = PolicyVectorStore()
    return _vector_store

class PolicyAgent(BaseAgent):
    """FAQ & Policy agent — RAG over store policies via FAISS + GPT-4o-mini."""

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        super().__init__(name="policy-agent")
        self._agent = _build_agent(model_name or settings.OPENAI_MODEL)

    async def process(self, query: str, context: dict[str, Any]) -> AgentResponse:
        deps: AgentDependencies = context.get("deps")
        if deps is None:
            return AgentResponse(success=False, data={},
                error="AgentDependencies not provided in context['deps']")

        vector_store = context.get("vector_store") or get_vector_store()
        policy_deps  = PolicyDependencies(db=deps.db, settings=deps.settings,
                                          vector_store=vector_store)
        try:
            result = await self._agent.run(query, deps=policy_deps)
            ans: _PolicyAnswer = result.output
            return AgentResponse(success=True, data={
                "query": query, "answer": ans.answer, "sources": ans.sources,
                "confidence": ans.confidence, "agent": self.name,
            })
        except Exception as exc:
            logger.error("PolicyAgent failed: %s", exc, exc_info=True)
            return AgentResponse(success=False, data={},
                error=f"Policy agent error: {str(exc)}")
```

### Task 5 — `app/schemas/policy.py`
```python
from pydantic import BaseModel, Field

class PolicyAskRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500,
        description="Policy question, e.g. 'What is the return policy for electronics?'")
    k: int = Field(default=3, ge=1, le=10, description="Number of policy chunks to retrieve")

class PolicyAskResponse(BaseModel):
    query:      str
    answer:     str
    sources:    list[str]
    confidence: str
    agent:      str
```

### Task 6 — `app/api/v1/policy.py`
```python
"""Policy FAQ API endpoint."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.policy.agent import PolicyAgent, get_vector_store
from app.schemas.policy import PolicyAskRequest, PolicyAskResponse

logger = logging.getLogger(__name__)
router = APIRouter()
_agent = PolicyAgent()

@router.post("/policy/ask", response_model=PolicyAskResponse, status_code=200)
async def ask_policy(request: PolicyAskRequest, db: Session = Depends(get_db)) -> PolicyAskResponse:
    """Answer a policy question using RAG (FAISS semantic search + GPT-4o-mini)."""
    deps = AgentDependencies.from_db(db)
    vs   = get_vector_store()

    if vs._index is None:
        from app.models.policy import Policy
        vs.load_or_build(db.query(Policy).all())

    response = await _agent.process(request.query, context={"deps": deps, "vector_store": vs})
    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)

    return PolicyAskResponse(
        query=response.data["query"],   answer=response.data["answer"],
        sources=response.data["sources"], confidence=response.data["confidence"],
        agent=response.data["agent"],
    )
```

### Task 7 — Register router + startup event in `app/main.py`
```python
# Add import:
from app.api.v1.policy import router as policy_router
app.include_router(policy_router, prefix="/api/v1", tags=["policy"])

# Add startup event to pre-build FAISS index:
@app.on_event("startup")
async def startup_vector_store():
    from app.agents.policy.agent import get_vector_store
    from app.models.policy import Policy
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        policies = db.query(Policy).all()
        if policies:
            get_vector_store().load_or_build(policies)
            logger.info("PolicyVectorStore ready with %d policies", len(policies))
    finally:
        db.close()
```

### Task 8 — Tests

#### `tests/test_agents/test_policy_agent.py` (6 tests)
```python
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
```

#### `tests/test_api/test_policy.py` (7 tests)
```python
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
```

---

## Testing Requirements
- **+13 new tests** (6 agent + 7 API)
- All 222 existing tests must continue to pass
- Target: **235 total**

## Key Notes for Claude Code
1. `pip install faiss-cpu` if not already installed
2. `data/embeddings/` directory is created automatically by `_save()`
3. Mock `get_vector_store()` in API tests — avoid FAISS on CI
4. In test fixtures, reset `_vector_store = None` via `app.agents.policy.agent._vector_store = None`
5. Response time <2s: FAISS search is ~1ms; OpenAI embedding + LLM call is the bottleneck
