# SCRUM-21 — Write Comprehensive Documentation

**Story:** Write comprehensive documentation
**Jira:** https://projecttracking.atlassian.net/browse/SCRUM-21
**Status:** In Progress
**Priority:** Medium
**Depends On:** All completed stories (SCRUM-8 → SCRUM-62) + Eval framework (tests/evals/)

---

## Acceptance Criteria

- [ ] README.md with project overview and setup instructions
- [ ] Architecture documentation with system diagrams
- [ ] API documentation (auto-generated from FastAPI)
- [ ] Agent documentation (capabilities, prompts, tools)
- [ ] Data pipeline documentation
- [ ] Deployment guide (Docker, cloud platforms)
- [ ] Troubleshooting guide
- [ ] Code comments for complex logic

---

## Current State Analysis

### What Already Exists (do NOT duplicate)
| File | Content |
|------|---------|
| `README.md` | Project overview, vision, features, quick start, architecture overview, tech stack |
| `QUICKSTART.md` | 5-minute quick start guide |
| `RUNNING_SERVICES.md` | How to start FastAPI + Streamlit |
| `RUN_ON_WINDOWS.md` | Windows-specific execution instructions |
| `docs/ARCHITECTURE.md` | Comprehensive system architecture with diagrams |
| `docs/DATABASE.md` | Database schema, migrations, entity relationships |
| `docs/PROJECT_STATUS.md` | Sprint status tracker |

### What Is Missing (SCRUM-21 must create)
1. **`docs/API_REFERENCE.md`** — Full endpoint reference with request/response examples
2. **`docs/AGENTS.md`** — Each agent's purpose, prompts, tools, output schemas
3. **`docs/TESTING.md`** — Testing strategy, patterns, mocking guide, how to run tests
4. **`docs/EVALS.md`** ⭐ NEW — LLM-as-judge eval framework: architecture, how to run, how to extend, all eval test files documented
5. **`docs/DEPLOYMENT.md`** — Docker, docker-compose, env vars, production checklist
6. **`docs/DATA_PIPELINE.md`** — CSV ingestion, data schemas, how to reload/extend data
7. **`docs/MONITORING.md`** — Metrics endpoints, alerting config, performance targets
8. **`docs/DEVELOPER_GUIDE.md`** — How to add new agents, extend the system, contribute
9. **`docs/TROUBLESHOOTING.md`** — Common issues, error codes, recovery procedures
10. **Inline code comments** — Complex logic in caching, circuit breaker, FAISS RAG, orchestrator, judge
11. **README.md update** — Link to new docs, add eval tests section with run command

---

## Technical Approach

### Strategy: Document the real, implemented system
- No fabrication — every doc section must reflect actual code in `app/`
- Use FastAPI's auto-generated OpenAPI schema as the source of truth for API docs
- Derive agent docs from actual prompts in `agents/*/prompts.py`
- Testing guide must match actual patterns found in `tests/`

### Document Structure Target
```
docs/
├── ARCHITECTURE.md          ← exists (update with eval framework layer)
├── DATABASE.md              ← exists (no changes needed)
├── API_REFERENCE.md         ← CREATE
├── AGENTS.md                ← CREATE
├── TESTING.md               ← CREATE
├── EVALS.md                 ← CREATE ⭐ (LLM-as-judge eval framework)
├── DEPLOYMENT.md            ← CREATE
├── DATA_PIPELINE.md         ← CREATE
├── MONITORING.md            ← CREATE
├── DEVELOPER_GUIDE.md       ← CREATE
└── TROUBLESHOOTING.md       ← CREATE
```

---

## File Map

### Files to CREATE

| File | Sections | Est. Lines |
|------|----------|-----------|
| `docs/API_REFERENCE.md` | Overview, Auth, Products, Recommendations, Reviews, Price, Policy, Chat, Health | ~300 |
| `docs/AGENTS.md` | BaseAgent, RecommendationAgent, ReviewAgent, PriceAgent, PolicyAgent, Orchestrator, GeneralAgent, IntentClassifier | ~250 |
| `docs/TESTING.md` | Test layout, running tests, mocking patterns, TestModel, AsyncMock, DB mock, eval tests pointer | ~200 |
| `docs/EVALS.md` | Why evals, architecture, LLMJudge, EvalScore, EvalCase, running evals, file index, extending, CI integration | ~250 |
| `docs/DEPLOYMENT.md` | Prerequisites, docker-compose, env vars, production checklist, health checks | ~200 |
| `docs/DATA_PIPELINE.md` | CSV schemas, ingesters, FAISS index build, how to extend | ~150 |
| `docs/MONITORING.md` | /health endpoints, metrics API, alerting, performance targets, Logfire | ~120 |
| `docs/DEVELOPER_GUIDE.md` | How to add an agent, extend the API, update the UI, add eval test | ~200 |
| `docs/TROUBLESHOOTING.md` | Startup issues, DB connection, Redis, OpenAI quota, FAISS, Streamlit, eval failures | ~160 |

