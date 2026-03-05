# SCRUM-62 — Inline Product Comparison: Select Two Products, Compare Side by Side

## Story
**As a** shopper browsing the product listing page,
**I want** to select any two products and compare them side by side,
**So that** I can quickly evaluate differences and make a more informed purchase decision.

**Jira:** https://projecttracking.atlassian.net/browse/SCRUM-62
**Status:** In Progress ✅ (verified via Jira API)

---

## Acceptance Criteria
### A — Product Selection
- [ ] Each product card displays a "Compare" toggle button
- [ ] Max 2 products selectable — selecting a third auto-deselects the oldest (FIFO)
- [ ] Selected cards are visually highlighted (border ring)
- [ ] Persistent "Compare (N/2)" action bar appears below the grid once ≥1 product selected
- [ ] User can deselect via toggle again or via "×" in the action bar

### B — Comparison Table
- [ ] Clicking "Compare Products" in action bar opens inline table below the action bar
- [ ] Table: field-label column on left, one column per product
- [ ] Fields: image, name, price, category, brand, rating, review count, description
- [ ] Rows where values differ are highlighted (light yellow `#fffbcc`)
- [ ] "✕ Close Comparison" dismisses the table and clears selection
- [ ] If < 2 selected, show "Please select a second product to compare"

### C — UX & Performance
- [ ] No new API calls — data comes from `st.session_state["search_products_list"]`
- [ ] Selecting/deselecting does not re-render the product grid
- [ ] Table scrollable on small viewports

---

## Dependencies
- SCRUM-61 (product_card.py already has toggle button pattern — reuse `on_click` closure approach)
- SCRUM-43 (`search_products_list` in session state — data source for comparison)

---

## Current State

### `product_card.py` (lines 83–103)
Already has a reviews toggle button using `on_click` closure + `st.session_state`. The compare button follows the same pattern — add a second button below the reviews button.

```python
# Current pattern (reviews toggle):
def _toggle_reviews(pid=product_id, currently_selected=is_selected):
    if currently_selected:
        st.session_state["selected_review_product_id"] = None
    else:
        st.session_state["selected_review_product_id"] = pid
st.button(btn_label, key=f"show_reviews_{product_id}", on_click=_toggle_reviews)
```

### `streamlit_app.py` session state (lines 82–94)
```python
def _init_search_state():
    for key, default in [
        ("search_products_list", []),
        ("search_page", 0),
        ...
        ("selected_review_product_id", None),
        ("review_panel_offset", 0),
        # ADD:
        ("compare_product_ids", []),
        ("compare_open", False),
    ]:
```

### Layout order in `streamlit_app.py` (lines 149–183)
```
review_panel (above grid if selected)
render_product_grid(products, cols=3)
[ADD] compare_action_bar + compare_panel (below grid, above Load More)
Load More button
```

---

## Technical Approach

### 1. Session State Keys (add to `_init_search_state`)
| Key | Type | Purpose |
|-----|------|---------|
| `compare_product_ids` | `list[str]` | Up to 2 product IDs selected for comparison |
| `compare_open` | `bool` | Whether the comparison table is visible |

### 2. New File: `app/ui/components/compare_panel.py`

