# Story: SCRUM-12 — Create Streamlit Chat UI for User Interaction

## Story Overview
- **Epic**: SCRUM-3 (Phase 2: Agent Development)
- **Story Points**: 5
- **Priority**: Medium
- **Jira Link**: https://projecttracking.atlassian.net/browse/SCRUM-12
- **Complexity**: Medium — modify existing scaffold, add API client layer, wire to live endpoints
- **Estimated Duration**: 3–4 hours

---

## Dependencies
- SCRUM-9 ✅ — `GET /api/v1/products` live
- SCRUM-10 ✅ — `POST /api/v1/recommendations` live
- SCRUM-11 ✅ — `POST /api/v1/reviews/summarize` live
- `app/ui/streamlit_app.py` ✅ — existing scaffold with 4-module sidebar structure

---

## What Already Exists (Do NOT recreate)
| File | Status | Notes |
|------|--------|-------|
| `app/ui/streamlit_app.py` | ✅ Exists | Scaffold with sidebar, 4 placeholder modules — **MODIFY** |
| `app/ui/__init__.py` | ✅ Exists | Empty, keep as-is |
| `app/ui/components/` | ✅ Exists | Empty dir — populate with component files |
| `Dockerfile.streamlit` | ✅ Exists | Runs on port 8501, API_URL env var set to `http://api:8080` |
| `docker-compose.yml` | ✅ Exists | Streamlit wired to FastAPI service |

---

## Key Observations from Existing Code

1. **API URL bug**: Default is `http://localhost:8000` but FastAPI runs on port **8080**. Fix to `http://localhost:8080`.
2. **Chat module** has `st.chat_input()` and session state but returns a hardcoded placeholder string — no API call at all.
3. **Product Search, Price Comparison, Review Summarization** all show `st.info("🚧 ...coming soon!")`.
4. **Sidebar nav labels** don't match Jira spec — update to: "AI Chat Assistant", "Product Search & Recommendations", "Review Summarization", "Pricing Insights".
5. **No API client layer** — HTTP calls will be scattered without one. Needs `app/ui/api_client.py`.

---

## Architectural Decisions

### Decision 1: API Client Module (`app/ui/api_client.py`)
All HTTP calls to FastAPI live in one place. The Streamlit app imports from this module — never calls `requests` directly. Benefits:
- Single place to update base URL or add auth headers later
- Easy to mock for testing
- Consistent error handling (timeout, 500, network failure)

### Decision 2: Reusable UI Components (`app/ui/components/`)
Repeated UI patterns (product cards, sentiment bars, star ratings, error boxes) extracted to component functions. Keeps `streamlit_app.py` readable and under 300 lines.

### Decision 3: Client-Side Intent Routing in Chat (Temporary until SCRUM-16)
SCRUM-16 (Orchestrator) doesn't exist yet. For this story, the chat module uses simple keyword detection to route queries:
- Contains "review", "summarize", "what do customers say", "opinions" → `POST /api/v1/reviews/summarize`
- Everything else → `POST /api/v1/recommendations`

This is explicitly temporary — documented with a `# TODO SCRUM-16: replace with orchestrator` comment. SCRUM-13 ("Integrate agents with UI") will refine this routing once the orchestrator exists.

### Decision 4: Fix API URL — Read from Environment Variable
In Docker (`docker-compose.yml`), `API_URL=http://api:8080` is injected via environment. Streamlit should read this with `os.getenv("API_URL", "http://localhost:8080")` as the default, not a hardcoded string. This makes the app work both locally and in Docker without changing code.

### Decision 5: No Unit Tests for Streamlit UI
Streamlit components aren't meaningfully unit-testable (they render to a browser context). API client functions in `api_client.py` are pure Python and ARE testable — add lightweight tests for those only.

---

## File Structure

```
app/ui/
├── __init__.py                  ✅ exists (empty)
├── streamlit_app.py             ← MODIFY: replace placeholders with live API calls
├── api_client.py                ← CREATE: all HTTP calls to FastAPI
└── components/
    ├── __init__.py              ← CREATE (empty)
    ├── product_card.py          ← CREATE: product card and grid rendering
    ├── review_display.py        ← CREATE: sentiment themes, rating distribution
    └── chat_helpers.py          ← CREATE: intent router, message formatting

tests/
└── test_ui/
    ├── __init__.py              ← CREATE
    └── test_api_client.py       ← CREATE: mock-based tests for API client functions
```

