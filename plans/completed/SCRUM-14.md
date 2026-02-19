# SCRUM-14: Implement Price Comparison Agent with Multi-Source Pricing

## Story
**As a shopper**, I want to compare prices across retailers so that I can find the best deal on products.

## Dependencies
- `app/agents/base.py` — `BaseAgent`, `AgentResponse`
- `app/agents/dependencies.py` — `AgentDependencies`
- `app/agents/recommendation/tools.py` — `search_products_by_filters()`, `get_product_details()` (reuse pattern)
- `app/models/product.py` — `Product` model (id, name, price, brand, category, stock, rating)
- `app/core/cache.py` — `TTLCache`, `RedisCache`, `get_review_cache()` pattern (reuse for price cache)
- `app/core/config.py` — `Settings.OPENAI_MODEL`, `REDIS_URL`, `CACHE_TTL_SECONDS`
- `app/main.py` — register new price router
- `app/ui/streamlit_app.py` — replace "Coming in SCRUM-14" stub on Pricing Insights page
- `app/ui/api_client.py` — add `compare_prices()` function
- `tests/conftest.py` — existing `db_session`, `sample_product` fixtures
- **No new package dependencies** — uses existing pydantic-ai, openai, sqlalchemy, redis

## Complexity Estimate
**Medium** — New agent + mock price service + caching + API endpoint + Streamlit page wiring

---

## Acceptance Criteria
- [ ] Agent compares prices across multiple sources (DB catalog + mock competitor prices for MVP)
- [ ] Queries product catalog and pricing APIs
- [ ] Returns side-by-side comparison table
- [ ] Highlights best deal with discount percentages
- [ ] Handles queries like "Compare Samsung S24 and Google Pixel 8"
- [ ] Includes feature comparison (specs, ratings)
- [ ] Fallback to cached prices if API unavailable
- [ ] Response time under 3 seconds

---

## Technical Approach

### Architecture Overview
```
User Query: "Compare Samsung S24 and Google Pixel 8"
    │
    ▼
POST /api/v1/price/compare
    │
    ▼
PriceComparisonAgent.process(query, context)
    │
    ├──► Tool: search_products_by_name(name) × N products
    │        → DB lookup for each product
    │
    ├──► Tool: get_competitor_prices(product_id)
    │        → PricingService (mock: ±15% variants for Amazon/BestBuy/Walmart)
    │        → check PriceCache first (1hr TTL), fetch + cache on miss
    │
    └──► pydantic-ai Agent (gpt-4o-mini)
             Input:  query + all product data + competitor prices
             Output: _ComparisonOutput
                 products: list[_ProductComparison]
                     - product_id, name, our_price, competitor_prices
                     - best_price, best_source, savings_pct
                     - key_specs: {screen, camera, battery, ...}
                 best_deal: str  (product name)
                 recommendation: str  (summary text)
             │
             ▼
    PriceCompareResponse  (structured JSON)
```

### Mock Competitor Pricing (MVP Strategy)
Real external pricing APIs require API keys and introduce latency. For MVP:
- `MockPricingService` generates deterministic competitor prices from `product_id` seed
- Sources: "Amazon", "BestBuy", "Walmart" with ±5–20% price variations
- Variations are seed-deterministic (same product → same mock prices every time)
- Architecture: `PricingService` ABC → `MockPricingService` / future `LivePricingService`
- Cache key: `price:{product_id}:{source}` with 1-hour TTL

### Cache Design
Reuse the `TTLCache`/`RedisCache` dual-backend pattern from `app/core/cache.py`:
- Module-level singleton `get_price_cache()` (same pattern as `get_review_cache()`)
- Key: `f"price:{product_id}"` → stores dict of `{source: price}`
- TTL: 3600 seconds (1 hour, same as `CACHE_TTL_SECONDS`)
- Staleness indicator: `cached_at` timestamp stored alongside prices

---

## File Structure