```python
"""Inline product comparison panel — SCRUM-62."""
import streamlit as st


def _get_field(product: dict, key: str) -> str:
    """Return a display string for a product field."""
    val = product.get(key)
    if val is None:
        return "—"
    if key == "price":
        return f"${float(val):.2f}"
    if key == "rating":
        return f"{'⭐' * round(float(val))} ({float(val):.1f})"
    if key == "review_count":
        return str(val)
    return str(val)


COMPARE_FIELDS = [
    ("image",        "Image"),
    ("name",         "Name"),
    ("price",        "Price"),
    ("brand",        "Brand"),
    ("category",     "Category"),
    ("rating",       "Rating"),
    ("review_count", "Reviews"),
    ("description",  "Description"),
]


def render_compare_panel(product_a: dict, product_b: dict) -> None:
    """Render a full-width side-by-side comparison table for two products."""
    st.markdown(
        '<div class="compare-panel-header">📊 Product Comparison</div>',
        unsafe_allow_html=True,
    )

    rows_html = ""
    for field_key, field_label in COMPARE_FIELDS:
        if field_key == "image":
            img_a = product_a.get("image_url") or "https://placehold.co/80x60"
            img_b = product_b.get("image_url") or "https://placehold.co/80x60"
            rows_html += (
                f'<tr class="compare-row">'
                f'<td class="compare-label">{field_label}</td>'
                f'<td class="compare-cell"><img src="{img_a}" class="compare-thumb"/></td>'
                f'<td class="compare-cell"><img src="{img_b}" class="compare-thumb"/></td>'
                f'</tr>'
            )
        else:
            val_a = _get_field(product_a, field_key)
            val_b = _get_field(product_b, field_key)
            diff_class = "compare-row-diff" if val_a != val_b else "compare-row"
            rows_html += (
                f'<tr class="{diff_class}">'
                f'<td class="compare-label">{field_label}</td>'
                f'<td class="compare-cell">{val_a}</td>'
                f'<td class="compare-cell">{val_b}</td>'
                f'</tr>'
            )

    name_a = product_a.get("name", "Product A")
    name_b = product_b.get("name", "Product B")

    table_html = f"""
<div class="compare-panel">
  <table class="compare-table">
    <thead>
      <tr>
        <th class="compare-label">Field</th>
        <th class="compare-cell compare-col-header">{name_a}</th>
        <th class="compare-cell compare-col-header">{name_b}</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
  <p class="compare-diff-legend">🟡 Highlighted rows indicate differences</p>
</div>
"""
    st.markdown(table_html, unsafe_allow_html=True)
```

### 3. Modify `product_card.py` — Add Compare Button

Add below the existing reviews button (after line 103):

```python
# Compare toggle button (SCRUM-62)
compare_ids: list = st.session_state.get("compare_product_ids", [])
is_comparing = product_id in compare_ids

def _toggle_compare(pid=product_id):
    ids: list = list(st.session_state.get("compare_product_ids", []))
    if pid in ids:
        ids.remove(pid)
        st.session_state["compare_open"] = False  # reset panel if deselected
    else:
        if len(ids) >= 2:
            ids.pop(0)  # FIFO: remove oldest selection
        ids.append(pid)
    st.session_state["compare_product_ids"] = ids

compare_label = "✅ Comparing" if is_comparing else "⚖️ Compare"
compare_type  = "primary" if is_comparing else "secondary"
st.button(
    compare_label,
    key=f"compare_{product_id}",
    type=compare_type,
    use_container_width=True,
    on_click=_toggle_compare,
)
```

### 4. Modify `streamlit_app.py` — Action Bar + Panel Injection

Add to `_init_search_state`:
```python
("compare_product_ids", []),
("compare_open", False),
```

After `render_product_grid(products, cols=3)` and before the Load More button:
```python
# Compare action bar (SCRUM-62)
compare_ids = st.session_state.get("compare_product_ids", [])
if compare_ids:
    compare_products = [p for p in products if p.get("id") in compare_ids]
    n = len(compare_ids)

    bar_col1, bar_col2, bar_col3 = st.columns([4, 2, 2])
    with bar_col1:
        names = " vs ".join(p.get("name", "?")[:30] for p in compare_products)
        st.markdown(
            f'<div class="compare-action-bar">⚖️ Comparing: <strong>{names}</strong></div>',
            unsafe_allow_html=True,
        )
    with bar_col2:
        if st.button(f"Compare Products ({n}/2)", type="primary",
                     disabled=(n < 2), use_container_width=True):
            st.session_state["compare_open"] = True
            st.rerun()
    with bar_col3:
        if st.button("✕ Clear Selection", use_container_width=True):
            st.session_state["compare_product_ids"] = []
            st.session_state["compare_open"] = False
            st.rerun()

    # Comparison table
    if st.session_state.get("compare_open") and len(compare_products) == 2:
        from app.ui.components.compare_panel import render_compare_panel
        with st.container():
            render_compare_panel(compare_products[0], compare_products[1])
            if st.button("✕ Close Comparison", use_container_width=True):
                st.session_state["compare_open"] = False
                st.rerun()
    elif st.session_state.get("compare_open") and len(compare_products) < 2:
        st.info("Please select a second product to compare.")
```

### 5. Add CSS to `design_tokens.py`

