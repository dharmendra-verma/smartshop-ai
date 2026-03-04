# SCRUM-43 — Implement Virtual Scrolling / Infinite Load to Display More Than 12 Products

**Jira:** https://projecttracking.atlassian.net/browse/SCRUM-43
**Priority:** Medium
**Status:** In Progress

---

## Story

> As a shopper browsing the product catalogue, I want to be able to scroll through the full product range without a hard page limit, so that I can discover more products easily without clicking through pages.

---

## Acceptance Criteria

- [ ] The product listing page no longer hard-caps at 12 items
- [ ] Virtual/progressive loading: next batch of products loads as user requests more (infinite scroll equivalent for Streamlit)
- [ ] A loading skeleton/spinner is shown while the next batch of products is being fetched
- [ ] Scroll position is preserved if the user navigates to a product detail and returns (back navigation)
- [ ] Initial page load performance is not degraded — first 24 products render within existing budgets
- [ ] The total product count is displayed at the top of the listing (e.g. "Showing 1–24 of 340 products")
- [ ] Works correctly on mobile and desktop viewports
- [ ] Accessibility: list is navigable via keyboard and screen-reader friendly

---

## Current State

**`streamlit_app.py` line 196–201** — hard-coded `page_size=12`:
```python
result = search_products(
    api_url,
    category=category if category != "All" else None,
    brand=brand or None,
    page_size=12,         # ← hard cap — to be removed
)
```

**`app/ui/api_client.py`** — `search_products` already supports `page` and `page_size` params ✅

**FastAPI `/api/v1/products`** — already supports full offset pagination:
- `page: int` (default 1), `page_size: int` (default 20, max 100)
- Response: `{ items, total, page, page_size, pages }` ✅

**`app/ui/components/product_card.py`** — `render_product_grid(products, cols=3)` renders any list ✅

**Key constraint:** Streamlit does not support true client-side virtual DOM windowing (`react-window` style). The Streamlit-appropriate pattern is **session-state–based "Load More" pagination**, which progressively appends batches to a cumulative list stored in `st.session_state`.

---

## Technical Approach

### Strategy: Session-State Progressive Loading ("Load More")

1. Store accumulated products in `st.session_state["search_products"]`
2. Store current page in `st.session_state["search_page"]`
3. Store last query/filter params in `st.session_state["search_params"]`
4. On first search: reset state, fetch page 1 (batch size 24)
5. On "Load More" click: fetch next page, append to accumulated list, re-render
6. Show `"Showing X–Y of Z products"` header
7. Hide "Load More" button when all pages loaded

### Batch Size
Change from `page_size=12` → `page_size=24` (configurable constant `PRODUCTS_BATCH_SIZE = 24`)

### State Management

```python
# Session state keys
SEARCH_PRODUCTS_KEY = "search_products_list"     # list[dict] — accumulated
SEARCH_PAGE_KEY     = "search_page"              # int — current page
SEARCH_TOTAL_KEY    = "search_total"             # int — total from API
SEARCH_PAGES_KEY    = "search_total_pages"       # int — total pages from API
SEARCH_PARAMS_KEY   = "search_params"            # dict — last query params
```

---

## File Map

| File | Action | What Changes |
|------|--------|-------------|
| `streamlit_app.py` | MODIFY | Replace one-shot search with progressive-load pattern; add "Load More" button; add product count header |
| `app/ui/api_client.py` | MODIFY | `search_products`: increase default `page_size` to 24; add `offset`-based variant comment |
| `app/ui/design_tokens.py` | MODIFY (additive) | Add `.product-count-header` CSS class |
| `tests/test_ui/test_api_client.py` | MODIFY | Add tests for page/page_size params in search_products |

---

## Code Snippets

### Constants (top of `streamlit_app.py`)

```python
PRODUCTS_BATCH_SIZE = 24   # products per page load
```

### Session State helpers

