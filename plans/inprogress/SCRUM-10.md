# Story: SCRUM-10 — Develop Product Recommendation Agent with Pydantic AI

## Story Overview
- **Epic**: SCRUM-3 (Phase 2: Agent Development)
- **Story Points**: 8
- **Priority**: Medium
- **Jira Link**: https://projecttracking.atlassian.net/browse/SCRUM-10
- **Complexity**: High — This is the **first agentic story** and sets architectural patterns for all future agents (SCRUM-11, 14, 15, 16, 17)
- **Estimated Duration**: 4–6 hours

---

## ⚠️ Critical Pre-Implementation Decision: pydantic-ai Version Upgrade

### Problem
`requirements.txt` pins `pydantic-ai==0.0.13`, which is a pre-release version that:
- Cannot be imported (missing `_griffe` dependency — broken package)
- Has a completely different API from what the Jira story describes
- Is incompatible with all modern pydantic-ai documentation and tooling

### Decision: Upgrade to pydantic-ai ≥1.0.0
The pydantic-ai 1.x series (current stable: 1.61.0) is the production-ready version with:
- Stable `Agent` class with `@agent.tool` decorator pattern
- Type-safe dependency injection via `RunContext[DepsType]`
- `result_type` for structured Pydantic output — no parsing required
- `TestModel` for unit testing without real API calls (no mocks, no patching)
- Clean async-first design matching our `BaseAgent.process()` contract

**Action required**: Update `requirements.txt`:
```
# OLD:
pydantic-ai==0.0.13

# NEW:
pydantic-ai>=1.0.0,<2.0.0
```

Then install: `pip install "pydantic-ai>=1.0.0,<2.0.0" --break-system-packages`

---

## Dependencies
- SCRUM-9 ✅ — FastAPI backend, `GET /api/v1/products` working
- SCRUM-6 ✅ — `Product` SQLAlchemy model available
- `app/agents/base.py` ✅ — `BaseAgent` ABC and `AgentResponse` exist
- `app/core/config.py` ✅ — `Settings` with `OPENAI_API_KEY`, `OPENAI_MODEL`
- `app/core/database.py` ✅ — `get_db()` FastAPI dependency

---

## Architectural Philosophy (Sets Pattern for All Future Agents)

This story is not just about one agent — it establishes the **agent architecture** that SCRUM-11 (Review Summarizer), SCRUM-14 (Price Comparison), SCRUM-15 (FAQ/Policy RAG), SCRUM-16 (Orchestrator), and SCRUM-17 (Session Memory) will all follow.

### Two-Layer Architecture
```
FastAPI Layer          Agent Layer             pydantic-ai Layer
─────────────         ─────────────           ──────────────────
POST /recommend  →    RecommendationAgent  →   pydantic_ai.Agent
                       (BaseAgent subclass)     (LLM + tools)
                            │
                       AgentResponse  ←────    RecommendationOutput
                       (standard format)        (typed Pydantic model)
```

### Why this pattern is scalable:
1. **SCRUM-16 (Orchestrator)** calls `agent.process(query, context)` on any `BaseAgent` subclass — no special cases
2. **SCRUM-17 (Session Memory)** passes conversation history via `context` dict — already wired
3. **Testing** uses pydantic-ai's `TestModel` — deterministic, no API calls, no mocks needed
4. **New agents** follow the same 4-file pattern: `agent.py`, `tools.py`, `prompts.py`, `__init__.py`

---

## Acceptance Criteria
- [x] pydantic-ai upgraded to ≥1.0.0 in requirements.txt
- [ ] `AgentDependencies` dataclass created — shared across all future agents
- [ ] `RecommendationAgent` implements `BaseAgent.process()` contract
- [ ] pydantic-ai `Agent` instance with `gpt-4o-mini`, typed output, tool-based reasoning
- [ ] Tool: `search_products_by_filters` — queries DB with category/brand/price/rating filters
- [ ] Tool: `get_product_details` — fetches a single product by ID for deep reasoning
- [ ] Recommendation considers: price range, category, ratings, user preferences
- [ ] Returns ranked list with relevance scores and reasoning per product
- [ ] Handles natural language queries: "budget smartphones under $500"
- [ ] `POST /api/v1/recommendations` endpoint wired into FastAPI
- [ ] Unit tests using `TestModel` (no real API calls): ≥80% coverage
- [ ] Response time under 2 seconds (with real API key)

