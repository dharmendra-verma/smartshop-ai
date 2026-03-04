# SCRUM-61 — Inline Product Reviews Panel with AI Summarization on Product Listing Page

**Jira:** https://projecttracking.atlassian.net/browse/SCRUM-61
**Priority:** Medium
**Status:** In Progress

---

## Story

> As a shopper browsing the product listing page, I want to click a "Reviews" button on a product card and see its reviews expand inline below the grid — with a one-click AI summarization option, so that I can read real customer feedback and get an instant AI digest without leaving the product listing.

---

## Acceptance Criteria

### A — Reviews Button on Product Card
- [ ] Each product card shows a clickable "📝 N reviews" link/button below the star rating
- [ ] If 0 reviews, show "No reviews yet" (non-clickable)
- [ ] Clicking highlights the selected card and scrolls to the inline review panel

### B — Inline Review Panel (full-width, below the grid)
- [ ] Panel appears below the product grid when a product is selected
- [ ] Header: product name, average rating, total review count, "✕ Close" button
- [ ] Reviews in chronological order (newest first) — 10 per page with "Load More Reviews"
- [ ] Each review card: star rating, sentiment badge, date, review text
- [ ] Selecting a different product replaces the panel content

### C — AI Summarization Button
- [ ] "✨ Summarize Reviews with AI" button in panel header
- [ ] Calls `POST /api/v1/reviews/summarize` with `product_id`
- [ ] Renders AI summary inline (themes, rating distribution, narrative) above raw review list
- [ ] Summary cached in `st.session_state["review_summary_cache"]` — no re-call on re-open

### D — New Backend Endpoint
- [ ] `GET /api/v1/reviews/{product_id}?limit=10&offset=0` — paginated, sorted newest first
- [ ] 404 if product not found; empty list (not error) if no reviews
- [ ] Response: `{ product_id, product_name, reviews[], total, limit, offset }`

### E — Minimal UI Impact
- [ ] Product grid (3 columns) unchanged
- [ ] No modals, no page navigation, no sidebar changes
- [ ] Only one product's reviews shown at a time
- [ ] Floating chat widget unobstructed

---

## Current State

| Component | Status | Relevant Detail |
|-----------|--------|-----------------|
| `Review` model | ✅ | `review_id`, `product_id`, `rating`, `text`, `sentiment`, `review_date`; `idx_review_product_rating` index exists |
| `POST /api/v1/reviews/summarize` | ✅ | Returns full AI summary with themes, distribution, narrative |
| `summarize_reviews()` in `api_client.py` | ✅ | Accepts `product_id` directly |
| `render_review_summary()` in `review_display.py` | ✅ | Full summary UI component ready |
| `render_star_rating_html()` in `star_rating.py` | ✅ | Used for per-review star rendering |
| `product_card.py` | ✅ | Shows star + price; already has `review_count` slot (SCRUM-42) |
| `GET /api/v1/reviews/{product_id}` | ❌ **MISSING** | Needs to be created |
| `get_product_reviews()` in `api_client.py` | ❌ **MISSING** | Needs to be created |
| `render_review_panel()` UI component | ❌ **MISSING** | New component to be created |

---

## Technical Approach

### Layer 1 — New Backend Endpoint

Add `GET /api/v1/reviews/{product_id}` to `app/api/v1/reviews.py`:

```python
@router.get("/{product_id}", response_model=ReviewListResponse)
def list_product_reviews(
    product_id: str,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List raw reviews for a product, newest first."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Product '{product_id}' not found")

    query = (
        db.query(Review)
        .filter(Review.product_id == product_id)
        .order_by(Review.review_date.desc().nulls_last(), Review.review_id.desc())
    )
    total = query.count()
    reviews = query.offset(offset).limit(limit).all()

    return ReviewListResponse(
        product_id=product_id,
        product_name=product.name,
        average_rating=product.rating,
        reviews=[ReviewItem(**r.to_dict()) for r in reviews],
        total=total,
        limit=limit,
        offset=offset,
    )
```

Add `ReviewItem` and `ReviewListResponse` to `app/schemas/review.py`:

```python
class ReviewItem(BaseModel):
    review_id: int
    product_id: str
    rating: float
    text: str | None = None
    sentiment: str | None = None          # "positive" | "negative" | "neutral" | None
    review_date: str | None = None        # ISO date string

class ReviewListResponse(BaseModel):
    product_id: str
    product_name: str
    average_rating: float | None = None
    reviews: list[ReviewItem]
    total: int
    limit: int
    offset: int
```