---

## Implementation Tasks

---

### Task 1: Create API Client Module

**File**: `app/ui/api_client.py`

**Purpose**: All HTTP communication with FastAPI. Returns typed dicts — never raises. Always returns `{"success": bool, "data": ..., "error": str | None}`.

```python
"""HTTP client for SmartShop AI FastAPI backend.

All functions return a result dict: {"success": bool, "data": any, "error": str | None}
Never raises — all exceptions are caught and returned as error responses.
"""

import logging
import requests
from typing import Any

logger = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 10  # seconds


def _get(url: str, params: dict | None = None) -> dict[str, Any]:
    """Internal GET helper."""
    try:
        r = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return {"success": True, "data": r.json(), "error": None}
    except requests.exceptions.ConnectionError:
        return {"success": False, "data": None, "error": "Cannot connect to backend. Is FastAPI running?"}
    except requests.exceptions.Timeout:
        return {"success": False, "data": None, "error": "Request timed out. Please try again."}
    except requests.exceptions.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        return {"success": False, "data": None, "error": f"API error: {detail}"}
    except Exception as e:
        logger.error("Unexpected error in GET %s: %s", url, e)
        return {"success": False, "data": None, "error": f"Unexpected error: {str(e)}"}


def _post(url: str, payload: dict) -> dict[str, Any]:
    """Internal POST helper."""
    try:
        r = requests.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        return {"success": True, "data": r.json(), "error": None}
    except requests.exceptions.ConnectionError:
        return {"success": False, "data": None, "error": "Cannot connect to backend. Is FastAPI running?"}
    except requests.exceptions.Timeout:
        return {"success": False, "data": None, "error": "Request timed out. Please try again."}
    except requests.exceptions.HTTPError as e:
        detail = e.response.json().get("detail", str(e)) if e.response else str(e)
        return {"success": False, "data": None, "error": f"API error: {detail}"}
    except Exception as e:
        logger.error("Unexpected error in POST %s: %s", url, e)
        return {"success": False, "data": None, "error": f"Unexpected error: {str(e)}"}


# ── Public API ──────────────────────────────────────────────────────────────────

def health_check(api_url: str) -> bool:
    """Returns True if the backend is reachable and healthy."""
    result = _get(f"{api_url}/health")
    return result["success"]


def get_recommendations(
    api_url: str,
    query: str,
    max_results: int = 5,
    max_price: float | None = None,
    min_price: float | None = None,
    category: str | None = None,
    min_rating: float | None = None,
) -> dict[str, Any]:
    """
    Call POST /api/v1/recommendations.
    Returns {"success": bool, "data": RecommendationResponse dict, "error": str | None}
    """
    payload = {"query": query, "max_results": max_results}
    if max_price is not None:
        payload["max_price"] = max_price
    if min_price is not None:
        payload["min_price"] = min_price
    if category:
        payload["category"] = category
    if min_rating is not None:
        payload["min_rating"] = min_rating
    return _post(f"{api_url}/api/v1/recommendations", payload)


def summarize_reviews(
    api_url: str,
    query: str,
    product_id: str | None = None,
    max_reviews: int = 20,
) -> dict[str, Any]:
    """
    Call POST /api/v1/reviews/summarize.
    Returns {"success": bool, "data": ReviewSummarizationResponse dict, "error": str | None}
    """
    payload = {"query": query, "max_reviews": max_reviews}
    if product_id:
        payload["product_id"] = product_id
    return _post(f"{api_url}/api/v1/reviews/summarize", payload)


def search_products(
    api_url: str,
    category: str | None = None,
    brand: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    page: int = 1,
    page_size: int = 12,
) -> dict[str, Any]:
    """
    Call GET /api/v1/products with filters.
    Returns {"success": bool, "data": ProductListResponse dict, "error": str | None}
    """
    params: dict = {"page": page, "page_size": page_size}
    if category and category != "All":
        params["category"] = category
    if brand:
        params["brand"] = brand
    if min_price:
        params["min_price"] = min_price
    if max_price:
        params["max_price"] = max_price
    if min_rating:
        params["min_rating"] = min_rating
    return _get(f"{api_url}/api/v1/products", params=params)
```

---

### Task 2: Create UI Components

**File**: `app/ui/components/__init__.py` — empty init

---

**File**: `app/ui/components/product_card.py`

