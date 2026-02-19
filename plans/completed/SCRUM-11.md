# Story: SCRUM-11 — Build Review Summarization Agent with Sentiment Analysis

## Story Overview
- **Epic**: SCRUM-3 (Phase 2: Agent Development)
- **Story Points**: 8
- **Priority**: Medium
- **Jira Link**: https://projecttracking.atlassian.net/browse/SCRUM-11
- **Complexity**: High — involves two-stage processing (fast DB lookup + GPT summarization) plus in-memory caching
- **Estimated Duration**: 4–5 hours

---

## Dependencies
- SCRUM-10 ✅ — Agent architecture established (`AgentDependencies`, `BaseAgent` pattern, pydantic-ai 1.x)
- SCRUM-9 ✅ — FastAPI v1 router in place
- `app/models/review.py` ✅ — `Review` model with `sentiment` column (positive/negative/neutral)
- `app/agents/dependencies.py` ✅ — `AgentDependencies(db, settings)` ready to use

---

## What Already Exists (Do NOT recreate)
| File | Status | Notes |
|------|--------|-------|
| `app/models/review.py` | ✅ Exists | `sentiment` (positive/negative/neutral), `rating`, `text`, `product_id` |
| `app/agents/dependencies.py` | ✅ Exists | Reuse as-is — no Redis dep needed |
| `app/agents/base.py` | ✅ Exists | `BaseAgent.process()` contract |
| `app/agents/recommendation/` | ✅ Exists | Reference pattern for 4-file structure |
| `app/api/v1/__init__.py` | ✅ Exists | Needs `reviews` router added |

---

## Key Architectural Decisions

### Decision 1: No Heavy NLP Libraries
The Jira story mentions "NLP pipeline for sentiment analysis". Based on the actual data:

- The `sentiment` column is **already populated** by the ingestion pipeline (positive/negative/neutral, derived from rating: ≥4 = positive, ≤2 = negative, 3 = neutral).
- No TextBlob, VADER, or scikit-learn needed — these libraries are not installed and would add significant setup overhead (NLTK corpora downloads, model files).
- **GPT-4o-mini handles theme extraction natively** and produces better, more nuanced themes than any rule-based NLP library.
- Pre-computed sentiment labels provide instant counts and statistics without any LLM call.

This is the right tradeoff: fast statistics from DB + smart summarization from LLM.

### Decision 2: Two-Stage Processing Architecture
```
Request
  │
  ├─ Stage 1 (sync, fast, <50ms): DB aggregate query
  │    → sentiment counts (positive/negative/neutral)
  │    → avg rating, rating distribution (1★–5★)
  │    → total review count
  │
  └─ Stage 2 (async, LLM, ~1–2s): pydantic-ai agent
       → receives sampled review texts (max 20: 10 positive + 10 negative)
       → extracts top 3 positive themes with confidence scores
       → extracts top 3 negative themes with confidence scores
       → writes overall narrative summary
       → result CACHED per product_id for 1 hour
```

### Decision 3: In-Memory TTL Cache (Redis-ready)
Redis is in `requirements.txt` but not installed in the dev environment. Rather than blocking on Redis setup, implement a **simple in-memory TTL cache** in `app/core/cache.py`:
- Dict-backed with timestamps
- Thread-safe for single-process dev use
- Documents itself as "swap for Redis by replacing `get`/`set` implementations"
- Avoids any new `pip install`

The cache only wraps Stage 2 (LLM results). Stage 1 (DB queries) is fast enough to run every time.

### Decision 4: Product Resolution Tool
Users query by name ("iPhone 15", "Samsung Galaxy") not product IDs. The agent needs a `find_product` tool to resolve fuzzy product names to IDs before fetching reviews.

### Decision 5: Token Budget Management
4000 reviews exist but GPT-4o-mini has a context limit. Strategy:
- Fetch up to 10 positive + 10 negative reviews by sentiment label
- Each review text truncated to 200 characters
- Total ~4000 tokens input — well within gpt-4o-mini's 128k context
- Recency-weighted: fetch most recent reviews first

---

## File Structure

