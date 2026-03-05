# Developer Guide

This guide covers how to extend SmartShop AI — add agents, endpoints, UI components, and eval tests.

---

## Adding a New Agent

### Step 1: Create Agent Directory

```
app/agents/newagent/
├── __init__.py
├── agent.py       # class NewAgent(BaseAgent)
├── prompts.py     # SYSTEM_PROMPT constant
└── tools.py       # @tool functions with RunContext[AgentDependencies]
```

### Step 2: Implement the Agent

```python
# app/agents/newagent/agent.py
from pydantic_ai import Agent
from pydantic_ai.settings import UsageLimits
from app.agents.base import BaseAgent, AgentResponse
from app.agents.dependencies import AgentDependencies
from app.core.llm_cache import get_cached_llm_response, set_cached_llm_response
from .prompts import SYSTEM_PROMPT
from .tools import tool_function

class _OutputSchema(BaseModel):
    answer: str

def _build_agent(model_name: str) -> Agent:
    from pydantic_ai.models.openai import OpenAIModel
    model = OpenAIModel(model_name)
    agent = Agent(
        model=model,
        deps_type=AgentDependencies,
        output_type=_OutputSchema,
        instructions=SYSTEM_PROMPT,
    )
    agent.tool(tool_function)
    return agent

class NewAgent(BaseAgent):
    def __init__(self, model_name: str | None = None):
        from app.core.config import get_settings
        model = model_name or get_settings().OPENAI_MODEL
        super().__init__(name="new-agent")
        self._agent = _build_agent(model)

    async def process(self, query: str, context: dict) -> AgentResponse:
        deps = context.get("deps")
        if not deps:
            return AgentResponse(success=False, data={}, error="Missing dependencies")

        # Check LLM cache
        cached = get_cached_llm_response(self.name, query)
        if cached:
            return cached

        # Run agent
        result = await self._agent.run(
            query, deps=deps,
            usage_limits=UsageLimits(request_limit=15)
        )

        response = AgentResponse(
            success=True,
            data=result.output.model_dump(),
            metadata={"model": self._agent.model.model_name}
        )
        set_cached_llm_response(self.name, query, response)
        return response
```

### Step 3: Define Tools

```python
# app/agents/newagent/tools.py
from pydantic_ai import RunContext
from app.agents.dependencies import AgentDependencies

async def tool_function(ctx: RunContext[AgentDependencies], param: str) -> dict:
    """Tool description for the LLM."""
    db = ctx.deps.db
    # Query database...
    return {"result": "data"}
```

### Step 4: Register in Orchestrator

```python
# app/agents/orchestrator/orchestrator.py → build_orchestrator()
from app.agents.newagent.agent import NewAgent

registry["new_intent"] = NewAgent()
```

### Step 5: Add Intent Type

```python
# app/schemas/chat.py
class IntentType(str, Enum):
    # ... existing intents
    NEW_INTENT = "new_intent"
```

Update the IntentClassifier prompt in `app/agents/orchestrator/intent_classifier.py` to describe the new intent.

### Step 6: Create API Endpoint

```python
# app/api/v1/newagent.py
from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.agents.newagent.agent import NewAgent
from app.agents.dependencies import AgentDependencies

router = APIRouter(prefix="/api/v1/newagent", tags=["newagent"])

@router.post("")
async def handle_query(request: NewRequest, db=Depends(get_db)):
    deps = AgentDependencies.from_db(db)
    agent = NewAgent()
    result = await agent.process(request.query, context={"deps": deps})
    if not result.success:
        raise HTTPException(500, detail=result.error)
    return result.data
```

Register the router in `app/main.py`.

### Step 7: Write Unit Tests

```python
# tests/test_agents/test_new_agent.py
from pydantic_ai.models.test import TestModel

@pytest.fixture(autouse=True)
def reset():
    reset_llm_cache()
    yield
    reset_llm_cache()

@pytest.mark.asyncio
async def test_new_agent_success(db_session, sample_product):
    agent = NewAgent()
    with agent._agent.override(model=TestModel()):
        result = await agent.process("query", context={"deps": deps})
    assert result.success
```

### Step 8: Write Eval Test

```python
# tests/evals/test_eval_newagent.py
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

---

## Adding a New API Endpoint (Without Agent)

1. Create router file in `app/api/v1/`
2. Use `Depends(get_db)` for database access
3. Register router in `app/main.py`
4. Add tests in `tests/test_api/`
5. Document in `docs/API_REFERENCE.md`

---

## Extending the Streamlit UI

UI components live in `app/ui/components/`.

### Adding a Component

1. Create `app/ui/components/new_component.py`
2. Import and use in `app/ui/streamlit_app.py`
3. Use design tokens from `app/ui/design_tokens.py` for consistent styling
4. Add tests in `tests/test_ui/test_new_component.py`

### Design Tokens

```python
from app.ui.design_tokens import COLORS, FONTS, SPACING
```

---

## Working with the Cache

### Adding a New Cache Singleton

Follow the existing pattern:

```python
# app/core/my_cache.py
_cache = None

def get_my_cache():
    global _cache
    if _cache is not None:
        return _cache
    try:
        _cache = RedisCache(prefix="myprefix:", ttl=3600)
    except Exception:
        _cache = TTLCache(max_size=500, ttl=3600)
    return _cache

def reset_my_cache():
    global _cache
    _cache = None
```

Always provide a `reset_*()` function for test isolation.

---

## Project Conventions

- **Error handling:** Use `SmartShopError` hierarchy, never return raw exceptions to users
- **Logging:** Use `logging.getLogger(__name__)`, include request_id where available
- **Testing:** Zero API cost in unit tests — use `TestModel` or `AsyncMock`
- **Caching:** Redis primary → TTLCache fallback, always provide `reset_*()` for tests
- **Agent limits:** `UsageLimits(request_limit=15)` on all specialized agents
- **Database:** SQLAlchemy 2.0 ORM, function-scoped fixtures in tests