```python
"""Product card and grid rendering components."""

import streamlit as st


def render_product_card(product: dict) -> None:
    """Render a single product as a styled card."""
    with st.container(border=True):
        st.markdown(f"**{product.get('name', 'Unknown')}**")

        col1, col2 = st.columns(2)
        with col1:
            price = product.get("price")
            st.metric("Price", f"${float(price):.2f}" if price else "N/A")
        with col2:
            rating = product.get("rating")
            st.metric("Rating", f"{'⭐' * round(rating)} ({rating:.1f})" if rating else "N/A")

        if product.get("brand"):
            st.caption(f"Brand: {product['brand']} · Category: {product.get('category', '')}")

        stock = product.get("stock")
        if stock is not None:
            if stock > 10:
                st.success(f"✅ In Stock ({stock} units)")
            elif stock > 0:
                st.warning(f"⚠️ Low Stock ({stock} units)")
            else:
                st.error("❌ Out of Stock")

        if product.get("reason"):
            st.info(f"💡 {product['reason']}")

        if product.get("relevance_score") is not None:
            score = product["relevance_score"]
            st.progress(score, text=f"Relevance: {score:.0%}")


def render_product_grid(products: list[dict], cols: int = 3) -> None:
    """Render a grid of product cards."""
    if not products:
        st.info("No products found matching your criteria.")
        return

    columns = st.columns(cols)
    for i, product in enumerate(products):
        with columns[i % cols]:
            render_product_card(product)
```

---

**File**: `app/ui/components/review_display.py`

```python
"""Review summarization display components."""

import streamlit as st


def render_sentiment_themes(themes: list[dict], label: str, emoji: str) -> None:
    """Render a list of sentiment themes with confidence bars."""
    st.markdown(f"**{emoji} {label}**")
    if not themes:
        st.caption("No themes identified.")
        return
    for theme in themes:
        confidence = theme.get("confidence", 0)
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(confidence, text=theme.get("theme", ""))
        with col2:
            st.caption(f"{confidence:.0%}")
        if theme.get("example_quote"):
            st.caption(f'_"{theme["example_quote"]}"_')


def render_rating_distribution(dist: dict) -> None:
    """Render star rating distribution as a horizontal bar chart."""
    st.markdown("**⭐ Rating Distribution**")
    labels = ["5★", "4★", "3★", "2★", "1★"]
    keys = ["five_star", "four_star", "three_star", "two_star", "one_star"]
    total = sum(dist.get(k, 0) for k in keys) or 1
    for label, key in zip(labels, keys):
        count = dist.get(key, 0)
        pct = count / total
        st.progress(pct, text=f"{label}  ({count})")


def render_review_summary(data: dict) -> None:
    """Render a full review summarization response."""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Reviews", data.get("total_reviews", 0))
    with col2:
        score = data.get("sentiment_score", 0)
        st.metric("Sentiment Score", f"{score:.2f}/1.0")
    with col3:
        avg = data.get("average_rating", 0)
        st.metric("Avg Rating", f"{avg:.1f}/5.0")

    if data.get("cached"):
        st.caption("⚡ Served from cache")

    st.divider()
    col_pos, col_neg = st.columns(2)
    with col_pos:
        render_sentiment_themes(data.get("positive_themes", []), "Positive Themes", "✅")
    with col_neg:
        render_sentiment_themes(data.get("negative_themes", []), "Negative Themes", "❌")

    st.divider()
    render_rating_distribution(data.get("rating_distribution", {}))

    st.divider()
    st.markdown("**📝 Overall Summary**")
    st.write(data.get("overall_summary", "No summary available."))
```

---

**File**: `app/ui/components/chat_helpers.py`