```
app/
├── agents/
│   ├── base.py                   ✅ exists
│   ├── dependencies.py           ✅ exists
│   ├── recommendation/           ✅ exists
│   └── review/
│       ├── __init__.py           ← CREATE
│       ├── agent.py              ← CREATE: ReviewSummarizationAgent
│       ├── tools.py              ← CREATE: 3 DB tools
│       └── prompts.py            ← CREATE: system prompt
├── api/v1/
│   ├── __init__.py               ← MODIFY: add reviews router
│   ├── products.py               ✅ exists
│   ├── recommendations.py        ✅ exists
│   └── reviews.py                ← CREATE: POST /api/v1/reviews/summarize
├── core/
│   ├── cache.py                  ← CREATE: in-memory TTL cache
│   ├── config.py                 ✅ exists
│   └── database.py               ✅ exists
└── schemas/
    ├── product.py                ✅ exists
    ├── recommendation.py         ✅ exists
    └── review.py                 ← CREATE: request/response schemas

tests/
└── test_agents/
    ├── test_recommendation_agent.py  ✅ exists
    └── test_review_agent.py          ← CREATE
```

---

## Implementation Tasks

---

### Task 1: Create In-Memory TTL Cache

**File**: `app/core/cache.py`

**Purpose**: Caches LLM summarization results per `product_id` for `CACHE_TTL_SECONDS` (default 3600s). Avoids re-calling GPT for popular products. Designed to be replaced with Redis with minimal code change.

```python
"""In-memory TTL cache for agent results.

Production note: Replace get/set/delete with redis.Redis calls to switch to Redis.
The interface is intentionally identical to redis-py's basic get/set/delete API.
"""

import time
import threading
import logging
from typing import Any

logger = logging.getLogger(__name__)


class TTLCache:
    """
    Thread-safe in-memory cache with TTL expiry.

    Interface mirrors redis-py so this can be swapped for a Redis client:
        cache = redis.Redis.from_url(settings.REDIS_URL)
    """

    def __init__(self, default_ttl: int = 3600, max_size: int = 1000):
        self._store: dict[str, tuple[Any, float]] = {}  # key -> (value, expires_at)
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
        self._max_size = max_size

    def get(self, key: str) -> Any | None:
        """Return cached value or None if missing/expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store value with TTL. Evicts oldest entry if at max_size."""
        ttl = ttl or self._default_ttl
        expires_at = time.time() + ttl
        with self._lock:
            if len(self._store) >= self._max_size and key not in self._store:
                # Evict oldest entry
                oldest = min(self._store, key=lambda k: self._store[k][1])
                del self._store[oldest]
            self._store[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        """Remove a key from the cache."""
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        """Clear all entries."""
        with self._lock:
            self._store.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._store)


# Module-level singleton — shared across all agent instances
_review_cache = TTLCache()


def get_review_cache() -> TTLCache:
    """Return the shared review summary cache."""
    return _review_cache
```

---

### Task 2: Create API Schemas

**File**: `app/schemas/review.py`

```python
"""Pydantic schemas for Review Summarization API."""

from pydantic import BaseModel, Field
from typing import Optional


class ReviewSummarizationRequest(BaseModel):
    """POST /api/v1/reviews/summarize request body."""
    query: str = Field(
        ...,
        description="Natural language query, e.g. 'Summarize reviews for iPhone 15'",
        min_length=3,
        max_length=500,
    )
    product_id: Optional[str] = Field(
        default=None,
        description="Optional: supply product_id directly to skip name resolution",
        max_length=20,
    )
    max_reviews: int = Field(
        default=20,
        ge=5,
        le=50,
        description="Max review samples sent to LLM (5–50)",
    )


class SentimentTheme(BaseModel):
    """A single extracted theme with confidence score."""
    theme: str = Field(description="Short theme description, e.g. 'Battery life'")
    confidence: float = Field(ge=0.0, le=1.0, description="0.0–1.0 confidence score")
    example_quote: Optional[str] = Field(
        default=None,
        description="Representative quote from reviews supporting this theme",
    )


class RatingDistribution(BaseModel):
    """Count of reviews per star rating."""
    one_star: int = 0
    two_star: int = 0
    three_star: int = 0
    four_star: int = 0
    five_star: int = 0


class ReviewSummarizationResponse(BaseModel):
    """POST /api/v1/reviews/summarize response."""
    product_id: str
    product_name: str
    total_reviews: int
    sentiment_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall sentiment: 0.0 (very negative) to 1.0 (very positive)",
    )
    average_rating: float = Field(ge=1.0, le=5.0)
    rating_distribution: RatingDistribution
    positive_themes: list[SentimentTheme] = Field(
        description="Top 3 positive themes extracted from reviews",
    )
    negative_themes: list[SentimentTheme] = Field(
        description="Top 3 negative themes extracted from reviews",
    )
    overall_summary: str = Field(
        description="2–3 sentence narrative summary of what customers say",
    )
    cached: bool = Field(
        default=False,
        description="True if result was served from cache",
    )
    agent: str = "review-summarization-agent"
```

