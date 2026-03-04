# SCRUM-42 — Improve Product Card: Compact Layout, Visible Description & Full Review Info

**Jira:** https://projecttracking.atlassian.net/browse/SCRUM-42
**Priority:** Medium
**Status:** In Progress

---

## Story

> As a shopper browsing the product listing page, I want product cards that are more compact, show the description upfront, and display complete review information, so that I can quickly compare and evaluate products without extra clicks.

---

## Acceptance Criteria

### A — Compact Card Layout
- [ ] Reduce internal padding and vertical spacing (~20–30% reduction in card height)
- [ ] Font sizes tightened: product name slightly smaller, price remains prominent
- [ ] Card still displays: product image, name, price, rating, and description without scrolling within the card

### B — Description Visible by Default
- [ ] Product description is displayed by default — no click/toggle required
- [ ] Description text in smaller font (12–13px) in muted/secondary colour
- [ ] Description capped at 2–3 lines with ellipsis overflow
- [ ] Remove the "Show Description" / "Hide Description" `st.expander` toggle button

### C — Full Review Information & Link
- [ ] Star rating icons AND total review count displayed side by side (e.g. ★★★★☆ 128 reviews)
- [ ] Review count is a clickable link navigating to reviews section on product detail page
- [ ] If 0 reviews, display "No reviews yet" in place of star rating
- [ ] Review count updates dynamically if reviews are loaded asynchronously

---

## Current State

**`app/ui/components/product_card.py`** (key issue lines):
```python
# Line 69–70 — Description is hidden behind expander (to be replaced):
if product.get("description"):
    with st.expander("Show Description"):
        st.write(product.get("description"))

# Line 36-37 — Star rating renders stars only, no review count:
stars_html = render_star_rating_html(rating, label=product.get("name"))
st.markdown(f"{price_html} &nbsp; {stars_html}", unsafe_allow_html=True)
```

**`app/ui/components/star_rating.py`**: Only renders stars, no review count field.

**`app/ui/design_tokens.py`**: Current `.product-card` has `padding: 16px` (SPACE_MD). Needs tightening.

**Product dict fields available**: `name`, `price`, `rating`, `brand`, `category`, `stock`, `description`, `reason`, `relevance_score`, `image_url`. Note: `review_count` field may need to be confirmed in the Product schema/model.

---

## Technical Approach

All changes are confined to the UI layer — no backend changes required.

### 1. Update `product_card.py`
- Replace `st.expander("Show Description")` with inline `st.markdown` using CSS class for truncation
- Update the rating line to include review count from `product.get("review_count", 0)`
- Tighten `st.markdown` for product name to use a smaller font via CSS class

### 2. Update `design_tokens.py`
- Add `.product-description` CSS class: `font-size: 12px; color: #6B7280; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;`
- Add `.review-count-link` CSS class for the review count hyperlink style
- Tighten `.product-card` padding from `{SPACE_MD}` (16px) to `10px`
- Add `.product-name` class for slightly smaller name font

### 3. Update `star_rating.py`
- Extend `render_star_rating_html` to accept optional `review_count: int | None = None`
- When `review_count` is provided: append review count text after stars
- When `review_count == 0`: return "No reviews yet" badge

### 4. Check Product Schema for `review_count`
- Verify `app/schemas/product.py` and `app/models/product.py` expose `review_count`
- If missing, add `review_count: int | None = None` to Pydantic schema (nullable, no DB migration needed for nullable field)

---

## File Map

| File | Action | What Changes |
|------|--------|-------------|
| `app/ui/components/product_card.py` | MODIFY | Remove expander; add inline description; pass review_count to star rating |
| `app/ui/components/star_rating.py` | MODIFY | Add `review_count` param; "No reviews yet" fallback |
| `app/ui/design_tokens.py` | MODIFY | Add description + review-link CSS; tighten card padding |
| `app/schemas/product.py` | MODIFY (if needed) | Add `review_count: int | None = None` if not present |
| `tests/test_ui/test_star_rating.py` | MODIFY | Add tests for review_count rendering |
| `tests/test_ui/test_product_card.py` | CREATE | Unit tests for updated product card HTML |

---

## Code Snippets

### Updated `render_star_rating_html` signature

```python
def render_star_rating_html(
    rating: float | None,
    max_stars: int = 5,
    label: str | None = None,
    review_count: int | None = None,
) -> str:
```

Review count rendering at end of function:
```python
# After building inner stars HTML:
if review_count is not None:
    if review_count == 0:
        return '<span class="star-empty" aria-label="No reviews">No reviews yet</span>'
    count_html = (
        f' <a href="#reviews" class="review-count-link" '
        f'aria-label="{review_count} customer reviews">'
        f'{review_count} review{"s" if review_count != 1 else ""}</a>'
    )
else:
    count_html = ""

return (
    f'<span class="star-rating" aria-label="{aria}" role="img">'
    f'{inner}</span>{count_html}'
)
```

### Updated description block in `product_card.py`

```python
# Replace st.expander block with:
if product.get("description"):
    st.markdown(
        f'<p class="product-description">{product["description"]}</p>',
        unsafe_allow_html=True,
    )
```

### Updated rating+review line in `product_card.py`

```python
stars_html = render_star_rating_html(
    rating,
    label=product.get("name"),
    review_count=product.get("review_count"),
)
st.markdown(f"{price_html} &nbsp; {stars_html}", unsafe_allow_html=True)
```

### New CSS in `design_tokens.py`

```css
/* Product Description (inline, truncated) */
.product-description {
    font-size: 12px;
    color: #6B7280;
    overflow: hidden;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    margin: 4px 0;
    line-height: 1.4;
}

/* Review Count Link */
.review-count-link {
    font-size: 0.8rem;
    color: #1f77b4;
    text-decoration: none;
    margin-left: 4px;
}
.review-count-link:hover {
    text-decoration: underline;
}
```

---

## Test Requirements

**Modify:** `tests/test_ui/test_star_rating.py` (~5 new tests):
```
test_review_count_shown_in_html()
test_zero_review_count_shows_no_reviews_yet()
test_review_count_none_shows_no_count_link()
test_plural_reviews_label()
test_singular_review_label()
```

**Create:** `tests/test_ui/test_product_card.py` (~7 new tests):
```
test_description_shown_inline_not_expander()
test_description_uses_product_description_class()
test_description_missing_renders_no_description_html()
test_product_name_rendered()
test_price_badge_rendered()
test_stock_badge_ok()
test_stock_out_badge()
```

**Expected new tests:** ~12
**Total after story:** ~299

---

## Dependencies

- Depends on SCRUM-18 (design_tokens.py in place) ✅
- Depends on SCRUM-40 (product_card.py v2 already merged) ✅
- No backend changes or new packages required

---

## Out of Scope

- Changes to the product detail page layout
- Sorting or filtering reviews from the card