### New Files (8)
```
app/
  agents/
    price/
      __init__.py                    # Package init
      agent.py                       # PriceComparisonAgent(BaseAgent)
      prompts.py                     # SYSTEM_PROMPT for comparison
      tools.py                       # search_products_by_name, get_competitor_prices
  services/
    pricing/
      __init__.py                    # Package init
      base.py                        # PricingService ABC
      mock_pricing.py                # MockPricingService (deterministic mock)
      price_cache.py                 # get_price_cache() singleton
  api/
    v1/
      price.py                       # POST /api/v1/price/compare
  schemas/
    price.py                         # PriceCompareRequest, PriceCompareResponse

tests/
  test_agents/
    test_price_agent.py              # 6 unit tests (mock agent.run)
  test_api/
    test_price.py                    # 7 TestClient integration tests
```

### Modified Files (3)
```
app/main.py                          # Include price router
app/ui/api_client.py                 # Add compare_prices() function
app/ui/streamlit_app.py              # Replace "Coming in SCRUM-14" with real Pricing Insights page
```

---

## Task Breakdown

### Task 1 — Pricing Service (`app/services/pricing/`)

#### `app/services/pricing/base.py`
```python
"""Abstract base class for pricing services."""

from abc import ABC, abstractmethod


class PricingService(ABC):
    """Interface for fetching competitor prices."""

    SOURCES: list[str] = []

    @abstractmethod
    def get_prices(self, product_id: str, base_price: float) -> dict[str, float]:
        """
        Return competitor prices for a product.

        Args:
            product_id: Product identifier
            base_price: Our catalog price (used as reference for mock variants)

        Returns:
            Dict mapping source name → price, e.g. {"Amazon": 749.99, "BestBuy": 799.00}
        """
        ...
```

#### `app/services/pricing/mock_pricing.py`
```python
"""Mock pricing service — deterministic competitor prices from product_id seed."""

import hashlib
from app.services.pricing.base import PricingService

# Price variation ranges per source (as fraction of base price)
_SOURCE_VARIATIONS = {
    "Amazon":  (-0.08, -0.03),   # typically 3-8% cheaper
    "BestBuy": (-0.02,  0.05),   # near parity to +5%
    "Walmart": (-0.12, -0.05),   # typically 5-12% cheaper
}


class MockPricingService(PricingService):
    """
    Generates deterministic mock competitor prices.

    Uses a hash of product_id to produce stable, repeatable price variants.
    Replace with a real API client when live pricing is available.
    """

    SOURCES = list(_SOURCE_VARIATIONS.keys())

    def get_prices(self, product_id: str, base_price: float) -> dict[str, float]:
        prices = {}
        for i, (source, (low, high)) in enumerate(_SOURCE_VARIATIONS.items()):
            # Deterministic variation: hash(product_id + source) → float in [low, high]
            seed = int(hashlib.md5(f"{product_id}:{source}".encode()).hexdigest()[:8], 16)
            variation = low + (seed / 0xFFFFFFFF) * (high - low)
            raw_price = base_price * (1 + variation)
            # Round to nearest $0.99
            prices[source] = round(raw_price - 0.01, 2) if raw_price > 1 else round(raw_price, 2)
        return prices
```

#### `app/services/pricing/price_cache.py`
```python
"""Module-level price cache singleton — Redis or in-memory TTLCache."""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_price_cache = None


def get_price_cache():
    """Return the shared price cache. Uses Redis if available, else in-memory TTLCache."""
    global _price_cache
    if _price_cache is not None:
        return _price_cache

    from app.core.config import get_settings
    from app.core.cache import RedisCache, TTLCache

    settings = get_settings()
    try:
        cache = RedisCache(
            redis_url=settings.REDIS_URL,
            default_ttl=3600,  # 1-hour TTL for prices
            key_prefix="price:",
        )
        cache._client.ping()
        _price_cache = cache
        logger.info("PriceCache: using Redis")
    except Exception:
        _price_cache = TTLCache(default_ttl=3600, max_size=500)
        logger.info("PriceCache: Redis unavailable, using in-memory TTLCache")

    return _price_cache


def reset_price_cache() -> None:
    """Reset singleton (for testing)."""
    global _price_cache
    _price_cache = None
```

---

### Task 2 — Price Comparison Agent Tools (`app/agents/price/tools.py`)