### Layer 2 — API Client

Add to `app/ui/api_client.py`:

```python
def get_product_reviews(
    api_url: str,
    product_id: str,
    limit: int = 10,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Call GET /api/v1/reviews/{product_id}.
    Returns {"success": bool, "data": ReviewListResponse dict, "error": str | None}
    """
    return _get(
        f"{api_url}/api/v1/reviews/{product_id}",
        params={"limit": limit, "offset": offset},
    )
```

### Layer 3 — New UI Component `app/ui/components/review_panel.py`

New file encapsulating the entire inline review panel:

```python
"""Inline review panel component — SCRUM-61."""
import streamlit as st
from app.ui.components.star_rating import render_star_rating_html
from app.ui.components.review_display import render_review_summary

REVIEWS_PAGE_SIZE = 10

_SENTIMENT_BADGE = {
    "positive": '<span style="color:#2ca02c;font-weight:600;">✅ Positive</span>',
    "negative": '<span style="color:#d62728;font-weight:600;">❌ Negative</span>',
    "neutral":  '<span style="color:#666;font-weight:600;">➖ Neutral</span>',
}


def render_review_panel(product: dict, api_url: str) -> None:
    """
    Render the full-width inline review panel for a selected product.
    Reads/writes session state for pagination and summary cache.
    """
    product_id   = product["id"]
    product_name = product.get("name", "Product")
    avg_rating   = product.get("rating")
    review_count = product.get("review_count", 0)

    # ── Panel wrapper ──────────────────────────────────────────────
    st.markdown(
        '<div style="background:#f8f9fa;border-top:2px solid #1f77b4;'
        'border-radius:8px;padding:16px;margin-top:16px;">',
        unsafe_allow_html=True,
    )

    # ── Panel header row ───────────────────────────────────────────
    col_title, col_close = st.columns([5, 1])
    with col_title:
        stars_html = render_star_rating_html(avg_rating)
        st.markdown(
            f"### 📝 Reviews for **{product_name}**&nbsp;&nbsp;"
            f"{stars_html}&nbsp;&nbsp;"
            f'<span style="color:#666;font-size:0.9rem;">({review_count} reviews)</span>',
            unsafe_allow_html=True,
        )
    with col_close:
        if st.button("✕ Close Reviews", key=f"close_reviews_{product_id}"):
            st.session_state["selected_review_product_id"] = None
            st.session_state["review_panel_offset"]        = 0
            st.rerun()

    # ── AI Summarize button ────────────────────────────────────────
    summary_cache_key = f"review_summary_{product_id}"
    if summary_cache_key not in st.session_state:
        if st.button(
            "✨ Summarize Reviews with AI",
            key=f"summarize_{product_id}",
            type="secondary",
            use_container_width=True,
        ):
            with st.spinner("Asking AI to summarise all reviews…"):
                from app.ui.api_client import summarize_reviews
                result = summarize_reviews(
                    api_url,
                    query=f"Summarize customer reviews for {product_name}",
                    product_id=product_id,
                    max_reviews=50,
                )
            if result["success"]:
                st.session_state[summary_cache_key] = result["data"]
                st.rerun()
            else:
                st.error(f"Summarization failed: {result['error']}")
    else:
        # Render cached summary
        st.markdown("#### ✨ AI Review Summary")
        render_review_summary(st.session_state[summary_cache_key])
        if st.button(
            "🔄 Re-summarize",
            key=f"resummarise_{product_id}",
            help="Clear cached summary and fetch a fresh one",
        ):
            del st.session_state[summary_cache_key]
            st.rerun()

    st.divider()

    # ── Raw reviews list ───────────────────────────────────────────
    offset = st.session_state.get("review_panel_offset", 0)
    from app.ui.api_client import get_product_reviews
    result = get_product_reviews(api_url, product_id, limit=REVIEWS_PAGE_SIZE, offset=0)

    if not result["success"]:
        st.error(f"Could not load reviews: {result['error']}")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    data     = result["data"]
    reviews  = data.get("reviews", [])
    total    = data.get("total", 0)

    # Accumulate all loaded reviews in session state for "Load More"
    loaded_key = f"review_loaded_{product_id}"
    if loaded_key not in st.session_state:
        st.session_state[loaded_key] = reviews
    current_reviews = st.session_state[loaded_key]

    if not current_reviews:
        st.info("No reviews yet for this product.")
    else:
        st.caption(f"Showing {len(current_reviews)} of {total} reviews — newest first")
        for rev in current_reviews:
            _render_single_review(rev)

        # Load More
        if len(current_reviews) < total:
            if st.button(
                f"⬇️ Load More Reviews",
                key=f"more_reviews_{product_id}",
                use_container_width=True,
            ):
                next_offset = len(current_reviews)
                more = get_product_reviews(
                    api_url, product_id,
                    limit=REVIEWS_PAGE_SIZE, offset=next_offset,
                )
                if more["success"]:
                    st.session_state[loaded_key].extend(more["data"]["reviews"])
                    st.rerun()
        else:
            st.caption(f"✅ All {total} reviews loaded.")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_single_review(review: dict) -> None:
    """Render one review card with rating, sentiment, date, and text."""
    rating    = review.get("rating", 0)
    sentiment = (review.get("sentiment") or "").lower()
    date_str  = review.get("review_date", "")
    text      = review.get("text") or "_No review text provided._"

    badge_html = _SENTIMENT_BADGE.get(sentiment, "")
    stars_html = render_star_rating_html(rating)

    st.markdown(
        f'<div style="background:#fff;border:1px solid #e0e0e0;border-radius:8px;'
        f'padding:12px 16px;margin-bottom:8px;">'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">'
        f'{stars_html}&nbsp;{badge_html}'
        f'<span style="color:#aaa;font-size:0.8rem;margin-left:auto;">{date_str}</span>'
        f"</div>"
        f'<p style="margin:0;font-size:0.9rem;color:#333;">{text}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )
```

