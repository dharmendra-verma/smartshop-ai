# API Reference

SmartShop AI exposes a RESTful JSON API on `http://localhost:8000`. All agent endpoints accept JSON bodies and return JSON responses. A Swagger UI is available at `/docs`.

---

## Global Headers

| Header | Direction | Description |
|--------|-----------|-------------|
| `Content-Type: application/json` | Request | Required for POST endpoints |
| `X-Request-Id` | Response | 8-char UUID added by `RequestIdMiddleware` |
| `Content-Encoding: gzip` | Response | Applied when body > 1 KB |
| `X-Process-Time-Ms` | Response | Server-side latency in milliseconds |

---

## Products — `/api/v1/products`

### GET `/api/v1/products/categories`

Return sorted list of distinct product categories.

**Response:** `string[]`

```json
["Electronics", "Home & Garden", "Sports & Outdoors"]
```

---

### GET `/api/v1/products`

List products with optional filtering and pagination.

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | Page number (min 1) |
| `page_size` | int | 20 | Items per page (1–100) |
| `category` | string | — | Case-insensitive substring filter |
| `brand` | string | — | Case-insensitive substring filter on name/brand |

**Response:**

```json
{
  "items": [
    {
      "id": "SP0001",
      "name": "Maxi Phone v95346",
      "description": "High-performance smartphone...",
      "price": 774.39,
      "brand": "TechCo",
      "category": "smartphone",
      "stock": 157,
      "rating": 4.2,
      "review_count": 45,
      "image_url": "https://...",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 20,
  "pages": 3
}
```

---

### GET `/api/v1/products/{product_id}`

Fetch a single product by ID.

**Success:** `200` — ProductResponse object (same shape as list item)

**Error:** `404` — `{"detail": "Product 'X' not found"}`

---

## Recommendations — `/api/v1/recommendations`

### POST `/api/v1/recommendations`

AI-powered product recommendations via `RecommendationAgent`.

**Request:**