```python
"""pydantic-ai tools for the PriceComparisonAgent."""

import logging
import time
from pydantic_ai import RunContext
from app.agents.dependencies import AgentDependencies
from app.models.product import Product

logger = logging.getLogger(__name__)


async def search_products_by_name(
    ctx: RunContext[AgentDependencies],
    name: str,
    limit: int = 5,
) -> list[dict]:
    """
    Search for products by name (fuzzy match on name and brand).

    Use this to find specific products mentioned by the user, e.g. "Samsung S24",
    "Google Pixel 8", "Sony WH-1000XM5".

    Args:
        name: Product name or brand+model string to search for
        limit: Maximum results (default 5)
    """
    db = ctx.deps.db
    products = (
        db.query(Product)
        .filter(Product.name.ilike(f"%{name}%"))
        .limit(limit)
        .all()
    )
    if not products:
        # Fallback: search by brand
        parts = name.split()
        if parts:
            products = (
                db.query(Product)
                .filter(Product.brand.ilike(f"%{parts[0]}%"))
                .limit(limit)
                .all()
            )
    logger.debug("search_products_by_name('%s'): found %d", name, len(products))
    return [p.to_dict() for p in products]


async def get_competitor_prices(
    ctx: RunContext[AgentDependencies],
    product_id: str,
    base_price: float,
) -> dict:
    """
    Retrieve competitor prices for a product from multiple sources.

    Checks the price cache first (1-hour TTL); fetches fresh prices on cache miss.
    Returns prices from Amazon, BestBuy, and Walmart alongside our catalog price.
    Also returns the best deal (lowest price) and savings percentage.

    Args:
        product_id: Product identifier (e.g. "PROD001")
        base_price: Our catalog price for this product
    """
    from app.services.pricing.price_cache import get_price_cache
    from app.services.pricing.mock_pricing import MockPricingService

    cache = get_price_cache()
    cached = cache.get(product_id)

    if cached:
        logger.debug("PriceCache hit for %s", product_id)
        return cached

    # Fetch fresh competitor prices
    service = MockPricingService()
    competitor_prices = service.get_prices(product_id, base_price)

    # Build full price map (include our price)
    all_prices = {"SmartShop": base_price, **competitor_prices}
    best_source = min(all_prices, key=all_prices.get)
    best_price = all_prices[best_source]
    savings_vs_highest = max(all_prices.values()) - best_price
    savings_pct = (savings_vs_highest / max(all_prices.values())) * 100 if savings_vs_highest > 0 else 0.0

    result = {
        "product_id": product_id,
        "prices": all_prices,
        "best_source": best_source,
        "best_price": best_price,
        "savings_pct": round(savings_pct, 1),
        "cached_at": time.time(),
        "is_cached": False,
    }

    cache.set(product_id, result, ttl=3600)
    logger.debug("PriceCache miss for %s — fetched and cached", product_id)
    return result
```

---

### Task 3 — Price Comparison Prompts (`app/agents/price/prompts.py`)

```python
SYSTEM_PROMPT = """You are a price comparison expert for SmartShop AI.

Your job is to compare products across multiple sources and help customers find the best deal.

Steps:
1. Search for each product mentioned in the query using search_products_by_name
2. For each product found, call get_competitor_prices to get multi-source pricing
3. Analyze the prices and features (rating, specs from description) side by side
4. Identify the best deal (lowest price with good quality)

Output requirements:
- products: Full comparison data for each product (include all sources, highlight best)
- best_deal: Name of the product that offers the best overall value
- recommendation: 2-3 sentence summary explaining why it's the best deal, citing prices and savings

Rules:
- If a product is not found in the catalog, skip it and explain in the recommendation
- Always highlight which source has the lowest price for each product
- Include percentage savings when there's a meaningful price difference (>3%)
- Keep recommendations factual and price-focused
"""
```

---

### Task 4 — PriceComparisonAgent (`app/agents/price/agent.py`)

