# Testing Guide

SmartShop AI uses **pytest** with ~511 unit/integration tests and ~97 opt-in LLM evaluation tests.

---

## Directory Structure

```
tests/
├── conftest.py                # Shared DB fixtures (SQLite in-memory)
├── evals/                     # LLM-as-judge eval tests (see docs/EVALS.md)
│   ├── judge.py               # LLMJudge, EvalScore, EvalCase
│   ├── conftest.py            # Skip logic, sample data, mock DB
│   └── test_eval_*.py         # 8 eval test files (97 tests)
├── test_agents/               # Agent unit tests (6 files)
├── test_api/                  # Endpoint tests (7 files)
├── test_core/                 # Core module tests (5 files)
├── test_integration/          # E2E tests (2 files)
├── test_middleware/            # Middleware tests (2 files)
├── test_models/               # SQLAlchemy model tests (4 files)
├── test_schemas/              # Pydantic schema tests (1 file)
├── test_scripts/              # Data loading script tests (3 files)
├── test_services/             # Service tests (6 files)
└── test_ui/                   # Streamlit component tests (7 files)
```

---

## Running Tests

```bash
# Run all unit/integration tests (no API cost)
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_agents/test_recommendation_agent.py -v

# Run tests matching a keyword
pytest -k "test_price" -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run eval tests (makes real OpenAI API calls)
RUN_EVALS=1 pytest tests/evals/ -v -m eval
```

---

## Database Fixtures

**File:** `tests/conftest.py`

All tests get a fresh in-memory SQLite database per test function.

```python
@pytest.fixture
def db_engine():
    """In-memory SQLite with foreign key pragma."""
    engine = create_engine("sqlite:///:memory:")
    # Enable FK support for SQLite
    Base.metadata.create_all(engine)
    yield engine

@pytest.fixture
def db_session(db_engine):
    """Fresh session per test with auto-rollback."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def sample_product(db_session):
    """Pre-populated Product record."""
    product = Product(id="TEST001", name="Test Phone", price=499.99, category="smartphone")
    db_session.add(product)
    db_session.commit()
    return product
```

---

## Key Testing Patterns

### Pattern 1: Mock Database

Use `make_mock_db()` to create a mock SQLAlchemy session that returns predefined data without a real database.

```python
from tests.evals.conftest import SAMPLE_PRODUCTS, make_mock_db

db = make_mock_db(products=SAMPLE_PRODUCTS)
deps = AgentDependencies(db=db, settings=get_settings())
```

### Pattern 2: TestModel (Mock LLM — No API Cost)

pydantic-ai provides `TestModel` to mock LLM calls in unit tests.

```python
from pydantic_ai.models.test import TestModel

with agent._agent.override(model=TestModel()):
    result = await agent.process(query, context={"deps": deps})
```

### Pattern 3: AsyncMock for Agent `.run()`

Mock the pydantic-ai agent's `.run()` method directly.

```python
from unittest.mock import AsyncMock, patch

with patch.object(agent._agent, "run", new_callable=AsyncMock) as mock_run:
    mock_run.return_value = mock_result
    result = await agent.process(query, context={"deps": deps})
```

**Important:** Mock side effects must accept `**kwargs` for compatibility with `usage_limits`:

```python
async def side_effect(prompt, *, deps=None, **kwargs):
    return mock_result

mock_run.side_effect = side_effect
```

### Pattern 4: Singleton Reset Fixtures

Module-level singletons (caches, orchestrator, session store) must be reset between tests to prevent state leakage.

```python
@pytest.fixture(autouse=True)
def reset_singletons():
    reset_orchestrator()
    reset_session_manager()
    reset_price_cache()
    reset_llm_cache()
    yield
    reset_orchestrator()
    reset_session_manager()
    reset_price_cache()
    reset_llm_cache()
```

### Pattern 5: API Endpoint Testing

Use FastAPI's `TestClient` with dependency overrides.

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_list_products(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    assert "items" in response.json()
```

---

## Test Coverage by Area

| Area | Files | What's Tested |
|------|-------|---------------|
| Agents | 10 | Intent classification, agent responses, error paths, caching, AI routing, SQL optimizations, error handling, base agent, query utils |
| API | 7 | Endpoint contracts, status codes, validation, 404s, 503 error boundaries |
| Core | 6 | DB singletons, LLM cache, metrics, query cache, alerting, cache factory, logging |
| Integration | 2 | Full recommendation + review E2E flows |
| Middleware | 2 | Error handler mapping, request ID injection, DB error handling |
| Models | 4 | Product/Review/Policy serialization, constraints |
| Schemas | 1 | Ingestion schema validation |
| Scripts | 3 | Data loading, image seeding, verification |
| Services | 6 | Pricing, session management, ingestion, quality monitoring |
| UI | 7 | Product card, review panel, floating chat components |

---

## Eval Tests

LLM-as-judge evaluation tests live in `tests/evals/` and verify **AI response quality** (not just plumbing). They make real OpenAI API calls and are opt-in.

See **[docs/EVALS.md](EVALS.md)** for full documentation.

```bash
# Run evals (requires OPENAI_API_KEY + RUN_EVALS=1)
RUN_EVALS=1 pytest tests/evals/ -v -m eval
```

---

## Test Count Tracker

| After Story | Unit Tests |
|-------------|-----------|
| SCRUM-14 | 222 |
| SCRUM-62 | 390 |
| SCRUM-63 | 444 |
| SCRUM-65 | 460 |
| SCRUM-66 | 474 |
| SCRUM-67 | 486 |
| SCRUM-68 | 500 |
| SCRUM-69 | 511 |

Total visible to `pytest`: ~511 unit + 97 eval = ~608 tests.

---

## Adding Tests for a New Feature

1. Create test file in the appropriate `tests/test_*` directory
2. Use `db_session` fixture for DB access
3. Use `TestModel` or `AsyncMock` for LLM calls (zero API cost)
4. Add `autouse` reset fixture for any singletons used
5. Follow existing naming: `test_<feature>_<scenario>`
6. For agent quality testing, add eval tests in `tests/evals/` (see [EVALS.md](EVALS.md))