```json
{
  "query": "budget smartphone under $500 with good battery",
  "max_results": 5,
  "max_price": 500,
  "min_price": 200,
  "category": "smartphone",
  "min_rating": 4.0
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `query` | string | yes | — | 3–500 chars |
| `max_results` | int | no | 5 | 1–20 |
| `max_price` | float | no | — | >= 0 |
| `min_price` | float | no | — | >= 0 |
| `category` | string | no | — | max 100 chars |
| `min_rating` | float | no | — | 0.0–5.0 |

**Response:**

```json
{
  "query": "budget smartphone under $500...",
  "recommendations": [
    {
      "id": "SP0012",
      "name": "Budget Phone X",
      "price": 349.99,
      "brand": "TechCo",
      "category": "smartphone",
      "rating": 4.3,
      "stock": 80,
      "image_url": "https://...",
      "relevance_score": 0.92,
      "reason": "Meets budget, excellent battery life reviews"
    }
  ],
  "total_found": 3,
  "reasoning_summary": "Found 3 smartphones under $500...",
  "agent": "recommendation-agent"
}
```

**Error:** `500` — `{"detail": "..."}` on agent failure

---

## Reviews — `/api/v1/reviews`

### POST `/api/v1/reviews/summarize`

AI review summarization via `ReviewSummarizationAgent`.

**Request:**

```json
{
  "query": "What do customers think about the Samsung Galaxy?",
  "product_id": null,
  "max_reviews": 20
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `query` | string | yes | — | 3–500 chars |
| `product_id` | string | no | — | max 20 chars, skips name resolution |
| `max_reviews` | int | no | 20 | 5–50 |

**Response:**

```json
{
  "product_id": "SP0005",
  "product_name": "Samsung Galaxy S24",
  "total_reviews": 245,
  "sentiment_score": 0.78,
  "average_rating": 4.3,
  "rating_distribution": {
    "one_star": 5, "two_star": 12, "three_star": 28,
    "four_star": 95, "five_star": 105
  },
  "positive_themes": [
    {"theme": "Battery life", "confidence": 0.9, "example_quote": "Lasts all day..."}
  ],
  "negative_themes": [
    {"theme": "Price", "confidence": 0.7, "example_quote": "A bit expensive..."}
  ],
  "overall_summary": "Customers largely praise the Galaxy S24...",
  "cached": false,
  "agent": "review-summarization-agent"
}
```

---

### GET `/api/v1/reviews/{product_id}`

List raw reviews for a product (newest first).

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `limit` | int | 10 | 1–50 |
| `offset` | int | 0 | Pagination offset |

**Response:**

```json
{
  "product_id": "SP0005",
  "product_name": "Samsung Galaxy S24",
  "average_rating": 4.3,
  "reviews": [
    {
      "review_id": 1234,
      "product_id": "SP0005",
      "rating": 5.0,
      "text": "Amazing phone...",
      "sentiment": "positive",
      "review_date": "2025-01-20"
    }
  ],
  "total": 245,
  "limit": 10,
  "offset": 0
}
```

**Error:** `404` — Product not found

---

## Price Comparison — `/api/v1/price`

### POST `/api/v1/price/compare`

Cross-retailer price comparison via `PriceComparisonAgent`.

**Request:**

```json
{
  "query": "Compare Samsung Galaxy S24 vs Google Pixel 8",
  "max_results": 4
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `query` | string | yes | — | 3–500 chars |
| `max_results` | int | no | 4 | 1–10 |

**Response:**

```json
{
  "query": "Compare Samsung Galaxy S24 vs Google Pixel 8",
  "products": [
    {
      "product_id": "SP0005",
      "name": "Samsung Galaxy S24",
      "our_price": 799.99,
      "competitor_prices": [
        {"source": "Amazon", "price": 749.99, "is_best": true},
        {"source": "BestBuy", "price": 789.99, "is_best": false},
        {"source": "Walmart", "price": 759.99, "is_best": false}
      ],
      "best_price": 749.99,
      "best_source": "Amazon",
      "savings_pct": 6.25,
      "rating": 4.3,
      "brand": "Samsung",
      "category": "smartphone",
      "is_cached": false
    }
  ],
  "best_deal": "Samsung Galaxy S24",
  "recommendation": "The Galaxy S24 offers the best value...",
  "total_compared": 2,
  "agent": "price-comparison-agent"
}
```

**Caching:** Competitor prices cached for 1 hour (Redis → TTLCache fallback).

---

## Policy Q&A — `/api/v1/policy`

### POST `/api/v1/policy/ask`

FAISS RAG-powered policy Q&A via `PolicyAgent`.

**Request:**

```json
{
  "query": "What is the return policy for electronics?",
  "k": 3
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `query` | string | yes | — | 3–500 chars |
| `k` | int | no | 3 | 1–10, top-k chunks to retrieve |

**Response:**

```json
{
  "query": "What is the return policy for electronics?",
  "answer": "Electronics can be returned within 30 days...",
  "sources": ["returns", "exchanges"],
  "confidence": "high",
  "agent": "policy-agent"
}
```

**RAG pipeline:** Query → `text-embedding-3-small` → FAISS `IndexFlatIP` (cosine similarity on L2-normed vectors) → top-k chunks → GPT-4o-mini synthesis.

---

## Chat — `/api/v1/chat`

### POST `/api/v1/chat`

Unified intent-routed chat with session memory via `Orchestrator`.

**Request:**

```json
{
  "message": "I want a smartphone under $500",
  "session_id": null,
  "max_results": 5
}
```

| Field | Type | Required | Default | Constraints |
|-------|------|----------|---------|-------------|
| `message` | string | yes | — | 1–1000 chars |
| `session_id` | string | no | — | Null → new session created |
| `max_results` | int | no | 5 | 1–20 |

**Response:**

```json
{
  "session_id": "a1b2c3d4-...",
  "message": "I want a smartphone under $500",
  "intent": "recommendation",
  "confidence": 0.95,
  "entities": {
    "product_name": null,
    "category": "smartphone",
    "max_price": 500.0,
    "min_price": null
  },
  "agent_used": "recommendation-agent",
  "response": { "...agent-specific data..." },
  "success": true,
  "error": null
}
```

**Intent routing:**

| Intent | Agent |
|--------|-------|
| `recommendation` | RecommendationAgent |
| `comparison` | PriceComparisonAgent (compare mode) |
| `review` | ReviewSummarizationAgent |
| `price` | PriceComparisonAgent |
| `policy` | PolicyAgent |
| `general` | GeneralResponseAgent (fallback) |

**Session:** 30-min TTL, sliding window of last 10 conversation pairs.

---

### DELETE `/api/v1/chat/session/{session_id}`

Clear conversation history for a session.

**Response:** `204 No Content`

---

## Health — `/health`

### GET `/health`

```json
{
  "status": "healthy",
  "service": "SmartShop AI",
  "version": "1.0.0",
  "timestamp": "2026-03-05T13:45:20Z"
}
```

### GET `/health/metrics`

P50/P95 latency per endpoint (rolling 200-sample window).

```json
{
  "metrics": {
    "/api/v1/recommendations": {"p50_ms": 145.3, "p95_ms": 890.2},
    "/api/v1/chat": {"p50_ms": 200.1, "p95_ms": 1200.5}
  }
}
```

### GET `/health/alerts`

Component failure counts (rolling 5-min window).

```json
{
  "alerts": {
    "recommendation-agent": 2,
    "database": 0
  }
}
```

---

## Error Response Format

All errors are wrapped by `ErrorHandlerMiddleware`:

```json
{
  "error": "rate_limit",
  "detail": "I'm experiencing high demand. Please try again in a moment.",
  "request_id": "a1b2c3d4"
}
```

| Exception | HTTP Status | Error Type |
|-----------|-------------|------------|
| `AgentRateLimitError` | 429 | `rate_limit` |
| `AgentTimeoutError` | 504 | `timeout` |
| `DatabaseError` | 503 | `service_unavailable` |
| `SmartShopError` | 500 | `internal_error` |
| Unhandled | 500 | `internal_error` |