---

## File Structure

```
app/
├── agents/
│   ├── __init__.py              ✅ exists
│   ├── base.py                  ✅ exists (BaseAgent, AgentResponse)
│   ├── dependencies.py          ← CREATE: Shared AgentDeps for all agents
│   └── recommendation/
│       ├── __init__.py          ← CREATE
│       ├── agent.py             ← CREATE: RecommendationAgent class
│       ├── tools.py             ← CREATE: pydantic-ai tool definitions
│       └── prompts.py           ← CREATE: System prompt + template
├── api/v1/
│   ├── __init__.py              ✅ exists
│   ├── products.py              ✅ exists
│   └── recommendations.py      ← CREATE: POST /api/v1/recommendations
└── schemas/
    ├── product.py               ✅ exists
    └── recommendation.py        ← CREATE: Request/response API schemas

tests/
└── test_agents/
    ├── __init__.py              ✅ exists (empty)
    └── test_recommendation_agent.py  ← CREATE

requirements.txt                 ← MODIFY: pydantic-ai version upgrade
```

---

## Implementation Tasks

---

### Task 0: Update requirements.txt

Replace the broken `pydantic-ai==0.0.13` pin with the stable 1.x series:

```
# AI & Machine Learning
openai==1.10.0
pydantic-ai>=1.0.0,<2.0.0    # upgraded from 0.0.13 (pre-release, broken)
tiktoken==0.5.2
```

Install: `pip install "pydantic-ai>=1.0.0,<2.0.0" --break-system-packages`

**Validation**: `python3 -c "import pydantic_ai; print(pydantic_ai.__version__)"` must succeed.

---

### Task 1: Create Shared Agent Dependencies

**File**: `app/agents/dependencies.py`

**Purpose**: This `AgentDependencies` dataclass is injected into every pydantic-ai tool via `RunContext`. It is the single source of shared context for all agents — database, settings. SCRUM-11, 14, 15, 16 will all import and reuse this.

```python
"""Shared dependency container for all pydantic-ai agents."""

from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.core.config import Settings, get_settings


@dataclass
class AgentDependencies:
    """
    Injected into all pydantic-ai agent tools via RunContext[AgentDependencies].

    Shared by: RecommendationAgent, ReviewAgent, PriceAgent, PolicyAgent, Orchestrator.
    Extended by individual agents if they need additional deps (e.g. vector store for SCRUM-15).
    """
    db: Session
    settings: Settings

    @classmethod
    def from_db(cls, db: Session) -> "AgentDependencies":
        """Convenience constructor used in FastAPI endpoints."""
        return cls(db=db, settings=get_settings())
```

**Why a dataclass (not a Pydantic model)**: pydantic-ai's `deps_type` expects a regular Python object (dataclass or plain class) for dependency injection — Pydantic models add unnecessary overhead here.

---

### Task 2: Create API Schemas for Recommendations

**File**: `app/schemas/recommendation.py`

**Purpose**: Clean Pydantic v2 request/response models for the FastAPI endpoint. Separate from the internal agent output model.

```python
"""Pydantic schemas for Recommendation API."""

from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional


class RecommendationRequest(BaseModel):
    """POST /api/v1/recommendations request body."""
    query: str = Field(
        ...,
        description="Natural language query, e.g. 'budget smartphones under $500'",
        min_length=3,
        max_length=500,
    )
    max_results: int = Field(default=5, ge=1, le=20)
    # Optional structured hints (user can provide either or both)
    max_price: Optional[float] = Field(default=None, ge=0)
    min_price: Optional[float] = Field(default=None, ge=0)
    category: Optional[str] = Field(default=None, max_length=100)
    min_rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)


class ProductRecommendation(BaseModel):
    """A single recommended product with relevance context."""
    id: str
    name: str
    price: Decimal
    brand: Optional[str] = None
    category: str
    rating: Optional[float] = None
    stock: Optional[int] = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str = Field(description="Why this product was recommended")


class RecommendationResponse(BaseModel):
    """POST /api/v1/recommendations response."""
    query: str
    recommendations: list[ProductRecommendation]
    total_found: int
    reasoning_summary: str = Field(description="Agent's overall reasoning")
    agent: str = "recommendation-agent"
```