```python
def _init_search_state():
    """Initialise search session state keys."""
    if "search_products_list" not in st.session_state:
        st.session_state["search_products_list"] = []
    if "search_page" not in st.session_state:
        st.session_state["search_page"] = 0
    if "search_total" not in st.session_state:
        st.session_state["search_total"] = 0
    if "search_total_pages" not in st.session_state:
        st.session_state["search_total_pages"] = 0
    if "search_params" not in st.session_state:
        st.session_state["search_params"] = {}

def _reset_search_state(params: dict):
    """Reset state when a new search is triggered."""
    st.session_state["search_products_list"] = []
    st.session_state["search_page"] = 0
    st.session_state["search_total"] = 0
    st.session_state["search_total_pages"] = 0
    st.session_state["search_params"] = params
```

### Updated search block in `tab_search` section of `streamlit_app.py`

```python
_init_search_state()

if st.button("Search Products", type="primary"):
    params = {
        "category": category if category != "All" else None,
        "brand": brand or None,
    }
    _reset_search_state(params)
    with st.spinner("Searching..."):
        result = search_products(
            api_url,
            category=params["category"],
            brand=params["brand"],
            page=1,
            page_size=PRODUCTS_BATCH_SIZE,
        )
    if result["success"]:
        data = result["data"]
        st.session_state["search_products_list"] = data["items"]
        st.session_state["search_page"] = 1
        st.session_state["search_total"] = data["total"]
        st.session_state["search_total_pages"] = data["pages"]
    else:
        st.error(result["error"])

# Display accumulated results
products = st.session_state.get("search_products_list", [])
total    = st.session_state.get("search_total", 0)
cur_page = st.session_state.get("search_page", 0)
tot_pages = st.session_state.get("search_total_pages", 0)

if products:
    shown = len(products)
    st.markdown(
        f'<p class="product-count-header">Showing <strong>1–{shown}</strong> of '
        f'<strong>{total}</strong> products</p>',
        unsafe_allow_html=True,
    )
    render_product_grid(products, cols=3)

    # "Load More" button — only shown if more pages exist
    if cur_page < tot_pages:
        if st.button("⬇️ Load More Products", use_container_width=True):
            next_page = cur_page + 1
            params = st.session_state.get("search_params", {})
            with st.spinner(f"Loading more products..."):
                result = search_products(
                    api_url,
                    category=params.get("category"),
                    brand=params.get("brand"),
                    page=next_page,
                    page_size=PRODUCTS_BATCH_SIZE,
                )
            if result["success"]:
                data = result["data"]
                st.session_state["search_products_list"].extend(data["items"])
                st.session_state["search_page"] = next_page
                st.rerun()
            else:
                st.error(result["error"])
    elif cur_page > 0 and cur_page >= tot_pages:
        st.success(f"✅ All {total} products loaded.")
```

### New CSS in `design_tokens.py`

```css
/* Product count header */
.product-count-header {
    font-size: 0.9rem;
    color: #555;
    margin-bottom: 12px;
}
```

---

## Test Requirements

**Modify:** `tests/test_ui/test_api_client.py` (~5 new tests):
```
test_search_products_default_page_is_1()
test_search_products_passes_page_size()
test_search_products_passes_page_param()
test_search_products_passes_category()
test_search_products_passes_brand()
```

**Expected new tests:** ~5
**Total after story:** ~292 (after SCRUM-42 which adds ~12 → from 287 base)

> Note: If SCRUM-42 is done first (adds ~12 → 299), then SCRUM-43 adds ~5 → ~304.
> If done independently from base 287: 287 + 5 = ~292.

---

## Dependencies

- Depends on FastAPI `/api/v1/products` pagination already implemented (SCRUM-9) ✅
- Depends on `search_products` in `api_client.py` already supporting `page`/`page_size` ✅
- No new Python packages required
- Should be implemented **after** SCRUM-41 and SCRUM-42 (both modify `streamlit_app.py`/`product_card.py`) to avoid merge conflicts

---

## Out of Scope

- Traditional pagination navigation (replaces it with progressive load)
- Product filtering/sorting changes
- URL state management for bookmarkable scroll position (follow-up story)
- React-window true virtual DOM rendering (not applicable in Streamlit)