```python
/* ── Compare Panel (SCRUM-62) ─────────────────────────────────── */
.compare-panel {{
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-radius: {RADIUS_MD};
    padding: {SPACE_MD};
    margin: {SPACE_MD} 0;
    overflow-x: auto;
}}
.compare-panel-header {{
    font-size: 1.1rem;
    font-weight: 700;
    color: {COLOR_BRAND_PRIMARY};
    margin-bottom: {SPACE_SM};
}}
.compare-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}}
.compare-label {{
    font-weight: 600;
    color: #444;
    background: #f0f4f8;
    padding: 8px 12px;
    width: 20%;
    border: 1px solid #e0e0e0;
    vertical-align: top;
}}
.compare-cell {{
    padding: 8px 12px;
    border: 1px solid #e0e0e0;
    width: 40%;
    vertical-align: top;
}}
.compare-col-header {{
    font-weight: 700;
    color: {COLOR_BRAND_PRIMARY};
    background: #eaf3fb;
}}
.compare-row-diff td {{
    background: #fffbcc !important;
}}
.compare-thumb {{
    width: 80px;
    height: 60px;
    object-fit: contain;
    border-radius: {RADIUS_SM};
}}
.compare-diff-legend {{
    font-size: 0.8rem;
    color: #888;
    margin-top: {SPACE_SM};
}}
.compare-action-bar {{
    font-size: 0.95rem;
    color: #333;
    padding: 10px 0;
}}
/* Selected card highlight */
```

---

## File Map

| File | Action | Change |
|------|--------|--------|
| `app/ui/components/compare_panel.py` | **CREATE** | Full comparison table component |
| `app/ui/components/product_card.py` | **MODIFY** | Add compare toggle button (after reviews button) |
| `app/ui/streamlit_app.py` | **MODIFY** | Add `compare_product_ids`/`compare_open` to state init; inject action bar + panel after grid |
| `app/ui/design_tokens.py` | **MODIFY** | Add `.compare-*` CSS classes |
| `tests/test_ui/test_compare_panel.py` | **CREATE** | Unit tests for compare panel |
| `tests/test_ui/test_product_card.py` | **MODIFY** | Add compare button tests |

---

## Test Requirements

### New: `tests/test_ui/test_compare_panel.py` (~10 tests)
```python
def test_render_compare_panel_two_products(mock_streamlit):
    """Panel renders without error given two valid products."""

def test_diff_highlighting_applied_when_values_differ():
    """compare-row-diff class used when field values differ."""

def test_no_diff_class_when_values_same():
    """compare-row class used when field values are identical."""

def test_get_field_price_format():
    """Price formatted as $XX.XX."""

def test_get_field_rating_stars():
    """Rating rendered with ⭐ emoji + numeric."""

def test_get_field_missing_key_returns_dash():
    """Missing fields return '—'."""

def test_image_row_renders_thumbnails():
    """Image row renders <img> tags for both products."""

def test_description_field_shown():
    """Description included in COMPARE_FIELDS."""

def test_compare_panel_handles_missing_image_url():
    """Falls back to placehold.co when image_url is None."""

def test_product_names_in_column_headers():
    """Product names appear as column headers in HTML."""
```

### Modify: `tests/test_ui/test_product_card.py` (~3 tests)
```python
def test_compare_button_shown_on_card():
    """Compare button rendered for product with valid ID."""

def test_compare_button_shows_selected_state():
    """Button label is '✅ Comparing' when product_id in compare_product_ids."""

def test_compare_fifo_removes_oldest_on_third_selection():
    """Adding a 3rd ID removes the first — FIFO behaviour."""
```

**Expected test delta:** +13 new tests (362 → ~375)

---

## Notes for Developer
- The `on_click` closure pattern (used in SCRUM-61 reviews toggle) avoids extra `st.rerun()` calls on selection — reuse it for compare toggle too
- `render_compare_panel` is pure HTML via `st.markdown(unsafe_allow_html=True)` — no Streamlit widgets inside, so no key conflicts with the grid
- The "Compare Products" button uses `disabled=(n < 2)` — Streamlit natively greys out disabled buttons
- Keep `compare_open = False` when a product is deselected from 2→1 so the table doesn't show a stale single-product state