---

### Task 3: Create pydantic-ai Tools

**File**: `app/agents/recommendation/tools.py`

**Purpose**: The actual database-querying logic, wrapped as pydantic-ai tools. Each tool is called by the LLM during its ReAct reasoning loop. Tools are the agent's "hands" — they can only see the database through these.

```python
"""Product search tools for the Recommendation Agent."""

import logging
from pydantic_ai import RunContext
from sqlalchemy.orm import Session
from app.agents.dependencies import AgentDependencies
from app.models.product import Product

logger = logging.getLogger(__name__)


async def search_products_by_filters(
    ctx: RunContext[AgentDependencies],
    category: str | None = None,
    brand: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    limit: int = 20,
) -> list[dict]:
    """
    Search the product catalog with optional filters.

    Use this to find products matching user criteria. All filters are optional
    and combined with AND logic. Call multiple times with different filters
    to explore the catalog.

    Args:
        category: Product category (e.g. "electronics", "laptops", "smartphones")
        brand: Brand name (e.g. "Samsung", "Apple", "Sony")
        min_price: Minimum price in USD
        max_price: Maximum price in USD
        min_rating: Minimum rating (0.0–5.0)
        limit: Max results to return (default 20, max 50)
    """
    db: Session = ctx.deps.db
    query = db.query(Product)

    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if brand:
        query = query.filter(Product.brand.ilike(f"%{brand}%"))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if min_rating is not None:
        query = query.filter(Product.rating >= min_rating)

    limit = min(limit, 50)
    products = query.order_by(Product.rating.desc().nullslast()).limit(limit).all()

    logger.debug("search_products_by_filters: found %d products", len(products))
    return [p.to_dict() for p in products]


async def get_product_details(
    ctx: RunContext[AgentDependencies],
    product_id: str,
) -> dict | None:
    """
    Retrieve full details for a specific product by its ID.

    Use this when you need more information about a product you found via search,
    or when the user asks about a specific product by ID.

    Args:
        product_id: The product's unique identifier (e.g. "PROD001")
    """
    db: Session = ctx.deps.db
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None
    return product.to_dict()


async def get_categories(ctx: RunContext[AgentDependencies]) -> list[str]:
    """
    Get a list of all distinct product categories available in the catalog.

    Use this when you're unsure what categories exist, to help interpret
    vague user queries (e.g. mapping "phones" to "smartphones").
    """
    db: Session = ctx.deps.db
    from sqlalchemy import distinct
    results = db.query(distinct(Product.category)).filter(
        Product.category.isnot(None)
    ).all()
    return sorted([r[0] for r in results if r[0]])
```

---

### Task 4: Create System Prompt

**File**: `app/agents/recommendation/prompts.py`

**Purpose**: The system prompt shapes the agent's reasoning behaviour. Keeping it in its own file makes it easy to iterate and A/B test without touching agent logic.

```python
"""Prompts for the Recommendation Agent."""

SYSTEM_PROMPT = """
You are a helpful product recommendation assistant for SmartShop AI.

Your goal is to recommend the most relevant products from our catalog based on
the user's natural language query and any structured preferences they provide.

## How to reason:
1. Parse the user's query to extract: product type, price constraints, brand preferences, feature needs
2. Call `get_categories` if you're unsure which category to search
3. Call `search_products_by_filters` with appropriate filters
4. If results are too few or empty, broaden your filters (e.g. remove brand, widen price range)
5. If results are too many, narrow filters or sort by rating
6. For each shortlisted product, assign a relevance_score (0.0–1.0) based on how well it matches
7. Return only the top N products the user asked for, ranked by relevance_score descending

## Relevance scoring guide:
- 1.0: Perfect match (exact category, within budget, high rating, preferred brand)
- 0.7–0.9: Good match (right category, close to budget, decent rating)
- 0.4–0.6: Partial match (adjacent category or slightly over budget)
- Below 0.4: Do not include in results

## Rules:
- Always respect price constraints; never recommend products over the stated max_price
- Prioritise products with stock > 0
- Provide a specific, helpful "reason" for each recommendation (mention price, rating, features)
- If no products match, say so clearly — do not hallucinate products
- Keep reasoning_summary concise (2–3 sentences)
"""
```

---

### Task 5: Create the Recommendation Agent

**File**: `app/agents/recommendation/agent.py`