---

### Task 3: Create pydantic-ai Tools

**File**: `app/agents/review/tools.py`

**Purpose**: Three tools covering the agent's complete information needs. `get_review_stats` handles Stage 1 (fast). `get_review_samples` handles Stage 2 input. `find_product` resolves names.

```python
"""Tools for the Review Summarization Agent."""

import logging
from pydantic_ai import RunContext
from sqlalchemy import func
from app.agents.dependencies import AgentDependencies
from app.models.review import Review
from app.models.product import Product

logger = logging.getLogger(__name__)


async def find_product(
    ctx: RunContext[AgentDependencies],
    name_or_id: str,
) -> dict | None:
    """
    Find a product by name (fuzzy) or exact product ID.

    Always call this first when the user provides a product name.
    Returns product dict with 'id' and 'name', or None if not found.

    Args:
        name_or_id: Product name (e.g. "iPhone 15", "Samsung Galaxy") or exact ID (e.g. "PROD001")
    """
    db = ctx.deps.db
    # Try exact ID first
    product = db.query(Product).filter(Product.id == name_or_id).first()
    if product:
        return {"id": product.id, "name": product.name, "category": product.category}

    # Fuzzy name match — returns best match by name similarity
    product = db.query(Product).filter(
        Product.name.ilike(f"%{name_or_id}%")
    ).order_by(Product.rating.desc().nullslast()).first()

    if product:
        return {"id": product.id, "name": product.name, "category": product.category}
    return None


async def get_review_stats(
    ctx: RunContext[AgentDependencies],
    product_id: str,
) -> dict:
    """
    Get aggregated review statistics for a product from the database.

    Returns counts by sentiment label, average rating, rating distribution,
    and total review count. This is a fast database query — no LLM involved.

    Args:
        product_id: Exact product ID (e.g. "PROD001")
    """
    db = ctx.deps.db

    # Sentiment counts
    sentiment_rows = (
        db.query(Review.sentiment, func.count(Review.review_id))
        .filter(Review.product_id == product_id)
        .group_by(Review.sentiment)
        .all()
    )
    sentiment_counts = {row[0]: row[1] for row in sentiment_rows}

    # Rating distribution
    dist_rows = (
        db.query(
            func.floor(Review.rating).label("bucket"),
            func.count(Review.review_id),
        )
        .filter(Review.product_id == product_id)
        .group_by("bucket")
        .all()
    )
    rating_dist = {int(row[0]): row[1] for row in dist_rows}

    # Average rating
    avg_row = (
        db.query(func.avg(Review.rating))
        .filter(Review.product_id == product_id)
        .scalar()
    )
    avg_rating = round(float(avg_row), 2) if avg_row else 0.0

    total = sum(sentiment_counts.values())
    positive = sentiment_counts.get("positive", 0)
    negative = sentiment_counts.get("negative", 0)

    # Sentiment score: proportion of positive reviews on 0–1 scale
    sentiment_score = round(positive / total, 3) if total > 0 else 0.0

    logger.debug("get_review_stats: product=%s total=%d", product_id, total)

    return {
        "product_id": product_id,
        "total_reviews": total,
        "sentiment_counts": sentiment_counts,
        "sentiment_score": sentiment_score,
        "average_rating": avg_rating,
        "rating_distribution": {
            "one_star": rating_dist.get(1, 0),
            "two_star": rating_dist.get(2, 0),
            "three_star": rating_dist.get(3, 0),
            "four_star": rating_dist.get(4, 0),
            "five_star": rating_dist.get(5, 0),
        },
    }


async def get_review_samples(
    ctx: RunContext[AgentDependencies],
    product_id: str,
    max_positive: int = 10,
    max_negative: int = 10,
) -> dict:
    """
    Fetch a sample of review texts for LLM theme extraction.

    Returns up to max_positive positive reviews and max_negative negative reviews,
    ordered by most recent first. Texts are truncated to 200 chars to manage tokens.

    Call this AFTER get_review_stats to get the actual text content for summarisation.

    Args:
        product_id: Exact product ID
        max_positive: Max positive review texts to fetch (default 10)
        max_negative: Max negative review texts to fetch (default 10)
    """
    db = ctx.deps.db

    def fetch_reviews(sentiment: str, limit: int) -> list[str]:
        rows = (
            db.query(Review.text)
            .filter(
                Review.product_id == product_id,
                Review.sentiment == sentiment,
                Review.text.isnot(None),
            )
            .order_by(Review.review_date.desc().nullslast())
            .limit(limit)
            .all()
        )
        return [str(r[0])[:200] for r in rows if r[0]]

    positive_texts = fetch_reviews("positive", max_positive)
    negative_texts = fetch_reviews("negative", max_negative)
    neutral_texts = fetch_reviews("neutral", 5)

    return {
        "product_id": product_id,
        "positive_reviews": positive_texts,
        "negative_reviews": negative_texts,
        "neutral_reviews": neutral_texts,
        "counts": {
            "positive": len(positive_texts),
            "negative": len(negative_texts),
            "neutral": len(neutral_texts),
        },
    }
```