```python
"""Chat intent routing and message formatting helpers."""

# Keyword sets for client-side intent detection
# TODO SCRUM-16: Replace with POST /api/v1/chat once the Orchestrator is live.
_REVIEW_KEYWORDS = {
    "review", "reviews", "summarize", "summary", "opinions",
    "what do customers", "what people say", "feedback", "ratings",
    "pros and cons", "pros cons",
}

_RECOMMENDATION_KEYWORDS = {
    "recommend", "suggest", "find", "show me", "best", "budget",
    "under $", "cheap", "affordable", "top", "popular", "buy",
    "looking for", "want to buy", "gift",
}


def detect_intent(query: str) -> str:
    """
    Detect user intent from a chat query.

    Returns: "review" | "recommendation" | "unknown"

    TODO SCRUM-16: Remove when Orchestrator endpoint is live.
    """
    q = query.lower()
    if any(kw in q for kw in _REVIEW_KEYWORDS):
        return "review"
    if any(kw in q for kw in _RECOMMENDATION_KEYWORDS):
        return "recommendation"
    # Default to recommendation for product-sounding queries
    return "recommendation"


def format_recommendation_message(data: dict) -> str:
    """Format a recommendation API response as markdown for chat display."""
    recs = data.get("recommendations", [])
    if not recs:
        return "I couldn't find any products matching your query. Try broadening your search."

    lines = [f"Here are my top recommendations for **\"{data.get('query', '')}\"**:\n"]
    for i, rec in enumerate(recs, 1):
        price = float(rec.get("price", 0))
        rating = rec.get("rating")
        stars = f"{'⭐' * round(rating)}" if rating else ""
        lines.append(
            f"**{i}. {rec['name']}** — ${price:.2f} {stars}\n"
            f"   _{rec.get('reason', '')}_\n"
        )

    summary = data.get("reasoning_summary", "")
    if summary:
        lines.append(f"\n💡 {summary}")
    return "\n".join(lines)


def format_review_message(data: dict) -> str:
    """Format a review summarization response as markdown for chat display."""
    product_name = data.get("product_name", "this product")
    total = data.get("total_reviews", 0)
    avg = data.get("average_rating", 0)
    score = data.get("sentiment_score", 0)

    pos = data.get("positive_themes", [])
    neg = data.get("negative_themes", [])

    lines = [
        f"**Review Summary: {product_name}**",
        f"_{total} reviews · {avg:.1f}/5.0 avg · {score:.0%} positive sentiment_\n",
    ]
    if pos:
        lines.append("✅ **Top Positives:**")
        for t in pos:
            lines.append(f"  • {t['theme']} ({t['confidence']:.0%} confidence)")
    if neg:
        lines.append("\n❌ **Top Concerns:**")
        for t in neg:
            lines.append(f"  • {t['theme']} ({t['confidence']:.0%} confidence)")

    summary = data.get("overall_summary", "")
    if summary:
        lines.append(f"\n📝 {summary}")
    return "\n".join(lines)
```

---

### Task 3: Rewrite `streamlit_app.py`

**File**: `app/ui/streamlit_app.py` — **full replacement**