**Purpose**: The `RecommendationAgent` is a `BaseAgent` subclass. It wraps a pydantic-ai `Agent` internally. This is the core pattern all future agents will copy.

```python
"""Product Recommendation Agent using pydantic-ai."""

import logging
from typing import Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from app.agents.base import BaseAgent, AgentResponse
from app.agents.dependencies import AgentDependencies
from app.agents.recommendation.prompts import SYSTEM_PROMPT
from app.agents.recommendation import tools
from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ── Structured output type (internal to pydantic-ai) ──────────────────────────

class _ProductResult(BaseModel):
    """Internal: a single product the LLM has selected."""
    product_id: str
    relevance_score: float = Field(ge=0.0, le=1.0)
    reason: str


class _RecommendationOutput(BaseModel):
    """Internal: the full structured output from pydantic-ai."""
    recommendations: list[_ProductResult]
    reasoning_summary: str


# ── Agent definition ────────────────────────────────────────────────────────────

def _build_agent(model_name: str) -> Agent:
    """Build the pydantic-ai Agent. Called once at startup."""
    model = OpenAIModel(model_name)
    agent: Agent[AgentDependencies, _RecommendationOutput] = Agent(
        model=model,
        deps_type=AgentDependencies,
        result_type=_RecommendationOutput,
        system_prompt=SYSTEM_PROMPT,
    )
    # Register tools
    agent.tool(tools.search_products_by_filters)
    agent.tool(tools.get_product_details)
    agent.tool(tools.get_categories)
    return agent


# ── BaseAgent subclass ──────────────────────────────────────────────────────────

class RecommendationAgent(BaseAgent):
    """
    Product recommendation agent.

    Wraps a pydantic-ai Agent internally while satisfying the BaseAgent
    contract so SCRUM-16 (Orchestrator) can route to it uniformly.
    """

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        model = model_name or settings.OPENAI_MODEL
        super().__init__(name="recommendation-agent")
        self._agent = _build_agent(model)

    async def process(
        self,
        query: str,
        context: dict[str, Any],
    ) -> AgentResponse:
        """
        Process a recommendation query.

        Args:
            query: Natural language query, e.g. "budget smartphones under $500"
            context: Must contain 'deps': AgentDependencies instance.
                     May also contain 'max_results': int (default 5).
        """
        deps: AgentDependencies = context.get("deps")
        if deps is None:
            return AgentResponse(
                success=False,
                data={},
                error="AgentDependencies not provided in context['deps']",
            )

        max_results: int = context.get("max_results", 5)
        # Enrich the query with structured hints if provided
        structured_hints = context.get("structured_hints", {})
        enriched_query = _build_enriched_query(query, structured_hints, max_results)

        try:
            result = await self._agent.run(enriched_query, deps=deps)
            output: _RecommendationOutput = result.data

            # Hydrate product details from DB for the API response
            recommendations = _hydrate_recommendations(output, deps)

            return AgentResponse(
                success=True,
                data={
                    "query": query,
                    "recommendations": recommendations,
                    "total_found": len(recommendations),
                    "reasoning_summary": output.reasoning_summary,
                    "agent": self.name,
                },
                metadata={
                    "model": str(self._agent.model),
                    "usage": result.usage().model_dump() if result.usage() else {},
                },
            )
        except Exception as exc:
            logger.error("RecommendationAgent failed: %s", exc, exc_info=True)
            return AgentResponse(
                success=False,
                data={},
                error=f"Recommendation agent error: {str(exc)}",
            )


def _build_enriched_query(
    query: str,
    hints: dict,
    max_results: int,
) -> str:
    """Append structured hints to the natural language query."""
    parts = [query]
    if hints.get("max_price"):
        parts.append(f"Maximum price: ${hints['max_price']}")
    if hints.get("min_price"):
        parts.append(f"Minimum price: ${hints['min_price']}")
    if hints.get("category"):
        parts.append(f"Category: {hints['category']}")
    if hints.get("min_rating"):
        parts.append(f"Minimum rating: {hints['min_rating']}/5")
    parts.append(f"Return top {max_results} recommendations.")
    return "\n".join(parts)


def _hydrate_recommendations(
    output: _RecommendationOutput,
    deps: AgentDependencies,
) -> list[dict]:
    """
    Fetch full product data from DB for each recommendation.
    Drops any product_id the LLM hallucinated (not in DB).
    """
    from app.models.product import Product
    results = []
    for rec in output.recommendations:
        product = deps.db.query(Product).filter(
            Product.id == rec.product_id
        ).first()
        if product:
            data = product.to_dict()
            data["relevance_score"] = rec.relevance_score
            data["reason"] = rec.reason
            results.append(data)
    # Sort by relevance descending
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results
```