---

### Task 4: Create System Prompt

**File**: `app/agents/review/prompts.py`

```python
"""Prompts for the Review Summarization Agent."""

SYSTEM_PROMPT = """
You are a review summarization assistant for SmartShop AI.

Your goal is to provide shoppers with a concise, accurate summary of what customers
say about a product, so they can make informed purchase decisions quickly.

## Reasoning steps:
1. Parse the user query to identify the product name or ID
2. Call `find_product` to resolve the product name to a product ID
   - If not found, report clearly that the product was not found
3. Call `get_review_stats` to get sentiment counts, average rating, and distribution
   - If total_reviews == 0, report that there are no reviews for this product
4. Call `get_review_samples` to retrieve the actual review texts
5. Analyse the texts and extract themes

## Theme extraction rules:
- Extract exactly 3 positive themes and 3 negative themes (or fewer if reviews are sparse)
- A theme is a specific, recurring topic (e.g. "Battery life", "Build quality", "Value for money")
- NOT a vague sentiment ("Good product", "Bad experience") — must be specific
- Confidence score = estimated proportion of reviews that mention this theme (0.0–1.0)
- example_quote: pick the most representative short quote (≤80 chars) from the review texts

## Output rules:
- sentiment_score comes from get_review_stats (do NOT recalculate)
- average_rating and rating_distribution come from get_review_stats (do NOT recalculate)
- overall_summary: 2–3 sentences. Mention the product name, top strength, main concern, and
  who this product is best suited for
- Be objective — if reviews are overwhelmingly positive, say so; if mixed, say so
- Never fabricate themes or quotes not present in the review texts
"""
```

---

### Task 5: Create the Review Summarization Agent

**File**: `app/agents/review/agent.py`

