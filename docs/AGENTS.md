# Agent Documentation

SmartShop AI uses a multi-agent architecture built on **pydantic-ai 1.61.0** with **gpt-4o-mini**. Each agent inherits from `BaseAgent` and returns `AgentResponse`. The `Orchestrator` classifies user intent and routes to the appropriate specialist.

---

## Architecture Overview

```
User query
    │
    ▼
┌──────────────┐
│  Orchestrator │
│  (router)     │
└──────┬───────┘
       │ IntentClassifier
       ▼
┌──────────────────────────────────────────────────┐
│  recommendation │ review │ price │ policy │ general │
│  Agent          │ Agent  │ Agent │ Agent  │ Agent   │
└──────────────────────────────────────────────────┘
       │
       ▼
  AgentResponse { success, data, error, metadata }
```

---

## BaseAgent

**File:** `app/agents/base.py`

```python
class AgentResponse(BaseModel):
    success: bool
    data: Dict[str, Any]
    error: str | None = None
    metadata: Dict[str, Any] = {}

class BaseAgent(ABC):
    def __init__(self, name: str)
    @abstractmethod
    async def process(self, query: str, context: Dict[str, Any]) -> AgentResponse
```

All agents follow this contract. `context["deps"]` provides `AgentDependencies` (DB session + settings).

---

## AgentDependencies

**File:** `app/agents/dependencies.py`

```python
@dataclass
class AgentDependencies:
    db: Session
    settings: Settings

    @classmethod
    def from_db(cls, db: Session) -> "AgentDependencies":
        return cls(db=db, settings=get_settings())
```

Injected into pydantic-ai tool functions via `RunContext[AgentDependencies]`. Tools access `ctx.deps.db` for queries and `ctx.deps.settings` for config.

---

## RecommendationAgent

**File:** `app/agents/recommendation/agent.py`
**Intent:** `recommendation`, `comparison`
**Endpoint:** `POST /api/v1/recommendations`

### Purpose

Searches the product catalog based on natural language queries, applies filters, and ranks products by relevance.

### Tools

| Tool | Description |
|------|-------------|
| `search_products_by_filters` | Filter by category, brand, price range, rating; limit 50; ordered by rating DESC |
| `get_product_details` | Fetch full product by ID |
| `get_categories` | List distinct categories |

### Output Schema

```python
class _RecommendationOutput(BaseModel):
    recommendations: list[_ProductResult]  # product_id, relevance_score (0-1), reason
    reasoning_summary: str
```

### Processing Pipeline

1. Check `context["deps"]` — fail if missing
2. Check LLM cache (`get_cached_llm_response`)
3. Build enriched query with structured hints (max_price, min_price, category, min_rating)
4. Run pydantic-ai agent with `UsageLimits(request_limit=15)`
5. Hydrate recommendations from DB, drop hallucinated product IDs
6. Cache response via `set_cached_llm_response`
7. Return `AgentResponse` sorted by `relevance_score` DESC

### Error Handling

- `RateLimitError` → `AgentRateLimitError` + `record_failure()`
- `Timeout` → `AgentTimeoutError` + `record_failure()`
- Generic → log + `record_failure()` + return error response

---

## ReviewSummarizationAgent

**File:** `app/agents/review/agent.py`
**Intent:** `review`
**Endpoint:** `POST /api/v1/reviews/summarize`

### Purpose

Summarizes customer reviews for a product — extracts sentiment themes, computes rating distribution, generates a narrative summary.

### Tools

| Tool | Description |
|------|-------------|
| `find_product` | Resolve product by name or ID (fuzzy match) |
| `get_review_stats` | Rating distribution + sentiment counts (DB-only, no LLM) |
| `get_review_samples` | Recent review texts by sentiment (truncated to 200 chars) |

### Output Schema

```python
class _ReviewSummaryOutput(BaseModel):
    product_id: str
    product_name: str
    total_reviews: int
    sentiment_score: float        # 0-1 (positive ratio)
    average_rating: float
    rating_distribution: dict     # {one_star, two_star, ..., five_star}
    positive_themes: list[_ThemeResult]  # theme, confidence, example_quote
    negative_themes: list[_ThemeResult]
    overall_summary: str
```

### Dual Caching

- **Agent-level cache:** Keyed by `review_summary:{product_id}`, fast for repeated product lookups
- **LLM cache:** Keyed by `agent_name:query_hash`, 24h TTL

---

## PriceComparisonAgent

**File:** `app/agents/price/agent.py`
**Intent:** `price`
**Endpoint:** `POST /api/v1/price/compare`

### Purpose

Compares product prices across multiple retailers (Amazon, BestBuy, Walmart) and identifies best deals.

### Tools

| Tool | Description |
|------|-------------|
| `search_products_by_name` | Fuzzy match on product name, fallback to brand prefix |
| `get_competitor_prices` | Fetch prices from `MockPricingService`, cached 1 hour in `PriceCache` |

### Output Schema

```python
class _ComparisonOutput(BaseModel):
    products: list[_ProductComparison]  # product_id, our_price, competitor_prices, best_price, savings_pct
    best_deal: str
    recommendation: str
```

### Price Cache

- **Backend:** `PriceCache` (Redis primary → TTLCache fallback)
- **TTL:** 3600s (1 hour)
- **Key prefix:** `price:`
- **Source:** `MockPricingService` — deterministic seed-based variation per product/source

---

## PolicyAgent (FAISS RAG)

**File:** `app/agents/policy/agent.py`
**Intent:** `policy`
**Endpoint:** `POST /api/v1/policy/ask`