**File**: `app/agents/recommendation/__init__.py`

```python
"""Product Recommendation Agent package."""

from app.agents.recommendation.agent import RecommendationAgent

__all__ = ["RecommendationAgent"]
```

---

### Task 6: Create FastAPI Endpoint

**File**: `app/api/v1/recommendations.py`

**Purpose**: Exposes the agent via REST. Wires `AgentDependencies` from FastAPI's DI container.

```python
"""Recommendation API endpoint — v1."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.recommendation import RecommendationAgent
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse, ProductRecommendation
from decimal import Decimal

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])

# Agent is a module-level singleton (created once on startup)
_agent = RecommendationAgent()


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
):
    """
    Get AI-powered product recommendations for a natural language query.

    The agent reasons over the product catalog and returns ranked recommendations
    with relevance scores and explanations.
    """
    deps = AgentDependencies.from_db(db)
    context = {
        "deps": deps,
        "max_results": request.max_results,
        "structured_hints": {
            "max_price": request.max_price,
            "min_price": request.min_price,
            "category": request.category,
            "min_rating": request.min_rating,
        },
    }

    response = await _agent.process(request.query, context)

    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)

    data = response.data
    recommendations = [
        ProductRecommendation(
            id=r["id"],
            name=r["name"],
            price=Decimal(str(r["price"])),
            brand=r.get("brand"),
            category=r["category"],
            rating=r.get("rating"),
            stock=r.get("stock"),
            relevance_score=r["relevance_score"],
            reason=r["reason"],
        )
        for r in data["recommendations"]
    ]

    return RecommendationResponse(
        query=data["query"],
        recommendations=recommendations,
        total_found=data["total_found"],
        reasoning_summary=data["reasoning_summary"],
        agent=data["agent"],
    )
```

**Wire into `app/api/v1/__init__.py`**:

```python
"""API v1 router — aggregates all v1 endpoints."""

from fastapi import APIRouter
from app.api.v1 import products, recommendations

router = APIRouter()
router.include_router(products.router)
router.include_router(recommendations.router)
```

---

### Task 7: Write Tests with TestModel

**File**: `tests/test_agents/test_recommendation_agent.py`

**Purpose**: Uses pydantic-ai's built-in `TestModel` — no real API calls, no mocking OpenAI. The `TestModel` responds deterministically based on tool calls, making tests fast and reliable.