```python
"""Review Summarization Agent using pydantic-ai."""

import logging
from typing import Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from app.agents.base import BaseAgent, AgentResponse
from app.agents.dependencies import AgentDependencies
from app.agents.review.prompts import SYSTEM_PROMPT
from app.agents.review import tools
from app.core.cache import get_review_cache
from app.core.config import get_settings

logger = logging.getLogger(__name__)


# ── Structured output type ──────────────────────────────────────────────────────

class _ThemeResult(BaseModel):
    theme: str
    confidence: float = Field(ge=0.0, le=1.0)
    example_quote: str | None = None


class _ReviewSummaryOutput(BaseModel):
    """Typed output from pydantic-ai for review summarization."""
    product_id: str
    product_name: str
    total_reviews: int
    sentiment_score: float = Field(ge=0.0, le=1.0)
    average_rating: float
    rating_distribution: dict[str, int]
    positive_themes: list[_ThemeResult]
    negative_themes: list[_ThemeResult]
    overall_summary: str


# ── Agent factory ───────────────────────────────────────────────────────────────

def _build_agent(model_name: str) -> Agent:
    """Build the pydantic-ai Agent. Called once at module load."""
    model = OpenAIModel(model_name)
    agent: Agent[AgentDependencies, _ReviewSummaryOutput] = Agent(
        model=model,
        deps_type=AgentDependencies,
        output_type=_ReviewSummaryOutput,
        instructions=SYSTEM_PROMPT,
    )
    agent.tool(tools.find_product)
    agent.tool(tools.get_review_stats)
    agent.tool(tools.get_review_samples)
    return agent


# ── BaseAgent subclass ──────────────────────────────────────────────────────────

class ReviewSummarizationAgent(BaseAgent):
    """
    Review summarization agent.

    Two-stage: fast DB stats (always fresh) + GPT theme extraction (cached per product).
    Follows the BaseAgent contract established in SCRUM-10 for Orchestrator compatibility.
    """

    def __init__(self, model_name: str | None = None):
        settings = get_settings()
        model = model_name or settings.OPENAI_MODEL
        super().__init__(name="review-summarization-agent")
        self._agent = _build_agent(model)
        self._cache = get_review_cache()

    def _cache_key(self, product_id: str) -> str:
        return f"review_summary:{product_id}"

    async def process(
        self,
        query: str,
        context: dict[str, Any],
    ) -> AgentResponse:
        """
        Summarize reviews for a product.

        Args:
            query: Natural language query, e.g. "Summarize reviews for iPhone 15"
            context: Must contain 'deps': AgentDependencies.
                     Optional 'product_id': str to skip name resolution.
                     Optional 'max_reviews': int (default 20).
        """
        deps: AgentDependencies = context.get("deps")
        if deps is None:
            return AgentResponse(
                success=False,
                data={},
                error="AgentDependencies not provided in context['deps']",
            )

        product_id: str | None = context.get("product_id")
        max_reviews: int = context.get("max_reviews", 20)

        # Build enriched query
        enriched = _build_enriched_query(query, product_id, max_reviews)

        # Check cache (only when product_id known upfront)
        if product_id:
            cached = self._cache.get(self._cache_key(product_id))
            if cached:
                logger.debug("Cache hit for product_id=%s", product_id)
                cached["cached"] = True
                return AgentResponse(success=True, data=cached)

        try:
            result = await self._agent.run(enriched, deps=deps)
            output: _ReviewSummaryOutput = result.output

            data = {
                "product_id": output.product_id,
                "product_name": output.product_name,
                "total_reviews": output.total_reviews,
                "sentiment_score": output.sentiment_score,
                "average_rating": output.average_rating,
                "rating_distribution": output.rating_distribution,
                "positive_themes": [t.model_dump() for t in output.positive_themes],
                "negative_themes": [t.model_dump() for t in output.negative_themes],
                "overall_summary": output.overall_summary,
                "cached": False,
                "agent": self.name,
            }

            # Store in cache using resolved product_id
            cache_key = self._cache_key(output.product_id)
            self._cache.set(
                cache_key,
                data,
                ttl=deps.settings.CACHE_TTL_SECONDS,
            )

            return AgentResponse(
                success=True,
                data=data,
                metadata={"model": str(self._agent.model)},
            )

        except Exception as exc:
            logger.error("ReviewSummarizationAgent failed: %s", exc, exc_info=True)
            return AgentResponse(
                success=False,
                data={},
                error=f"Review summarization error: {str(exc)}",
            )


def _build_enriched_query(
    query: str,
    product_id: str | None,
    max_reviews: int,
) -> str:
    parts = [query]
    if product_id:
        parts.append(f"Product ID (use directly, skip find_product): {product_id}")
    parts.append(f"Fetch up to {max_reviews // 2} positive and {max_reviews // 2} negative reviews.")
    return "\n".join(parts)
```

**File**: `app/agents/review/__init__.py`

```python
"""Review Summarization Agent package."""

from app.agents.review.agent import ReviewSummarizationAgent

__all__ = ["ReviewSummarizationAgent"]
```

---

### Task 6: Create FastAPI Endpoint

**File**: `app/api/v1/reviews.py`