### Layer 4 — Product Card: "N reviews" Button

Modify `app/ui/components/product_card.py` — replace the current static review count display with a clickable button that sets `st.session_state["selected_review_product_id"]`:

```python
# Inside render_product_card(), after the star rating line:
review_count = product.get("review_count", 0)
product_id   = product.get("id", "")

if review_count and review_count > 0:
    is_selected = st.session_state.get("selected_review_product_id") == product_id
    btn_label   = f"{'📖' if is_selected else '📝'} {review_count} review{'s' if review_count != 1 else ''}"
    btn_style   = "primary" if is_selected else "secondary"
    if st.button(btn_label, key=f"show_reviews_{product_id}", type=btn_style,
                 use_container_width=True):
        if is_selected:
            # Toggle off
            st.session_state["selected_review_product_id"] = None
            st.session_state.pop(f"review_loaded_{product_id}", None)
        else:
            st.session_state["selected_review_product_id"] = product_id
            st.session_state.pop(f"review_loaded_{product_id}", None)  # reset on new selection
        st.rerun()
else:
    st.caption("No reviews yet")
```

### Layer 5 — Integrate Panel into `streamlit_app.py`

After `render_product_grid()` and before the "Load More" button block, add:

```python
# ── Inline review panel ──────────────────────────────────────────
selected_id = st.session_state.get("selected_review_product_id")
if selected_id:
    # Find the selected product dict from the loaded list
    selected_product = next(
        (p for p in st.session_state.get("products_list", []) if p["id"] == selected_id),
        None,
    )
    if selected_product:
        from app.ui.components.review_panel import render_review_panel
        render_review_panel(selected_product, api_url)
    else:
        st.session_state["selected_review_product_id"] = None
```

Add to `_init_state()` in `streamlit_app.py`:
```python
"selected_review_product_id": None,
"review_panel_offset": 0,
```

### Session State Keys Added

| Key | Type | Purpose |
|-----|------|---------|
| `selected_review_product_id` | `str \| None` | Which product's reviews are open |
| `review_panel_offset` | `int` | Pagination offset for raw reviews |
| `review_loaded_{product_id}` | `list[dict]` | Accumulated loaded reviews per product |
| `review_summary_{product_id}` | `dict` | Cached AI summary per product |

---

## File Map