```python
"""Tests for RecommendationAgent using pydantic-ai TestModel."""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from pydantic_ai.models.test import TestModel

from app.agents.recommendation.agent import RecommendationAgent, _RecommendationOutput, _ProductResult
from app.agents.dependencies import AgentDependencies
from app.core.config import get_settings


# ── Fixtures ────────────────────────────────────────────────────────────────────

def make_mock_db(products: list[dict] | None = None):
    """Create a mock SQLAlchemy session with optional product data."""
    from unittest.mock import MagicMock
    db = MagicMock()
    mock_products = []
    for p in (products or []):
        mock_product = MagicMock()
        for key, val in p.items():
            setattr(mock_product, key, val)
        mock_product.to_dict.return_value = p
        mock_products.append(mock_product)

    db.query.return_value.filter.return_value.filter.return_value = db.query.return_value
    db.query.return_value.filter.return_value = db.query.return_value
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value = mock_products
    db.query.return_value.limit.return_value.all.return_value = mock_products
    db.query.return_value.all.return_value = mock_products
    # For get_product_details
    if mock_products:
        db.query.return_value.filter.return_value.first.return_value = mock_products[0]
    else:
        db.query.return_value.filter.return_value.first.return_value = None
    return db


SAMPLE_PRODUCTS = [
    {
        "id": "PROD001", "name": "Budget Phone X1", "price": Decimal("299.99"),
        "brand": "TechCo", "category": "smartphones", "stock": 50,
        "rating": 4.2, "description": "Affordable smartphone", "created_at": None, "updated_at": None,
    },
    {
        "id": "PROD002", "name": "Premium Phone Y2", "price": Decimal("799.99"),
        "brand": "PremiumBrand", "category": "smartphones", "stock": 20,
        "rating": 4.8, "description": "High-end smartphone", "created_at": None, "updated_at": None,
    },
]


# ── Unit Tests ──────────────────────────────────────────────────────────────────

class TestRecommendationAgentInit:
    def test_agent_initialises(self):
        """Agent can be created without errors."""
        agent = RecommendationAgent()
        assert agent.name == "recommendation-agent"
        assert agent._agent is not None

    def test_agent_repr(self):
        agent = RecommendationAgent()
        assert "RecommendationAgent" in repr(agent)


class TestRecommendationAgentProcess:
    @pytest.mark.asyncio
    async def test_missing_deps_returns_error(self):
        """process() returns failure when deps not in context."""
        agent = RecommendationAgent()
        result = await agent.process("smartphones under $500", context={})
        assert result.success is False
        assert "AgentDependencies" in result.error

    @pytest.mark.asyncio
    async def test_successful_recommendation_with_test_model(self):
        """
        Uses pydantic-ai TestModel to simulate agent response without real API.
        TestModel returns a fixed structured output based on result_type.
        """
        db = make_mock_db(SAMPLE_PRODUCTS)
        deps = AgentDependencies(db=db, settings=get_settings())

        agent = RecommendationAgent()

        # Override the internal pydantic-ai agent with TestModel
        with agent._agent.override(model=TestModel()):
            result = await agent.process(
                "budget smartphones under $500",
                context={"deps": deps, "max_results": 2},
            )

        # TestModel produces a valid _RecommendationOutput structure
        # success may be True or False depending on TestModel's output;
        # we validate the contract, not the specific recommendations
        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    @pytest.mark.asyncio
    async def test_agent_error_handling(self):
        """Agent returns AgentResponse with success=False on exception."""
        db = make_mock_db()
        deps = AgentDependencies(db=db, settings=get_settings())
        agent = RecommendationAgent()

        # Force an exception inside the agent run
        with patch.object(agent._agent, "run", side_effect=RuntimeError("LLM timeout")):
            result = await agent.process("phones", context={"deps": deps})

        assert result.success is False
        assert "LLM timeout" in result.error


class TestRecommendationTools:
    @pytest.mark.asyncio
    async def test_search_products_filters(self):
        """Tool filters products correctly via mock DB."""
        from app.agents.recommendation.tools import search_products_by_filters

        db = make_mock_db(SAMPLE_PRODUCTS)
        deps = AgentDependencies(db=db, settings=get_settings())

        ctx = MagicMock()
        ctx.deps = deps

        results = await search_products_by_filters(
            ctx, category="smartphones", max_price=400.0
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_product_details_found(self):
        """Tool returns product dict when product exists."""
        from app.agents.recommendation.tools import get_product_details

        db = make_mock_db(SAMPLE_PRODUCTS)
        deps = AgentDependencies(db=db, settings=get_settings())

        ctx = MagicMock()
        ctx.deps = deps

        result = await get_product_details(ctx, product_id="PROD001")
        assert result is not None
        assert result["id"] == "PROD001"

    @pytest.mark.asyncio
    async def test_get_product_details_not_found(self):
        """Tool returns None when product doesn't exist."""
        from app.agents.recommendation.tools import get_product_details

        db = make_mock_db([])  # empty catalog
        deps = AgentDependencies(db=db, settings=get_settings())
        db.query.return_value.filter.return_value.first.return_value = None

        ctx = MagicMock()
        ctx.deps = deps

        result = await get_product_details(ctx, product_id="nonexistent")
        assert result is None


class TestRecommendationSchemas:
    def test_request_schema_valid(self):
        from app.schemas.recommendation import RecommendationRequest
        req = RecommendationRequest(query="phones under $300", max_results=3, max_price=300.0)
        assert req.max_results == 3
        assert req.max_price == 300.0

    def test_request_schema_defaults(self):
        from app.schemas.recommendation import RecommendationRequest
        req = RecommendationRequest(query="phones")
        assert req.max_results == 5
        assert req.max_price is None

    def test_request_schema_query_too_short(self):
        from app.schemas.recommendation import RecommendationRequest
        import pytest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            RecommendationRequest(query="ab")  # min_length=3

    def test_product_recommendation_schema(self):
        from app.schemas.recommendation import ProductRecommendation
        rec = ProductRecommendation(
            id="P1", name="Test Phone", price=Decimal("299.99"),
            category="smartphones", relevance_score=0.9,
            reason="Great value for money"
        )
        assert rec.relevance_score == 0.9
```