```python
"""SmartShop AI — Streamlit User Interface."""

import os
import streamlit as st

from app.ui.api_client import (
    health_check,
    get_recommendations,
    summarize_reviews,
    search_products,
)
from app.ui.components.product_card import render_product_grid
from app.ui.components.review_display import render_review_summary
from app.ui.components.chat_helpers import (
    detect_intent,
    format_recommendation_message,
    format_review_message,
)

# ── Config ──────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SmartShop AI",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1f77b4; }
    .sub-header  { font-size: 1.1rem; color: #666; margin-bottom: 1.5rem; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p class="main-header">🛒 SmartShop</p>', unsafe_allow_html=True)
    st.caption("AI-Powered Shopping Assistant")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🤖 AI Chat Assistant",
            "🔍 Product Search & Recommendations",
            "⭐ Review Summarization",
            "💰 Pricing Insights",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.subheader("⚙️ Settings")
    # Read from env var (Docker) or allow manual override
    default_url = os.getenv("API_URL", "http://localhost:8080")
    api_url = st.text_input("API URL", default_url)

    # Backend status indicator
    if health_check(api_url):
        st.success("✅ Backend connected")
    else:
        st.error("❌ Backend unreachable")
        st.caption(f"Ensure FastAPI is running at {api_url}")

# ── Page: AI Chat Assistant ──────────────────────────────────────────────────────
if page == "🤖 AI Chat Assistant":
    st.header("AI Shopping Assistant")
    st.caption(
        "Ask me to find products or summarize reviews. "
        "Try: _'Show me laptops under $800'_ or _'Summarize reviews for Samsung'_"
    )

    # Initialise chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "👋 Hi! I'm your AI shopping assistant. I can help you:\n\n"
                    "- 🔍 **Find products** — _'Recommend budget headphones under $100'_\n"
                    "- ⭐ **Summarize reviews** — _'What do customers say about Sony speakers?'_\n\n"
                    "What are you looking for today?"
                ),
            }
        ]

    # Display history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask me about products or reviews..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Route and call API
        # TODO SCRUM-16: Replace detect_intent() with POST /api/v1/chat orchestrator call
        intent = detect_intent(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                if intent == "review":
                    result = summarize_reviews(api_url, query=prompt)
                    if result["success"]:
                        reply = format_review_message(result["data"])
                    else:
                        reply = f"⚠️ {result['error']}"
                else:
                    result = get_recommendations(api_url, query=prompt, max_results=5)
                    if result["success"]:
                        reply = format_recommendation_message(result["data"])
                    else:
                        reply = f"⚠️ {result['error']}"
            st.markdown(reply)
        st.session_state.messages.append({"role": "assistant", "content": reply})

    # Clear chat button
    if st.button("🗑️ Clear Chat", type="secondary"):
        st.session_state.messages = []
        st.rerun()

# ── Page: Product Search & Recommendations ──────────────────────────────────────
elif page == "🔍 Product Search & Recommendations":
    st.header("Product Search & Recommendations")

    tab_search, tab_recommend = st.tabs(["🔍 Filter Search", "🤖 AI Recommendations"])

    # Tab 1: Structured filter search
    with tab_search:
        col1, col2, col3 = st.columns(3)
        with col1:
            category = st.selectbox(
                "Category",
                ["All", "smartphones", "laptops", "headphones", "speakers", "tablets", "cameras"],
            )
        with col2:
            min_price = st.number_input("Min Price ($)", min_value=0, value=0, step=50)
        with col3:
            max_price = st.number_input("Max Price ($)", min_value=0, value=2000, step=50)

        col4, col5 = st.columns([2, 1])
        with col4:
            brand = st.text_input("Brand (optional)", placeholder="e.g. Samsung, Apple")
        with col5:
            min_rating = st.slider("Min Rating", 0.0, 5.0, 0.0, step=0.5)

        if st.button("Search Products", type="primary"):
            with st.spinner("Searching..."):
                result = search_products(
                    api_url,
                    category=category if category != "All" else None,
                    brand=brand or None,
                    min_price=min_price or None,
                    max_price=max_price or None,
                    min_rating=min_rating or None,
                    page_size=12,
                )
            if result["success"]:
                data = result["data"]
                st.success(f"Found {data['total']} products (showing {len(data['items'])})")
                render_product_grid(data["items"], cols=3)
            else:
                st.error(result["error"])

    # Tab 2: AI recommendation
    with tab_recommend:
        nl_query = st.text_input(
            "Describe what you're looking for",
            placeholder="e.g. 'best wireless headphones for gym use under $150'",
        )
        max_results = st.slider("Number of recommendations", 1, 10, 5)

        if st.button("Get AI Recommendations", type="primary"):
            if not nl_query.strip():
                st.warning("Please enter a search query.")
            else:
                with st.spinner("Finding the best matches for you..."):
                    result = get_recommendations(
                        api_url, query=nl_query, max_results=max_results
                    )
                if result["success"]:
                    data = result["data"]
                    st.success(f"Found {data['total_found']} recommendation(s)")
                    if data.get("reasoning_summary"):
                        st.info(f"💡 {data['reasoning_summary']}")
                    render_product_grid(data["recommendations"], cols=3)
                else:
                    st.error(result["error"])

# ── Page: Review Summarization ──────────────────────────────────────────────────
elif page == "⭐ Review Summarization":
    st.header("Review Summarization")
    st.caption("Get AI-powered summaries of what customers say about any product.")

    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input(
            "Product name or question",
            placeholder="e.g. 'Summarize reviews for Sony WH-1000XM5'",
        )
    with col2:
        product_id = st.text_input("Product ID (optional)", placeholder="e.g. PROD001")

    max_reviews = st.slider("Reviews to analyse", 5, 50, 20, step=5)

    if st.button("Summarize Reviews", type="primary"):
        if not query.strip():
            st.warning("Please enter a product name or question.")
        else:
            with st.spinner("Analysing customer reviews..."):
                result = summarize_reviews(
                    api_url,
                    query=query,
                    product_id=product_id.strip() or None,
                    max_reviews=max_reviews,
                )
            if result["success"]:
                data = result["data"]
                st.subheader(f"Reviews for: **{data.get('product_name', query)}**")
                render_review_summary(data)
            else:
                st.error(result["error"])

# ── Page: Pricing Insights ──────────────────────────────────────────────────────
elif page == "💰 Pricing Insights":
    st.header("Pricing Insights")
    st.caption("Compare prices and find the best deals.")

    st.info(
        "🚧 **Coming in SCRUM-14** — Price Comparison Agent will provide real-time "
        "pricing data, deal alerts, and side-by-side comparisons. "
        "Use **Product Search & Recommendations** in the meantime to explore products by price range."
    )

    # Preview of what it will look like
    with st.expander("Preview: What Pricing Insights will show"):
        import pandas as pd
        st.dataframe(
            pd.DataFrame({
                "Product": ["Phone A", "Phone B", "Phone C"],
                "Our Price": ["$299", "$349", "$399"],
                "Avg Market": ["$319", "$339", "$419"],
                "Deal Score": ["🔥 Good", "✅ Fair", "⭐ Best"],
                "In Stock": ["Yes", "Yes", "Low"],
            }),
            use_container_width=True,
        )

# ── Footer ───────────────────────────────────────────────────────────────────────
st.divider()
st.caption("SmartShop AI v1.0.0 · Powered by pydantic-ai & FastAPI")
```