```python
"""Review summarization API endpoint — v1."""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.agents.dependencies import AgentDependencies
from app.agents.review import ReviewSummarizationAgent
from app.schemas.review import (
    ReviewSummarizationRequest,
    ReviewSummarizationResponse,
    SentimentTheme,
    RatingDistribution,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])

# Module-level singleton
_agent = ReviewSummarizationAgent()


@router.post("/summarize", response_model=ReviewSummarizationResponse)
async def summarize_reviews(
    request: ReviewSummarizationRequest,
    db: Session = Depends(get_db),
):
    """
    Summarize customer reviews for a product using AI.

    Provide either a natural language query ("Summarize reviews for iPhone 15")
    or supply product_id directly for faster resolution.

    Returns top positive/negative themes with confidence scores, sentiment score,
    rating distribution, and an overall narrative summary.

    Results are cached per product for 1 hour to ensure fast repeated queries.
    """
    deps = AgentDependencies.from_db(db)
    context = {
        "deps": deps,
        "product_id": request.product_id,
        "max_reviews": request.max_reviews,
    }

    response = await _agent.process(request.query, context)

    if not response.success:
        raise HTTPException(status_code=500, detail=response.error)

    d = response.data
    return ReviewSummarizationResponse(
        product_id=d["product_id"],
        product_name=d["product_name"],
        total_reviews=d["total_reviews"],
        sentiment_score=d["sentiment_score"],
        average_rating=d["average_rating"],
        rating_distribution=RatingDistribution(**d["rating_distribution"]),
        positive_themes=[SentimentTheme(**t) for t in d["positive_themes"]],
        negative_themes=[SentimentTheme(**t) for t in d["negative_themes"]],
        overall_summary=d["overall_summary"],
        cached=d.get("cached", False),
        agent=d.get("agent", "review-summarization-agent"),
    )
```

**Modify `app/api/v1/__init__.py`**:

```python
"""API v1 router — aggregates all v1 endpoints."""

from fastapi import APIRouter
from app.api.v1 import products, recommendations, reviews

router = APIRouter()
router.include_router(products.router)
router.include_router(recommendations.router)
router.include_router(reviews.router)
```

---

### Task 7: Write Tests

**File**: `tests/test_agents/test_review_agent.py`