### Files to MODIFY

| File | Change |
|------|--------|
| `README.md` | Add docs index table, add `tests/evals/` to test section with run command, update total test count to 495 |
| `docs/ARCHITECTURE.md` | Add eval tests layer, update test counts, add caching diagram |
| `app/agents/orchestrator/orchestrator.py` | Add docstrings to `handle()`, `build_orchestrator()` |
| `app/agents/orchestrator/circuit_breaker.py` | Add class/method docstrings |
| `app/core/cache.py` | Add module docstring explaining Redis→TTLCache fallback |
| `app/core/llm_cache.py` | Add docstring explaining 24h TTL and deduplication |
| `app/core/query_cache.py` | Add docstring explaining the 24h fallback cache |
| `app/agents/policy/vector_store.py` | Add docstring explaining FAISS IndexFlatIP + L2 norm |
| `tests/evals/judge.py` | Add module-level docstring with architecture overview and usage example |
| `tests/evals/conftest.py` | Add module-level docstring explaining skip logic, opt-in flags, and shared data schemas |

---

## API Reference — Endpoint Inventory

### Products (`/api/v1/products`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/products` | List products with pagination, filtering, category |
| GET | `/api/v1/products/{product_id}` | Get single product |
| GET | `/api/v1/products/categories` | List distinct categories |

### Recommendations (`/api/v1/recommendations`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/recommendations` | AI-powered recommendations (RecommendationAgent) |

### Reviews (`/api/v1/reviews`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/reviews/summarize` | LLM review summarization (ReviewSummarizationAgent) |
| GET | `/api/v1/reviews/{product_id}` | Raw reviews for a product |

### Price (`/price`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/price/compare` | Cross-retailer price comparison (PriceComparisonAgent) |

### Policy (`/policy`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/policy/ask` | FAISS RAG policy Q&A (PolicyAgent) |

### Chat (`/api/v1/chat`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/chat` | Unified intent-routed chat with session memory |
| DELETE | `/api/v1/chat/session/{session_id}` | Clear session history |

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health status |
| GET | `/health/metrics` | Latency P50/P95 per endpoint (rolling 200 samples) |
| GET | `/health/alerts` | Component failure counts (rolling 5-min window) |

---

## Agent Documentation Plan

For each agent, document:
1. **Purpose** — one-sentence description
2. **Intent(s) it handles** — from `IntentType` enum
3. **Input** — `AgentDependencies`, key context fields
4. **Tools** — list from `agents/*/tools.py`
5. **Output schema** — the pydantic `OutputType` class
6. **LLM cache** — TTL, key structure
7. **Error behaviour** — what happens on failure

| Agent | Intent | Key Tools | Output Type |
|-------|--------|-----------|-------------|
| `RecommendationAgent` | `recommendation`, `comparison` | `search_products_by_filters`, `get_product_details`, `get_categories` | `_RecommendationOutput` |
| `ReviewSummarizationAgent` | `review` | `get_reviews_for_product`, `get_product_details` | `_ReviewSummary` |
| `PriceComparisonAgent` | `price` | `get_price_comparison`, `get_price_history` | `_PriceComparisonOutput` |
| `PolicyAgent` | `policy` | `search_policy_chunks` (FAISS) | `_PolicyAnswer` |
| `GeneralResponseAgent` | `general` (fallback) | — (no tools, pure LLM) | `_Answer` |
| `IntentClassifier` | all | — (no tools) | `_IntentResult` |

---

## Eval Framework Documentation Plan (`docs/EVALS.md`)

This is a **new, dedicated document** covering the LLM-as-judge eval system in `tests/evals/`.

### Why evals exist (intro section)
- Unit tests verify the plumbing (routing, DB queries, error handling)
- Eval tests verify the *quality of AI reasoning* — relevance, correctness, helpfulness
- Neither replaces the other; they test different layers