| File | Action | What Changes |
|------|--------|-------------|
| `app/api/v1/reviews.py` | **MODIFY** | Add `GET /{product_id}` endpoint |
| `app/schemas/review.py` | **MODIFY** | Add `ReviewItem` and `ReviewListResponse` schemas |
| `app/ui/api_client.py` | **MODIFY** | Add `get_product_reviews()` function |
| `app/ui/components/review_panel.py` | **CREATE** | Full inline review panel component |
| `app/ui/components/product_card.py` | **MODIFY** | Replace static review count with clickable "N reviews" button |
| `app/ui/streamlit_app.py` | **MODIFY** | Add `selected_review_product_id` to `_init_state()`; render `review_panel` below grid |
| `app/ui/design_tokens.py` | **MODIFY (additive)** | Add `.review-card` CSS class |
| `tests/test_api/test_reviews.py` | **MODIFY** | Add tests for `GET /api/v1/reviews/{product_id}` |
| `tests/test_ui/test_review_panel.py` | **CREATE** | Unit tests for `_render_single_review()`, session state helpers |

---

## CSS Addition to `design_tokens.py`

```css
/* Inline Review Card */
.review-card {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 8px;
}
.sentiment-positive { color: #2ca02c; font-weight: 600; }
.sentiment-negative { color: #d62728; font-weight: 600; }
.sentiment-neutral  { color: #666;    font-weight: 600; }
```

---

## Test Requirements

**Modify `tests/test_api/test_reviews.py`** (~8 new tests):
```
test_get_reviews_returns_200_for_valid_product()
test_get_reviews_sorted_newest_first()
test_get_reviews_returns_404_for_unknown_product()
test_get_reviews_returns_empty_list_not_error_when_no_reviews()
test_get_reviews_pagination_limit()
test_get_reviews_pagination_offset()
test_get_reviews_response_has_total_and_product_name()
test_get_reviews_nulls_sorted_last()
```

**Create `tests/test_ui/test_review_panel.py`** (~6 new tests):
```
test_sentiment_badge_positive()
test_sentiment_badge_negative()
test_sentiment_badge_neutral()
test_sentiment_badge_unknown_returns_empty()
test_render_single_review_contains_rating_stars()
test_render_single_review_handles_missing_text()
```

**Modify `tests/test_ui/test_api_client.py`** (~3 new tests):
```
test_get_product_reviews_calls_correct_url()
test_get_product_reviews_passes_limit_and_offset()
test_get_product_reviews_returns_error_dict_on_failure()
```

**Expected new tests:** ~17
**Total after story:** ~358 (341 base + 17)

---

## Dependencies

- Depends on SCRUM-60 (single-page `streamlit_app.py` layout) ✅ — `render_review_panel` is injected below the product grid that SCRUM-60 creates
- Depends on SCRUM-42 (product_card.py compact layout) ✅ — review count slot already present
- `Review` model, `review_date` sort index already exist ✅
- `render_review_summary()` and `render_star_rating_html()` already exist ✅
- `summarize_reviews()` in `api_client.py` already exists ✅
- No new Python packages required

---

## Implementation Order

1. Backend: `app/schemas/review.py` — add `ReviewItem` + `ReviewListResponse`
2. Backend: `app/api/v1/reviews.py` — add `GET /{product_id}` endpoint
3. API client: `app/ui/api_client.py` — add `get_product_reviews()`
4. UI: `app/ui/components/review_panel.py` — create new component (largest piece)
5. UI: `app/ui/components/product_card.py` — add clickable "N reviews" button
6. UI: `app/ui/streamlit_app.py` — extend `_init_state()`, inject panel below grid
7. CSS: `app/ui/design_tokens.py` — add review card styles
8. Tests: API endpoint tests, review panel unit tests, api_client tests
9. Run full test suite
10. Run app and verify: click "N reviews" → panel opens below grid → "Summarize" → summary appears inline

## Notes for Dev Agent

- **Toggle behaviour**: Clicking "📝 N reviews" on an already-selected product closes the panel (set `selected_review_product_id = None`). Clicking a different product's button replaces the content.
- **Summary caching**: Cache key is `review_summary_{product_id}` in `st.session_state`. The "Re-summarize" button deletes the key and re-runs. Do NOT automatically invalidate on page load — the cache should survive Streamlit re-runs within the same browser session.
- **Review list accumulation**: `review_loaded_{product_id}` starts fresh whenever a new product is selected (clear the key in the toggle handler). "Load More" appends to this key.
- **`render_review_panel` is pure Streamlit** — no HTML injection like `floating_chat.py`. Keep it simple with `st.markdown`, `st.button`, `st.divider`.
- **Order in `streamlit_app.py`**: `render_product_grid()` → review panel → "Load More Products" button → floating chat → footer. The review panel must appear between the grid and the Load More button so the page flow is natural.