---

### Task 4: Write API Client Tests

**File**: `tests/test_ui/__init__.py` — empty init

**File**: `tests/test_ui/test_api_client.py`

```python
"""Tests for the API client functions (mock-based, no real HTTP)."""

import pytest
from unittest.mock import patch, MagicMock
import requests

from app.ui.api_client import (
    health_check,
    get_recommendations,
    summarize_reviews,
    search_products,
)


def make_mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    return mock


class TestHealthCheck:
    def test_healthy_backend(self):
        with patch("app.ui.api_client.requests.get") as mock_get:
            mock_get.return_value = make_mock_response({"status": "healthy"})
            assert health_check("http://localhost:8080") is True

    def test_unreachable_backend(self):
        with patch("app.ui.api_client.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError
            assert health_check("http://localhost:8080") is False

    def test_timeout(self):
        with patch("app.ui.api_client.requests.get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout
            assert health_check("http://localhost:8080") is False


class TestGetRecommendations:
    def test_success(self):
        payload = {"query": "phones", "recommendations": [], "total_found": 0, "reasoning_summary": ""}
        with patch("app.ui.api_client.requests.post") as mock_post:
            mock_post.return_value = make_mock_response(payload)
            result = get_recommendations("http://localhost:8080", "phones")
        assert result["success"] is True
        assert result["data"]["query"] == "phones"

    def test_connection_error_returns_error_dict(self):
        with patch("app.ui.api_client.requests.post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectionError
            result = get_recommendations("http://localhost:8080", "phones")
        assert result["success"] is False
        assert "connect" in result["error"].lower()

    def test_optional_filters_included(self):
        with patch("app.ui.api_client.requests.post") as mock_post:
            mock_post.return_value = make_mock_response({})
            get_recommendations("http://x", "phones", max_price=500.0, category="smartphones")
            call_args = mock_post.call_args
            body = call_args.kwargs.get("json") or call_args.args[1]
            assert body["max_price"] == 500.0
            assert body["category"] == "smartphones"


class TestSummarizeReviews:
    def test_success_without_product_id(self):
        payload = {"product_id": "P1", "product_name": "Test", "total_reviews": 10,
                   "sentiment_score": 0.8, "average_rating": 4.2,
                   "rating_distribution": {}, "positive_themes": [],
                   "negative_themes": [], "overall_summary": "Good.", "cached": False}
        with patch("app.ui.api_client.requests.post") as mock_post:
            mock_post.return_value = make_mock_response(payload)
            result = summarize_reviews("http://localhost:8080", "Review Samsung")
        assert result["success"] is True

    def test_product_id_included_when_provided(self):
        with patch("app.ui.api_client.requests.post") as mock_post:
            mock_post.return_value = make_mock_response({})
            summarize_reviews("http://x", "review", product_id="PROD001")
            body = mock_post.call_args.kwargs.get("json") or mock_post.call_args.args[1]
            assert body["product_id"] == "PROD001"

    def test_http_error_returns_error_dict(self):
        with patch("app.ui.api_client.requests.post") as mock_post:
            err = requests.exceptions.HTTPError(response=MagicMock())
            err.response.json.return_value = {"detail": "Not found"}
            mock_post.return_value.raise_for_status.side_effect = err
            result = summarize_reviews("http://x", "review")
        assert result["success"] is False


class TestSearchProducts:
    def test_success(self):
        payload = {"items": [], "total": 0, "page": 1, "page_size": 12, "pages": 0}
        with patch("app.ui.api_client.requests.get") as mock_get:
            mock_get.return_value = make_mock_response(payload)
            result = search_products("http://localhost:8080", category="smartphones")
        assert result["success"] is True

    def test_all_category_not_sent_as_filter(self):
        with patch("app.ui.api_client.requests.get") as mock_get:
            mock_get.return_value = make_mock_response({})
            search_products("http://x", category="All")
            params = mock_get.call_args.kwargs.get("params") or {}
            assert "category" not in params


class TestChatHelpers:
    def test_review_intent_detected(self):
        from app.ui.components.chat_helpers import detect_intent
        assert detect_intent("Summarize reviews for iPhone") == "review"
        assert detect_intent("What do customers say about this?") == "review"

    def test_recommendation_intent_detected(self):
        from app.ui.components.chat_helpers import detect_intent
        assert detect_intent("Recommend budget laptops under $500") == "recommendation"
        assert detect_intent("Find me good headphones") == "recommendation"

    def test_format_recommendation_empty(self):
        from app.ui.components.chat_helpers import format_recommendation_message
        msg = format_recommendation_message({"recommendations": [], "query": "phones"})
        assert "couldn't find" in msg.lower()

    def test_format_review_message(self):
        from app.ui.components.chat_helpers import format_review_message
        data = {
            "product_name": "Test Phone",
            "total_reviews": 100,
            "average_rating": 4.2,
            "sentiment_score": 0.8,
            "positive_themes": [{"theme": "Battery life", "confidence": 0.85}],
            "negative_themes": [],
            "overall_summary": "Great phone overall.",
        }
        msg = format_review_message(data)
        assert "Test Phone" in msg
        assert "Battery life" in msg
```