### Architecture diagram
```
User query
    │
    ▼
┌─────────────────────────────────┐
│  Agent (e.g. RecommendationAgent)│  ← real LLM call (gpt-4o-mini)
│  mocked DB (SAMPLE_PRODUCTS)    │
└──────────────┬──────────────────┘
               │ AgentResponse
               ▼
┌──────────────────────┐
│  format_agent_response│  ← converts data dict → readable string
└──────────┬───────────┘
           │ response_text
           ▼
┌──────────────────────┐
│  LLMJudge.evaluate() │  ← real LLM call (gpt-4o-mini as judge)
│  JUDGE_SYSTEM_PROMPT │
└──────────┬───────────┘
           │ EvalScore
           ▼
┌──────────────────────────────────────┐
│  pytest assertions                   │
│  assert score.overall >= min_overall │
└──────────────────────────────────────┘
```

### Core classes to document

**`EvalScore`** (from `tests/evals/judge.py`)
```python
class EvalScore(BaseModel):
    relevance: float          # Does response address the query? (0–1)
    correctness: float        # Is information plausible/accurate? (0–1)
    reasoning_quality: float  # Is reasoning coherent? (0–1)
    helpfulness: float        # Would this help the user? (0–1)
    overall: float            # Holistic quality score (0–1)
    explanation: str          # One-sentence judge reasoning

    @property
    def average(self) -> float: ...  # mean of 4 primary dimensions
```

**`EvalCase`** (from `tests/evals/judge.py`)
```python
@dataclass
class EvalCase:
    name: str           # Human-readable test case name
    query: str          # User query to evaluate
    agent_type: str     # "recommendation" | "review" | "price" | "policy" | "general"
    response_text: str  # Formatted agent response presented to judge
    context: str        # Optional evaluation hint for the judge
    min_overall: float  # Minimum passing threshold
    max_overall: float  # Maximum threshold (for bad-response tests)
```

**`LLMJudge`** (from `tests/evals/judge.py`)
```python
judge = LLMJudge(model_name="gpt-4o-mini")

# Score a single response
score: EvalScore = await judge.evaluate(query, response_text, agent_type, context)

# Score two responses concurrently (good vs bad — for calibration)
good_score, bad_score = await judge.compare(query, good_response, bad_response)

# Run a full suite
results = await judge.run_suite(cases)  # → list[(EvalCase, EvalScore)]
```

### Eval test file index

| File | Tests | Purpose |
|------|-------|---------|
| `tests/evals/judge.py` | — | `LLMJudge`, `EvalScore`, `EvalCase` classes |
| `tests/evals/conftest.py` | — | Skip logic, shared fixtures, `SAMPLE_PRODUCTS/REVIEWS/POLICIES`, `make_mock_db()`, `format_agent_response()` |
| `tests/evals/test_eval_judge.py` | 18 | **Judge calibration** — good responses score ≥ 0.70; bad responses ≤ 0.45; good always ranks above bad for all 5 agent types |
| `tests/evals/test_eval_intent_classifier.py` | 20 | **Intent routing accuracy** — 12 query→intent pairs, entity extraction (price, category, product name), confidence calibration |
| `tests/evals/test_eval_recommendation.py` | 8 | **Recommendation quality** — budget filtering, use-case matching, reasoning quality, comparison mode, empty-result handling |
| `tests/evals/test_eval_review.py` | 7 | **Review summary quality** — sentiment accuracy, pro/con balance, correctness vs. seeded data |
| `tests/evals/test_eval_price.py` | 7 | **Price comparison quality** — competitive assessment, multi-store comparison, value recommendations |
| `tests/evals/test_eval_policy.py` | 10 | **Policy answer accuracy** — return window, restocking fee, shipping costs, warranty exclusions (mocked FAISS) |
| `tests/evals/test_eval_general.py` | 13 | **General agent quality** — on-brand redirects, off-topic handling, conciseness, fallback message |
| `tests/evals/test_eval_orchestrator.py` | 14 | **E2E routing** — all 6 intent types, context enrichment (price hints, category), graceful fallback on agent failure |

**Total eval tests: 97**

### How to run evals
```bash
# Run all eval tests (makes real OpenAI API calls)
RUN_EVALS=1 pytest tests/evals/ -v -m eval

# Run a single eval file
RUN_EVALS=1 pytest tests/evals/test_eval_judge.py -v -s

# Skip evals (default in CI — no opt-in flag)
pytest tests/evals/   # → 97 skipped (no API calls made)
```

### Score thresholds (calibration reference)
| Response quality | Expected `overall` score |
|-----------------|--------------------------|
| Excellent | ≥ 0.85 |
| Good | 0.70 – 0.85 |
| Mediocre | 0.50 – 0.70 |
| Poor | < 0.50 |

Good responses in tests assert `min_overall ≥ 0.65–0.70`.
Bad/off-topic responses assert `max_overall ≤ 0.45`.