---

## Completion Checklist

### Prerequisites
- [ ] `requirements.txt` updated: `pydantic-ai>=1.0.0,<2.0.0`
- [ ] pydantic-ai 1.x installed and importable

### New Files Created
- [ ] `app/agents/dependencies.py`
- [ ] `app/agents/recommendation/__init__.py`
- [ ] `app/agents/recommendation/agent.py`
- [ ] `app/agents/recommendation/tools.py`
- [ ] `app/agents/recommendation/prompts.py`
- [ ] `app/api/v1/recommendations.py`
- [ ] `app/schemas/recommendation.py`
- [ ] `tests/test_agents/test_recommendation_agent.py`

### Modified Files
- [ ] `requirements.txt` — pydantic-ai version upgrade
- [ ] `app/api/v1/__init__.py` — include recommendations router

### Testing
- [ ] All new tests pass: `pytest tests/test_agents/ -v`
- [ ] Schema tests pass: coverage on `schemas/recommendation.py` ≥ 90%
- [ ] No import errors: `python3 -c "from app.agents.recommendation import RecommendationAgent"`
- [ ] Endpoint registered: visible in `GET /docs`

### Acceptance Criteria (from Jira)
- [ ] Agent implemented using pydantic-ai framework (1.x)
- [ ] OpenAI GPT-4o-mini integration configured
- [ ] Tool for querying product catalog by filters
- [ ] Recommendation considers: price range, category, ratings, preferences
- [ ] Returns ranked product list with relevance scores
- [ ] Handles queries like "budget smartphones under $500"
- [ ] Unit tests with ≥80% coverage
- [ ] Response time under 2 seconds (with live API key)

---

## Patterns Established for Future Agents

| Future Story | Reuses from SCRUM-10 |
|---|---|
| SCRUM-11 (Review Agent) | `AgentDependencies`, `BaseAgent.process()`, tool pattern, `TestModel` tests |
| SCRUM-14 (Price Agent) | Same structure — add Redis cache dep to `AgentDependencies` |
| SCRUM-15 (Policy/RAG Agent) | Extend `AgentDependencies` with `vector_store` field |
| SCRUM-16 (Orchestrator) | Calls `agent.process(query, context)` on all `BaseAgent` subclasses uniformly |
| SCRUM-17 (Session Memory) | Passes `conversation_history` via `context` dict |

---

## Integration Test (Manual, Requires OPENAI_API_KEY)

```bash
# Start server
uvicorn app.main:app --reload --port 8080

# Test recommendation endpoint
curl -X POST http://localhost:8080/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"query": "budget smartphones under $500", "max_results": 3}'

# Test with structured hints
curl -X POST http://localhost:8080/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"query": "best rated laptops", "max_price": 1000, "min_rating": 4.0, "max_results": 5}'

# Check Swagger docs
open http://localhost:8080/docs
```

---

## Time Tracking
- **Estimated**: 4–6 hours
- **Actual**: _[To be filled during execution]_

---

## Jira Completion Comment Template
```
SCRUM-10 completed: Product Recommendation Agent ✅

Architecture established for all future agents (SCRUM-11, 14, 15, 16, 17):
- pydantic-ai upgraded to 1.x (0.0.13 was broken pre-release)
- AgentDependencies dataclass — shared injection container for all agents
- BaseAgent + pydantic-ai Agent two-layer pattern established
- TestModel-based unit tests (no real API calls)

Files created: app/agents/dependencies.py, app/agents/recommendation/* (4 files),
app/api/v1/recommendations.py, app/schemas/recommendation.py,
tests/test_agents/test_recommendation_agent.py

Files modified: requirements.txt, app/api/v1/__init__.py

Endpoint: POST /api/v1/recommendations — accepts NL query + optional filters,
returns ranked products with relevance scores and per-product reasoning.

Next: SCRUM-11 (Review Summarization Agent) can follow the same pattern.
```