```python
"""Price Comparison Agent using pydantic-ai."""

import logging
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from app.agents.base import BaseAgent, AgentResponse
from app.agents.dependencies import AgentDependencies
from app.agents.price.prompts import SYSTEM_PROMPT
from app.agents.price import tools
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class _PricePoint(BaseModel):
    """Price at a specific source."""
    source: str
    price: float
    is_best: bool = False


class _ProductComparison(BaseModel):
    """Comparison data for one product."""
    product_id: str
    name: str
    our_price: float
    competitor_prices: list[_PricePoint]
    best_price: float
    best_source: str
    savings_pct: float = Field(ge=0.0, description="Savings vs. highest price (%)")
    rating: float | None = None
    brand: str | None = None
    category: str | None = None
    is_cached: bool = False


class _ComparisonOutput(BaseModel):
    """Full structured output from the price comparison LLM."""
    products: list[_ProductComparison]
    best_deal: str = Field(description="Name of the product offering best overall value")
    recommendation: str = Field(description="2-3 sentence summary of the best deal and why")


def _build_agent(model_name: str) -> Agent:
    model = OpenAIModel(model_name)
    agent: Agent[AgentDependencies, _ComparisonOutput] = Agent(
        model=model,
        deps_type=AgentDependencies,
        output_type=_ComparisonOutput,
        instructions=SYSTEM_PROMPT,
    )
    agent.tool(tools.search_products_by_name)
    agent.tool(tools.get_competitor_prices)
    return agent


class PriceComparisonAgent(BaseAgent):
    """
    Price comparison agent.

    Looks up products in the catalog, fetches multi-source competitor prices
    (mock for MVP, swappable with live APIs), and uses GPT-4o-mini to produce
    a structured side-by-side comparison with best-deal identification.
    """

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        model = model_name or settings.OPENAI_MODEL
        super().__init__(name="price-comparison-agent")
        self._agent = _build_agent(model)

    async def process(self, query: str, context: dict[str, Any]) -> AgentResponse:
        deps: AgentDependencies = context.get("deps")
        if deps is None:
            return AgentResponse(
                success=False,
                data={},
                error="AgentDependencies not provided in context['deps']",
            )

        try:
            result = await self._agent.run(query, deps=deps)
            output: _ComparisonOutput = result.output

            return AgentResponse(
                success=True,
                data={
                    "query": query,
                    "products": [p.model_dump() for p in output.products],
                    "best_deal": output.best_deal,
                    "recommendation": output.recommendation,
                    "total_compared": len(output.products),
                    "agent": self.name,
                },
                metadata={"model": str(self._agent.model)},
            )
        except Exception as exc:
            logger.error("PriceComparisonAgent failed: %s", exc, exc_info=True)
            return AgentResponse(
                success=False,
                data={},
                error=f"Price comparison error: {str(exc)}",
            )
```

---

### Task 5 — Pydantic Schemas (`app/schemas/price.py`)

```python
"""Request/response schemas for the Price Comparison API."""

from typing import Optional
from pydantic import BaseModel, Field


class PriceCompareRequest(BaseModel):
    """Request body for POST /api/v1/price/compare."""
    query: str = Field(
        ..., min_length=3, max_length=500,
        description="Comparison query, e.g. 'Compare Samsung S24 and Google Pixel 8'"
    )
    max_results: int = Field(default=4, ge=1, le=10,
                              description="Max products to include in comparison")


class PricePoint(BaseModel):
    source: str
    price: float
    is_best: bool = False


class ProductComparison(BaseModel):
    product_id: str
    name: str
    our_price: float
    competitor_prices: list[PricePoint]
    best_price: float
    best_source: str
    savings_pct: float
    rating: Optional[float] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    is_cached: bool = False


class PriceCompareResponse(BaseModel):
    """Response body for POST /api/v1/price/compare."""
    query: str
    products: list[ProductComparison]
    best_deal: str
    recommendation: str
    total_compared: int
    agent: str
```

---

### Task 6 — API Endpoint (`app/api/v1/price.py`)