### How to add an eval test for a new agent
```python
# tests/evals/test_eval_newagent.py
import pytest
from app.agents.newagent.agent import NewAgent
from app.agents.dependencies import AgentDependencies
from tests.evals.conftest import SAMPLE_PRODUCTS, format_agent_response, make_mock_db

@pytest.mark.asyncio
@pytest.mark.eval
async def test_newagent_quality(judge):
    db = make_mock_db(products=SAMPLE_PRODUCTS)
    deps = AgentDependencies(db=db, settings=get_settings())
    agent = NewAgent()
    result = await agent.process("my query", context={"deps": deps})
    response_text = format_agent_response(result, "new")
    score = await judge.evaluate("my query", response_text, "new")
    assert result.success
    assert score.overall >= 0.65
```

### Shared test data (in `conftest.py`)
```
SAMPLE_PRODUCTS  — 7 products (smartphones, laptops, headphones) with realistic prices/ratings
SAMPLE_REVIEWS   — 5 reviews for PROD001 and PROD006 (mixed positive/neutral/negative)
SAMPLE_POLICIES  — 3 policies (return 30d, shipping 5-7d, warranty 1yr)
```

### CI integration guidance
- Eval tests are **opt-in** — they require `RUN_EVALS=1` + `OPENAI_API_KEY`
- Regular `pytest` runs always skip evals — zero API cost in CI
- Recommend running evals on-demand before major releases or after prompt changes
- Average cost: ~$0.01–0.05 per full eval suite run (97 tests × 2 LLM calls each)

---

## Testing Guide Plan (`docs/TESTING.md`)

### Sections
1. **Test layout** — directory structure, what each folder tests
2. **Running tests** — `pytest`, coverage, eval flag
3. **Unit test patterns**:
   - `make_mock_db()` — mock SQLAlchemy sessions
   - `TestModel` — mock pydantic-ai LLM calls without API cost
   - `AsyncMock` + `patch.object` — mock agent `.run()` directly
   - `autouse` reset fixtures — `reset_X()` for singletons
4. **Eval tests** — brief overview, pointer to `docs/EVALS.md`
5. **Test count tracker** — current 487 tests (390 unit + 97 evals), how to update CLAUDE.md

### Key patterns to document (with code examples)
```python
# Pattern 1: Mock DB
db = make_mock_db(products=SAMPLE_PRODUCTS)
deps = AgentDependencies(db=db, settings=get_settings())

# Pattern 2: Mock LLM (no API cost)
with agent._agent.override(model=TestModel()):
    result = await agent.process(query, context={"deps": deps})

# Pattern 3: Mock async agent run
with patch.object(agent._agent, "run", new_callable=AsyncMock) as m:
    m.return_value = mock_result
    result = await agent.process(query, context={"deps": deps})

# Pattern 4: Singleton reset
@pytest.fixture(autouse=True)
def reset():
    reset_orchestrator(); reset_session_store()
    yield
    reset_orchestrator(); reset_session_store()
```

---

## Deployment Guide Plan

### Sections
1. **Prerequisites** — Python 3.11+, Docker, OpenAI API key, PostgreSQL, Redis
2. **Environment variables** — complete `.env` reference table
3. **Local development** — without Docker
4. **Docker Compose** — full stack startup
5. **Database setup** — Alembic migrations + CSV data load
6. **Production considerations** — scaling, secrets management, HTTPS
7. **Health checks** — monitoring startup

### Environment Variables Reference
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ | — | OpenAI API key for all agents + embeddings |
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string |
| `REDIS_URL` | ❌ | `None` | Redis URL; falls back to TTLCache if absent |
| `OPENAI_MODEL` | ❌ | `gpt-4o-mini` | LLM model for agents |
| `ENVIRONMENT` | ❌ | `development` | `development` or `production` |
| `DEBUG` | ❌ | `False` | Enable debug logging |
| `PORT` | ❌ | `8000` | FastAPI port |

---

## Troubleshooting Guide Plan

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| `ModuleNotFoundError: faiss` | FAISS not installed | `pip install faiss-cpu` |
| `PolicyAgent not registered` | FAISS import failed | Check FAISS install; see logs |
| `OpenAI RateLimitError` | API quota exceeded | Wait or increase quota |
| DB connection refused | PostgreSQL not running | `docker-compose up postgres` |
| Redis connection timeout | Redis not running | Falls back to TTLCache automatically |
| Streamlit blank page | FastAPI not running | Start FastAPI first (`uvicorn app.main:app`) |
| `AgentDependencies not in context` | Endpoint missing `deps` | Check `context["deps"]` injection in router |
| Circuit breaker OPEN | Agent repeated failures | Wait for recovery timeout (30s default) |
| Eval tests not running | `RUN_EVALS` not set | Run with `RUN_EVALS=1 pytest tests/evals/` |
| Eval tests skipped — no key | `OPENAI_API_KEY` missing | Set `export OPENAI_API_KEY=sk-...` |
| Judge scores unexpectedly low | Judge miscalibrated | Run `test_eval_judge.py` calibration tests first |
| Eval test assertion fails | Agent response quality degraded | Check if prompt changed; review `score.explanation` |
| `EvalScore` validation error | Judge returned out-of-range float | Check `JUDGE_SYSTEM_PROMPT` — may need tuning |