---

## Completion Checklist

### New Files
- [ ] `app/ui/api_client.py` — HTTP client (health, recommendations, reviews, products)
- [ ] `app/ui/components/__init__.py`
- [ ] `app/ui/components/product_card.py` — product card + grid
- [ ] `app/ui/components/review_display.py` — sentiment themes, rating dist, summary
- [ ] `app/ui/components/chat_helpers.py` — intent router, message formatters
- [ ] `tests/test_ui/__init__.py`
- [ ] `tests/test_ui/test_api_client.py`

### Modified Files
- [ ] `app/ui/streamlit_app.py` — full replacement (fix port, wire live APIs, real UI)

### Testing
- [ ] `pytest tests/test_ui/ -v` — all tests pass
- [ ] Health check: True/False for connected/disconnected backend
- [ ] Recommendations: success, connection error, optional filters
- [ ] Reviews: success, product_id inclusion, HTTP error
- [ ] Products: success, "All" category not sent as filter
- [ ] Chat helpers: intent detection (review + recommendation), message formatters

### Acceptance Criteria (from Jira)
- [ ] Streamlit chat interface implemented (`st.chat_message`, `st.chat_input`)
- [ ] Message history maintained in session state
- [ ] User input text box with submit button
- [ ] Agent response display with markdown formatting
- [ ] Loading indicators (`st.spinner`) during API calls
- [ ] Error messages displayed gracefully (connection errors, API errors)
- [ ] Sidebar with module navigation (4 modules)
- [ ] Product Search filters (category, price, brand, rating)
- [ ] AI Recommendations tab with NL query
- [ ] Review Summarization page with themed output and confidence bars
- [ ] Pricing Insights placeholder with SCRUM-14 note

---

## Patterns Established for SCRUM-13 (End-to-End Integration)
| Pattern | Reused by |
|---------|-----------|
| `api_client.py` functions | SCRUM-13 — add `chat()` function for orchestrator |
| `detect_intent()` in `chat_helpers.py` | SCRUM-13/16 — replaced by real orchestrator call |
| Component functions (product_card, review_display) | SCRUM-13, SCRUM-18 (UI polish) |

---

## Integration Test (Manual)

```bash
# Terminal 1: Start FastAPI
uvicorn app.main:app --reload --port 8080

# Terminal 2: Start Streamlit
streamlit run app/ui/streamlit_app.py

# Open http://localhost:8501
# Test chat: "Show me budget phones under $300"
# Test chat: "Summarize reviews for Samsung"
# Test Product Search: category=smartphones, max_price=500
# Test Review Summarization page directly
```

---

## Time Tracking
- **Estimated**: 3–4 hours
- **Actual**: _[To be filled]_