```python
"""Price comparison API endpoint."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.price.agent import PriceComparisonAgent
from app.schemas.price import PriceCompareRequest, PriceCompareResponse, ProductComparison, PricePoint

logger = logging.getLogger(__name__)
router = APIRouter()

_agent = PriceComparisonAgent()


@router.post("/price/compare", response_model=PriceCompareResponse, status_code=200)
async def compare_prices(
    request: PriceCompareRequest,
    db: Session = Depends(get_db),
) -> PriceCompareResponse:
    """
    Compare prices for products across multiple sources.

    Accepts a natural language query (e.g. "Compare Samsung S24 and Google Pixel 8"),
    looks up matching products, fetches competitor prices (with 1-hour cache),
    and returns a structured side-by-side comparison with best-deal identification.
    """
    deps = AgentDependencies.from_db(db)
    context = {
        "deps": deps,
        "max_results": request.max_results,
    }

    response = await _agent.process(request.query, context)

    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)

    data = response.data
    products = [
        ProductComparison(
            product_id=p["product_id"],
            name=p["name"],
            our_price=p["our_price"],
            competitor_prices=[PricePoint(**pp) for pp in p["competitor_prices"]],
            best_price=p["best_price"],
            best_source=p["best_source"],
            savings_pct=p["savings_pct"],
            rating=p.get("rating"),
            brand=p.get("brand"),
            category=p.get("category"),
            is_cached=p.get("is_cached", False),
        )
        for p in data["products"]
    ]

    return PriceCompareResponse(
        query=data["query"],
        products=products,
        best_deal=data["best_deal"],
        recommendation=data["recommendation"],
        total_compared=data["total_compared"],
        agent=data["agent"],
    )
```

---

### Task 7 — Register Router (`app/main.py`)

Add after existing v1 routers:
```python
from app.api.v1.price import router as price_router
app.include_router(price_router, prefix="/api/v1", tags=["price"])
```

---

### Task 8 — Update Streamlit UI

#### `app/ui/api_client.py` — add `compare_prices()`:
```python
def compare_prices(
    api_url: str,
    query: str,
    max_results: int = 4,
) -> dict[str, Any]:
    """
    Call POST /api/v1/price/compare.
    Returns {"success": bool, "data": PriceCompareResponse dict, "error": str | None}
    """
    return _post(f"{api_url}/api/v1/price/compare", {"query": query, "max_results": max_results})
```

#### `app/ui/streamlit_app.py` — replace Pricing Insights page stub:

Replace the existing `elif page == "💰 Pricing Insights":` block with:
```python
elif page == "💰 Pricing Insights":
    st.header("Pricing Insights")
    st.caption(
        "Compare prices across Amazon, BestBuy, and Walmart to find the best deal."
    )

    query = st.text_input(
        "What would you like to compare?",
        placeholder="e.g. 'Compare Samsung S24 and Google Pixel 8'",
    )
    max_results = st.slider("Max products to compare", 2, 6, 4)

    if st.button("Compare Prices", type="primary"):
        if not query.strip():
            st.warning("Please enter a comparison query.")
        else:
            with st.spinner("Fetching prices from multiple sources..."):
                result = compare_prices(api_url, query=query, max_results=max_results)

            if result["success"]:
                data = result["data"]
                st.success(f"Compared **{data['total_compared']}** products")

                # Best deal highlight
                st.info(f"🏆 **Best Deal:** {data['best_deal']}\n\n{data['recommendation']}")

                # Side-by-side comparison table
                if data["products"]:
                    import pandas as pd

                    # Build comparison DataFrame
                    rows = []
                    for p in data["products"]:
                        row = {
                            "Product": p["name"],
                            "SmartShop": f"${p['our_price']:,.2f}",
                        }
                        for pp in p["competitor_prices"]:
                            row[pp["source"]] = f"${pp['price']:,.2f}" + (" ✓" if pp["is_best"] else "")
                        row["Best Price"] = f"${p['best_price']:,.2f} ({p['best_source']})"
                        row["Savings"] = f"{p['savings_pct']:.1f}%" if p["savings_pct"] > 0 else "—"
                        row["Rating"] = f"{'⭐' * round(p['rating'])} ({p['rating']:.1f})" if p.get("rating") else "N/A"
                        row["Cached"] = "♻️" if p.get("is_cached") else "🔴 Live"
                        rows.append(row)

                    df = pd.DataFrame(rows).set_index("Product")
                    st.dataframe(df, use_container_width=True)
            else:
                st.error(result["error"])
```