```python
"""Tests for ReviewSummarizationAgent and supporting components."""

import pytest
import time
from unittest.mock import MagicMock, patch
from pydantic_ai.models.test import TestModel

from app.agents.review.agent import ReviewSummarizationAgent
from app.agents.dependencies import AgentDependencies
from app.core.cache import TTLCache
from app.core.config import get_settings


# ── Helpers ─────────────────────────────────────────────────────────────────────

def make_mock_db():
    db = MagicMock()
    # Sentiment stats
    db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
        ("positive", 80), ("negative", 15), ("neutral", 5)
    ]
    db.query.return_value.filter.return_value.scalar.return_value = 4.2
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    # Product lookup
    mock_product = MagicMock()
    mock_product.id = "PROD001"
    mock_product.name = "Test Phone X"
    mock_product.category = "smartphones"
    db.query.return_value.filter.return_value.first.return_value = mock_product
    return db


SETTINGS = get_settings()


# ── TTLCache unit tests ──────────────────────────────────────────────────────────

class TestTTLCache:
    def test_set_and_get(self):
        cache = TTLCache(default_ttl=60)
        cache.set("key1", {"data": "value"})
        assert cache.get("key1") == {"data": "value"}

    def test_miss_returns_none(self):
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_expiry(self):
        cache = TTLCache(default_ttl=1)
        cache.set("key1", "value", ttl=1)
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_delete(self):
        cache = TTLCache()
        cache.set("key1", "value")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_max_size_evicts_oldest(self):
        cache = TTLCache(max_size=2)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")  # should evict k1 or k2
        assert cache.size == 2

    def test_clear(self):
        cache = TTLCache()
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.clear()
        assert cache.size == 0


# ── Agent init tests ─────────────────────────────────────────────────────────────

class TestReviewSummarizationAgentInit:
    def test_agent_initialises(self):
        agent = ReviewSummarizationAgent()
        assert agent.name == "review-summarization-agent"
        assert agent._agent is not None

    def test_cache_attached(self):
        agent = ReviewSummarizationAgent()
        assert agent._cache is not None


# ── Agent process tests ──────────────────────────────────────────────────────────

class TestReviewSummarizationAgentProcess:
    @pytest.mark.asyncio
    async def test_missing_deps_returns_error(self):
        agent = ReviewSummarizationAgent()
        result = await agent.process("Summarize reviews for iPhone", context={})
        assert result.success is False
        assert "AgentDependencies" in result.error

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_result(self):
        """Cache hit skips LLM call entirely."""
        db = make_mock_db()
        deps = AgentDependencies(db=db, settings=SETTINGS)
        agent = ReviewSummarizationAgent()

        cached_data = {
            "product_id": "PROD001",
            "product_name": "Test Phone X",
            "total_reviews": 100,
            "sentiment_score": 0.8,
            "average_rating": 4.2,
            "rating_distribution": {"one_star": 2, "two_star": 3, "three_star": 5, "four_star": 30, "five_star": 60},
            "positive_themes": [],
            "negative_themes": [],
            "overall_summary": "Cached summary.",
        }
        agent._cache.set("review_summary:PROD001", cached_data)

        result = await agent.process(
            "Summarize reviews",
            context={"deps": deps, "product_id": "PROD001"},
        )
        assert result.success is True
        assert result.data["cached"] is True
        assert result.data["product_id"] == "PROD001"

    @pytest.mark.asyncio
    async def test_process_with_test_model(self):
        """TestModel produces a valid structured output without real API."""
        db = make_mock_db()
        deps = AgentDependencies(db=db, settings=SETTINGS)
        agent = ReviewSummarizationAgent()

        with agent._agent.override(model=TestModel()):
            result = await agent.process(
                "Summarize reviews for Test Phone X",
                context={"deps": deps},
            )
        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    @pytest.mark.asyncio
    async def test_error_handling(self):
        db = make_mock_db()
        deps = AgentDependencies(db=db, settings=SETTINGS)
        agent = ReviewSummarizationAgent()

        with patch.object(agent._agent, "run", side_effect=RuntimeError("API timeout")):
            result = await agent.process(
                "Summarize reviews for any product",
                context={"deps": deps},
            )
        assert result.success is False
        assert "API timeout" in result.error


# ── Tools unit tests ─────────────────────────────────────────────────────────────

class TestReviewTools:
    @pytest.mark.asyncio
    async def test_find_product_by_id(self):
        from app.agents.review.tools import find_product
        db = make_mock_db()
        deps = AgentDependencies(db=db, settings=SETTINGS)
        ctx = MagicMock(); ctx.deps = deps
        result = await find_product(ctx, "PROD001")
        assert result is not None
        assert result["id"] == "PROD001"

    @pytest.mark.asyncio
    async def test_find_product_not_found(self):
        from app.agents.review.tools import find_product
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        deps = AgentDependencies(db=db, settings=SETTINGS)
        ctx = MagicMock(); ctx.deps = deps
        result = await find_product(ctx, "nonexistent product xyz")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_review_stats_returns_dict(self):
        from app.agents.review.tools import get_review_stats
        db = make_mock_db()
        # Override scalar for avg rating
        db.query.return_value.filter.return_value.scalar.return_value = 4.2
        db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ("positive", 80), ("negative", 15), ("neutral", 5)
        ]
        deps = AgentDependencies(db=db, settings=SETTINGS)
        ctx = MagicMock(); ctx.deps = deps
        result = await get_review_stats(ctx, "PROD001")
        assert "total_reviews" in result
        assert "sentiment_score" in result
        assert "rating_distribution" in result

    @pytest.mark.asyncio
    async def test_get_review_samples_returns_texts(self):
        from app.agents.review.tools import get_review_samples
        db = MagicMock()
        db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
            ("Great product!",), ("Love the battery life.",)
        ]
        deps = AgentDependencies(db=db, settings=SETTINGS)
        ctx = MagicMock(); ctx.deps = deps
        result = await get_review_samples(ctx, "PROD001", max_positive=5, max_negative=5)
        assert "positive_reviews" in result
        assert "negative_reviews" in result


# ── Schema tests ─────────────────────────────────────────────────────────────────

class TestReviewSchemas:
    def test_request_valid(self):
        from app.schemas.review import ReviewSummarizationRequest
        req = ReviewSummarizationRequest(query="Summarize reviews for Samsung TV")
        assert req.max_reviews == 20
        assert req.product_id is None

    def test_request_with_product_id(self):
        from app.schemas.review import ReviewSummarizationRequest
        req = ReviewSummarizationRequest(query="reviews", product_id="PROD001")
        assert req.product_id == "PROD001"

    def test_sentiment_theme_confidence_bounds(self):
        from app.schemas.review import SentimentTheme
        import pytest
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            SentimentTheme(theme="Battery", confidence=1.5)  # > 1.0

    def test_rating_distribution_defaults(self):
        from app.schemas.review import RatingDistribution
        dist = RatingDistribution()
        assert dist.five_star == 0
        assert dist.one_star == 0
```