---

## Developer Guide Plan — Adding a New Agent

```
Step 1: Create app/agents/newagent/
  ├── __init__.py
  ├── agent.py       # class NewAgent(BaseAgent)
  ├── prompts.py     # SYSTEM_PROMPT constant
  └── tools.py       # @tool functions with RunContext[AgentDependencies]

Step 2: Register in orchestrator.py → build_orchestrator()
  registry["new_intent"] = NewAgent()

Step 3: Add IntentType.NEW_INTENT to app/schemas/chat.py

Step 4: Update IntentClassifier prompt with new intent description

Step 5: Create app/api/v1/newagent.py router + POST endpoint

Step 6: Write unit tests in tests/test_agents/test_new_agent.py
  - TestModel for LLM mocking (no API cost)
  - make_mock_db() for DB mocking
  - autouse reset fixture

Step 7: Write eval test in tests/evals/test_eval_newagent.py
  - Use real agent LLM + mocked DB
  - Judge response with LLMJudge.evaluate()
  - Assert score.overall >= 0.65
  - Add good/bad pair to test_eval_judge.py calibration suite
```

---

## Code Comments Plan (Complex Logic)

| File | What to Document |
|------|-----------------|
| `app/agents/orchestrator/orchestrator.py` | `handle()` flow: classify → enrich → route → circuit breaker → cache fallback |
| `app/agents/orchestrator/circuit_breaker.py` | State machine: CLOSED → OPEN → HALF_OPEN → CLOSED |
| `app/core/cache.py` | Redis→TTLCache fallback pattern |
| `app/core/llm_cache.py` | Cache key construction, 24h TTL, deduplication |
| `app/core/query_cache.py` | Orchestrator fallback before GeneralAgent |
| `app/agents/policy/vector_store.py` | FAISS IndexFlatIP + L2 norm for cosine similarity |
| `app/services/session/session_manager.py` | Session TTL, history appending, turn structure |
| `tests/evals/judge.py` | Module docstring: why LLM-as-judge, scoring dimensions, calibration guidance |
| `tests/evals/conftest.py` | Module docstring: how skip logic works, how to opt-in, shared data schema |

---

## Test Requirements

### New tests to write
| Test File | Tests | What |
|-----------|-------|------|
| `tests/test_core/test_documentation_links.py` | 8 | Verify all docs/*.md files exist, are non-empty, and contain expected section headers (including EVALS.md) |

### Test estimate: ~8 new unit tests + 97 eval tests (already written)

**Test count before (unit):** 390
**Test count after (unit):** ~398

**Eval tests (separate, opt-in):** 97 (in `tests/evals/`)
**Total tests visible to `pytest`:** ~495

---

## Implementation Order

1. **`docs/API_REFERENCE.md`** — most immediately useful, no code changes needed
2. **`docs/AGENTS.md`** — captures all agent design decisions
3. **`docs/TESTING.md`** — unblocks new contributors (with pointer to EVALS.md)
4. **`docs/EVALS.md`** ⭐ — LLM-as-judge eval framework (architecture, file index, run commands, extend guide)
5. **`docs/DEPLOYMENT.md`** — needed for any production use
6. **`docs/DEVELOPER_GUIDE.md`** — how to add agents / extend (includes eval test step)
7. **`docs/DATA_PIPELINE.md`** — data ingestion and FAISS details
8. **`docs/MONITORING.md`** — metrics, alerting, health endpoints
9. **`docs/TROUBLESHOOTING.md`** — common issues + eval-specific failures
10. **Inline code comments** — orchestrator, circuit breaker, caches, FAISS, judge, conftest
11. **README.md update** — link to all new docs, add evals section with run command, update test count to 495
12. **`docs/ARCHITECTURE.md` update** — add eval tests layer to system diagram
13. **`tests/test_core/test_documentation_links.py`** — verify all 9 docs/*.md files exist and have required sections

---

## Dependencies

- Requires all prior stories complete ✅ (SCRUM-8 → SCRUM-62 all done)
- No new backend endpoints
- No DB migrations
- No new Python dependencies