Also update the import at the top of `streamlit_app.py`:
```python
from app.ui.api_client import (
    health_check,
    get_recommendations,
    summarize_reviews,
    search_products,
    compare_prices,          # ADD THIS
)
```

---

### Task 9 — Tests

#### `tests/test_agents/test_price_agent.py` (6 tests)
```python
"""Tests for PriceComparisonAgent."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.price.agent import PriceComparisonAgent
from app.agents.base import AgentResponse


@pytest.fixture
def mock_deps(db_session):
    from app.agents.dependencies import AgentDependencies
    from app.core.config import get_settings
    return AgentDependencies(db=db_session, settings=get_settings())


@pytest.mark.asyncio
async def test_process_returns_success(mock_deps):
    agent = PriceComparisonAgent()
    mock_output = MagicMock()
    mock_output.products = [
        MagicMock(
            product_id="PROD001",
            name="Samsung Galaxy S24",
            our_price=799.99,
            competitor_prices=[
                MagicMock(source="Amazon", price=749.99, is_best=True),
                MagicMock(source="BestBuy", price=819.99, is_best=False),
                MagicMock(source="Walmart", price=699.99, is_best=False),
            ],
            best_price=699.99,
            best_source="Walmart",
            savings_pct=12.5,
            rating=4.5,
            brand="Samsung",
            category="smartphones",
            is_cached=False,
            model_dump=lambda: {
                "product_id": "PROD001", "name": "Samsung Galaxy S24",
                "our_price": 799.99, "competitor_prices": [], "best_price": 699.99,
                "best_source": "Walmart", "savings_pct": 12.5, "rating": 4.5,
                "brand": "Samsung", "category": "smartphones", "is_cached": False,
            }
        )
    ]
    mock_output.best_deal = "Samsung Galaxy S24"
    mock_output.recommendation = "Walmart offers the best price at $699.99, saving 12.5%."

    with patch.object(agent._agent, "run", new_callable=AsyncMock) as mock_run:
        result_mock = MagicMock()
        result_mock.output = mock_output
        mock_run.return_value = result_mock
        response = await agent.process(
            "Compare Samsung S24 prices",
            context={"deps": mock_deps},
        )

    assert response.success is True
    assert response.data["best_deal"] == "Samsung Galaxy S24"
    assert response.data["total_compared"] == 1
    assert response.data["agent"] == "price-comparison-agent"


@pytest.mark.asyncio
async def test_process_missing_deps_returns_error():
    agent = PriceComparisonAgent()
    response = await agent.process("Compare phones", context={})
    assert response.success is False
    assert "AgentDependencies not provided" in response.error


@pytest.mark.asyncio
async def test_process_exception_handled(mock_deps):
    agent = PriceComparisonAgent()
    with patch.object(agent._agent, "run", side_effect=Exception("LLM timeout")):
        response = await agent.process("Compare phones", context={"deps": mock_deps})
    assert response.success is False
    assert "Price comparison error" in response.error


def test_price_agent_name():
    agent = PriceComparisonAgent()
    assert agent.name == "price-comparison-agent"


def test_mock_pricing_service_deterministic():
    from app.services.pricing.mock_pricing import MockPricingService
    service = MockPricingService()
    prices1 = service.get_prices("PROD001", 799.99)
    prices2 = service.get_prices("PROD001", 799.99)
    assert prices1 == prices2  # deterministic


def test_mock_pricing_service_sources():
    from app.services.pricing.mock_pricing import MockPricingService
    service = MockPricingService()
    prices = service.get_prices("PROD001", 100.0)
    assert set(prices.keys()) == {"Amazon", "BestBuy", "Walmart"}
    for source, price in prices.items():
        assert price > 0
        assert price != 100.0  # should differ from base
```