### Purpose

Answers store policy questions using Retrieval-Augmented Generation. Searches a FAISS vector index of policy documents and synthesizes answers grounded in retrieved chunks.

### Tools

| Tool | Description |
|------|-------------|
| `retrieve_policy_sections` | Semantic search via `PolicyVectorStore.search(query, k)` |

### Output Schema

```python
class _PolicyAnswer(BaseModel):
    answer: str
    sources: list[str]     # Policy type names cited
    confidence: str        # "high", "medium", "low"
```

### Vector Store Details

- **Embedding model:** `text-embedding-3-small` (1536 dimensions)
- **Index type:** `faiss.IndexFlatIP` (inner product on L2-normalized vectors = cosine similarity)
- **Persistence:** `data/embeddings/faiss_index.bin` + `faiss_metadata.json`
- **Load strategy:** Load from disk if file exists and policy count matches; rebuild otherwise
- **Fallback:** DB keyword search if vector store unavailable

### Dependencies Extension

```python
@dataclass
class PolicyDependencies(AgentDependencies):
    vector_store: Any = None  # PolicyVectorStore
```

---

## IntentClassifier

**File:** `app/agents/orchestrator/intent_classifier.py`
**Used by:** Orchestrator (internal, no direct endpoint)

### Purpose

Classifies user queries into one of six intent types and extracts structured entities.

### Output Schema

```python
class _IntentResult(BaseModel):
    intent: IntentType       # recommendation | comparison | review | policy | price | general
    confidence: float        # 0.0–1.0
    product_name: str | None
    category: str | None
    max_price: float | None
    min_price: float | None
    reasoning: str
```

### Configuration

- `UsageLimits(request_limit=5)` — lower than specialized agents
- **Fallback on error:** Returns `IntentType.GENERAL` with `confidence=0.0`

---

## GeneralResponseAgent

**File:** `app/agents/orchestrator/general_agent.py`
**Intent:** `general` (fallback)

### Purpose

Handles queries that don't match any specialized intent. Provides brief helpful responses and redirects toward product search, recommendations, reviews, price comparison, or policy questions.

### Configuration

- **No tools** — pure LLM response
- `UsageLimits(request_limit=5)`
- **Graceful degradation:** On exception, returns hardcoded message: *"I'm here to help with product recommendations, reviews, price comparisons, and store policies."*

---

## Orchestrator

**File:** `app/agents/orchestrator/orchestrator.py`
**Endpoint:** `POST /api/v1/chat`

### Purpose

Routes user queries to the appropriate specialized agent. Manages session context, circuit breakers, and multi-level fallback.

### Registry

```python
{
    "recommendation": RecommendationAgent(),
    "review":         ReviewSummarizationAgent(),
    "price":          PriceComparisonAgent(),
    "general":        GeneralResponseAgent(),
    "policy":         PolicyAgent(),  # optional
}
```

### `handle()` Pipeline

1. `IntentClassifier.classify(query)` → `_IntentResult`
2. Enrich context with extracted entities (category, max_price, etc.)
3. Map intent to agent key (`"comparison"` → `"recommendation"` with `compare_mode: True`)
4. Check circuit breaker → fallback to `"general"` if open
5. Call `agent.process(query, context)`
6. On success: record circuit breaker success, cache via `query_cache`
7. On exception: record failure, try `query_cache.get_cached_response()`, fallback to general agent

### Singleton

```python
get_orchestrator()    # Lazy init
reset_orchestrator()  # For tests
```

---

## CircuitBreaker

**File:** `app/agents/orchestrator/circuit_breaker.py`

Prevents cascading failures by temporarily disabling failing agents.

### State Machine

```
CLOSED ──(3 failures)──▶ OPEN ──(30s timeout)──▶ HALF_OPEN
   ▲                                                  │
   └──────────(success)───────────────────────────────┘
                                                      │
OPEN ◀──────────(failure)─────────────────────────────┘
```

| Parameter | Default |
|-----------|---------|
| `failure_threshold` | 3 |
| `recovery_timeout` | 30 seconds |

### Methods

- `is_available()` → `bool` — Can this agent accept requests?
- `record_success()` → Reset to CLOSED
- `record_failure()` → Increment failures; transition to OPEN at threshold

---

## LLM Cache Integration

All four specialized agents (Recommendation, Review, Price, Policy) share the same caching pattern:

```python
# Before agent.run()
cached = get_cached_llm_response(self.name, query)
if cached:
    cached["metadata"]["from_llm_cache"] = True
    return cached

# After successful agent.run()
set_cached_llm_response(self.name, query, response)
```

- **Cache key:** `{agent_name}:{SHA256(normalized_query)[:16]}`
- **TTL:** 24 hours
- **Backend:** Redis primary → TTLCache fallback

---

## Summary Table

| Agent | Intent | Tools | Output | Request Limit |
|-------|--------|-------|--------|---------------|
| RecommendationAgent | recommendation, comparison | search_products_by_filters, get_product_details, get_categories | recommendations + reasoning | 15 |
| ReviewSummarizationAgent | review | find_product, get_review_stats, get_review_samples | themes + summary + sentiment | 15 |
| PriceComparisonAgent | price | search_products_by_name, get_competitor_prices | price comparison + best deal | 15 |
| PolicyAgent | policy | retrieve_policy_sections (FAISS) | answer + sources + confidence | 15 |
| IntentClassifier | (internal) | none | intent + entities | 5 |
| GeneralResponseAgent | general | none | brief answer | 5 |
| Orchestrator | all (router) | none | routes to specialist | — |