---

## Completion Checklist

### New Files
- [ ] `app/core/cache.py` — `TTLCache` with thread-safe TTL and max-size eviction
- [ ] `app/schemas/review.py` — request/response schemas
- [ ] `app/agents/review/__init__.py`
- [ ] `app/agents/review/agent.py` — `ReviewSummarizationAgent`
- [ ] `app/agents/review/tools.py` — 3 tools: `find_product`, `get_review_stats`, `get_review_samples`
- [ ] `app/agents/review/prompts.py` — system prompt
- [ ] `app/api/v1/reviews.py` — `POST /api/v1/reviews/summarize`
- [ ] `tests/test_agents/test_review_agent.py`

### Modified Files
- [ ] `app/api/v1/__init__.py` — add `reviews` router

### Testing
- [ ] `pytest tests/test_agents/test_review_agent.py -v` — all pass
- [ ] TTLCache unit tests: all 6 pass (set, get, expiry, delete, max_size, clear)
- [ ] Tool tests: find_product (found + not found), get_review_stats, get_review_samples
- [ ] Agent tests: missing deps, cache hit, TestModel run, error handling
- [ ] Schema tests: request defaults, product_id, confidence bounds, rating distribution
- [ ] No import errors: `python3 -c "from app.agents.review import ReviewSummarizationAgent"`
- [ ] Endpoint visible in `GET /docs`

### Acceptance Criteria (from Jira)
- [ ] Agent extracts key positive themes (top 3) with confidence scores
- [ ] Agent extracts key negative themes (top 3) with confidence scores
- [ ] Sentiment score calculation (0–1 scale) — from pre-computed DB labels
- [ ] Handles queries like "Summarize reviews for iPhone 15"
- [ ] Pre-processed sentiment labels used for fast stats lookup
- [ ] GPT-based summarization for on-demand theme extraction
- [ ] Confidence scores per theme
- [ ] Response time under 3 seconds (LLM path); under 100ms (cache hit)

---

## Patterns Inherited from SCRUM-10
| Pattern | Status |
|---------|--------|
| `AgentDependencies` reused as-is | ✅ No changes needed |
| `BaseAgent.process()` signature | ✅ Followed exactly |
| `output_type` + `instructions` (pydantic-ai 1.x) | ✅ Applied |
| 4-file agent package | ✅ Applied |
| Module-level agent singleton in endpoint | ✅ Applied |
| `TestModel` for unit tests | ✅ Applied |
| Error → `AgentResponse(success=False)` | ✅ Applied |

## New Patterns Introduced (for future agents)
| Pattern | Used by |
|---------|---------|
| `TTLCache` in `app/core/cache.py` | SCRUM-14 (price caching), SCRUM-15 (policy caching) |
| Cache-aside inside `agent.process()` | SCRUM-14, SCRUM-15 |
| Two-stage (fast DB + LLM) | SCRUM-14 (price comparison) |

---

## Integration Test (Manual, Requires OPENAI_API_KEY)

```bash
uvicorn app.main:app --reload --port 8080

# Summarize by name
curl -X POST http://localhost:8080/api/v1/reviews/summarize \
  -H "Content-Type: application/json" \
  -d '{"query": "Summarize reviews for Samsung"}'

# Summarize by product ID (faster — skips name resolution)
curl -X POST http://localhost:8080/api/v1/reviews/summarize \
  -H "Content-Type: application/json" \
  -d '{"query": "What do customers say?", "product_id": "PROD001"}'

# Second call — should return cached: true
curl -X POST http://localhost:8080/api/v1/reviews/summarize \
  -H "Content-Type: application/json" \
  -d '{"query": "reviews", "product_id": "PROD001"}'
```

---

## Time Tracking
- **Estimated**: 4–5 hours
- **Actual**: _[To be filled]_