#### `tests/test_api/test_price.py` (7 tests)
```python
"""TestClient tests for POST /api/v1/price/compare."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.agents.base import AgentResponse

client = TestClient(app)


def mock_price_response(products=None, best_deal="Samsung S24", recommendation="Best deal at Walmart."):
    return AgentResponse(
        success=True,
        data={
            "query": "Compare phones",
            "products": products or [{
                "product_id": "PROD001",
                "name": "Samsung S24",
                "our_price": 799.99,
                "competitor_prices": [
                    {"source": "Amazon", "price": 749.99, "is_best": True},
                    {"source": "BestBuy", "price": 829.99, "is_best": False},
                    {"source": "Walmart", "price": 699.99, "is_best": False},
                ],
                "best_price": 699.99,
                "best_source": "Walmart",
                "savings_pct": 12.5,
                "rating": 4.5,
                "brand": "Samsung",
                "category": "smartphones",
                "is_cached": False,
            }],
            "best_deal": best_deal,
            "recommendation": recommendation,
            "total_compared": 1,
            "agent": "price-comparison-agent",
        }
    )


def test_compare_prices_success():
    with patch("app.api.v1.price._agent.process", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = mock_price_response()
        resp = client.post("/api/v1/price/compare", json={"query": "Compare Samsung S24 and Pixel 8"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["best_deal"] == "Samsung S24"
    assert data["total_compared"] == 1
    assert len(data["products"]) == 1
    assert data["products"][0]["best_source"] == "Walmart"


def test_compare_prices_empty_query():
    resp = client.post("/api/v1/price/compare", json={"query": ""})
    assert resp.status_code == 422


def test_compare_prices_query_too_short():
    resp = client.post("/api/v1/price/compare", json={"query": "ab"})
    assert resp.status_code == 422


def test_compare_prices_missing_query():
    resp = client.post("/api/v1/price/compare", json={})
    assert resp.status_code == 422


def test_compare_prices_agent_failure():
    with patch("app.api.v1.price._agent.process", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = AgentResponse(
            success=False, data={}, error="Product not found in catalog"
        )
        resp = client.post("/api/v1/price/compare", json={"query": "Compare XYZ123 and ABC456"})
    assert resp.status_code == 500
    assert "Product not found" in resp.json()["detail"]


def test_compare_prices_competitor_prices_in_response():
    with patch("app.api.v1.price._agent.process", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = mock_price_response()
        resp = client.post("/api/v1/price/compare", json={"query": "Compare Samsung S24 prices"})
    product = resp.json()["products"][0]
    assert len(product["competitor_prices"]) == 3
    sources = [pp["source"] for pp in product["competitor_prices"]]
    assert "Amazon" in sources
    assert "BestBuy" in sources
    assert "Walmart" in sources


def test_compare_prices_savings_pct_present():
    with patch("app.api.v1.price._agent.process", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = mock_price_response()
        resp = client.post("/api/v1/price/compare", json={"query": "best laptop deal"})
    assert resp.json()["products"][0]["savings_pct"] == 12.5
```

---

## Testing Requirements
- `tests/test_agents/test_price_agent.py` — 6 tests
- `tests/test_api/test_price.py` — 7 tests
- All existing 209 tests must continue to pass
- Target: **+13 new tests, 222 total**

---

## Key Notes for Claude Code
1. `MockPricingService.get_prices()` is **synchronous** — no `await` needed; it's purely computational
2. `get_price_cache()` follows the exact same singleton pattern as `get_review_cache()` in `app/core/cache.py` — use `reset_price_cache()` in test fixtures
3. The `_ComparisonOutput.products` uses `model_dump()` to serialize — make sure `_ProductComparison` model includes all fields in `ProductComparison` schema
4. In `compare_prices()` API endpoint, use `p.model_dump()` to convert `_ProductComparison` before passing to `ProductComparison(...)` — or map fields explicitly as shown above
5. The `is_cached` field indicates whether prices came from cache (shows "♻️" in UI) vs. freshly fetched ("🔴 Live")
6. The `streamlit_app.py` import of `compare_prices` must be added to the existing import block at the top of the file
7. **Response time <3s**: `MockPricingService` is instantaneous; the bottleneck is the LLM call (~1-2s for `gpt-4o-mini`) — well within target
8. The `plans/plan/` files for SCRUM-15, 16, 17, 18 were cleaned up (truncated) — they will be re-created when those stories move to "In Progress"
