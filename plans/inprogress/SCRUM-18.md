# SCRUM-18 — UI/UX Refinement and Visual Polish

## Story
As a user, I want a polished, intuitive interface so that my shopping experience is
pleasant and efficient.

## Acceptance Criteria
- [ ] Consistent color scheme and branding (design tokens)
- [ ] Product cards with images, ratings, prices (enhanced)
- [ ] Smooth transitions and animations
- [ ] Mobile-responsive design tested (Streamlit layout engine)
- [ ] Accessibility improvements (WCAG 2.1 AA contrast, aria-label fallbacks)
- [ ] Dark mode support via `.streamlit/config.toml`
- [ ] Loading states and progress indicators (spinners + skeletons)
- [ ] Empty states with helpful messages
- [ ] Chat message timestamps
- [ ] Star ratings visualised as filled/empty stars (not just ⭐ emoji)

## Current Test Count
241 (after SCRUM-17). Target after this story: **251** (+10 new tests).

---

## Architecture Overview

```
app/ui/
├── design_tokens.py          ← NEW: CSS constants & full stylesheet
├── components/
│   ├── star_rating.py        ← NEW: SVG-based star rating renderer
│   ├── product_card.py       ← MODIFY: image thumbnails, star rating, price badge
│   ├── review_display.py     ← MODIFY: progress bars with WCAG colours
│   └── chat_helpers.py       ← MODIFY: timestamps on messages
├── streamlit_app.py          ← MODIFY: inject design tokens, timestamps, empty states
.streamlit/
└── config.toml               ← NEW: theme + dark mode toggle
```

---

## Tasks

### Task 1 — `.streamlit/config.toml` (dark mode + brand theme)

```toml
[theme]
# SmartShop AI brand palette
primaryColor        = "#1f77b4"   # brand blue
backgroundColor     = "#ffffff"
secondaryBackgroundColor = "#f0f4f8"
textColor           = "#1a1a2e"
font                = "sans serif"

[server]
headless            = true
enableCORS          = false

# Dark mode: users toggle via Settings ▸ Theme in the Streamlit toolbar.
# The primaryColor etc. above apply to the light theme.
# For dark mode we rely on Streamlit's built-in inversion — no separate overrides needed.
```

> **Note:** Streamlit does not support per-session server-side dark mode switching via
> Python code. Dark mode is enabled by the end-user via the hamburger ▸ Settings ▸
> Theme menu. `config.toml` sets the *light* brand palette; Streamlit's auto-dark mode
> inverts it appropriately.

---

### Task 2 — `app/ui/design_tokens.py` (CSS design system)

Centralise all CSS so it is injected once at app startup. Replaces the two inline
rules in `streamlit_app.py`.

```python
"""SmartShop AI design tokens & global CSS."""

# --- Colour palette -----------------------------------------------------------
COLOR_BRAND_PRIMARY   = "#1f77b4"
COLOR_BRAND_SECONDARY = "#ff7f0e"
COLOR_SUCCESS         = "#2ca02c"
COLOR_WARNING         = "#d62728"
COLOR_NEUTRAL_DARK    = "#1a1a2e"
COLOR_NEUTRAL_LIGHT   = "#f0f4f8"

# --- Typography ---------------------------------------------------------------
FONT_SIZE_H1 = "2.4rem"
FONT_SIZE_H2 = "1.6rem"
FONT_SIZE_BODY = "1rem"
FONT_SIZE_CAPTION = "0.85rem"

# --- Spacing -----------------------------------------------------------------
SPACE_XS = "4px"
SPACE_SM = "8px"
SPACE_MD = "16px"
SPACE_LG = "24px"
SPACE_XL = "40px"

# --- Border radius -----------------------------------------------------------
RADIUS_SM = "6px"
RADIUS_MD = "12px"
RADIUS_LG = "20px"


def get_global_css() -> str:
    """
    Return the complete SmartShop AI stylesheet as a <style> string.
    Inject once via st.markdown(get_global_css(), unsafe_allow_html=True).
    """
    return f"""
<style>
/* ── Brand Header ─────────────────────────────────────────────── */
.main-header {{
    font-size: {FONT_SIZE_H1};
    font-weight: 700;
    color: {COLOR_BRAND_PRIMARY};
    letter-spacing: -0.5px;
}}
.sub-header {{
    font-size: {FONT_SIZE_BODY};
    color: #666;
    margin-bottom: {SPACE_LG};
}}

/* ── Product Card ─────────────────────────────────────────────── */
.product-card {{
    border: 1px solid #e0e0e0;
    border-radius: {RADIUS_MD};
    padding: {SPACE_MD};
    transition: box-shadow 0.2s ease, transform 0.15s ease;
}}
.product-card:hover {{
    box-shadow: 0 4px 16px rgba(31,119,180,0.18);
    transform: translateY(-2px);
}}
.product-image {{
    width: 100%;
    border-radius: {RADIUS_SM};
    object-fit: contain;
    max-height: 160px;
    background: {COLOR_NEUTRAL_LIGHT};
}}
.price-badge {{
    display: inline-block;
    background: {COLOR_BRAND_PRIMARY};
    color: #fff;
    border-radius: {RADIUS_SM};
    padding: 2px 10px;
    font-size: {FONT_SIZE_CAPTION};
    font-weight: 600;
}}
.stock-badge-ok      {{ color: {COLOR_SUCCESS}; font-weight: 600; }}
.stock-badge-low     {{ color: {COLOR_BRAND_SECONDARY}; font-weight: 600; }}
.stock-badge-out     {{ color: {COLOR_WARNING}; font-weight: 600; }}

/* ── Star Rating ──────────────────────────────────────────────── */
.star-rating {{
    display: inline-flex;
    gap: 2px;
    vertical-align: middle;
}}
.star-filled  {{ color: #f5a623; font-size: 1.1rem; }}
.star-half    {{ color: #f5a623; font-size: 1.1rem; }}
.star-empty   {{ color: #d0d0d0; font-size: 1.1rem; }}

/* ── Chat Bubbles ─────────────────────────────────────────────── */
.chat-timestamp {{
    font-size: {FONT_SIZE_CAPTION};
    color: #999;
    margin-top: {SPACE_XS};
}}

/* ── Empty State ──────────────────────────────────────────────── */
.empty-state {{
    text-align: center;
    padding: {SPACE_XL};
    color: #888;
    font-size: {FONT_SIZE_BODY};
}}

/* ── Accessibility: focus ring ────────────────────────────────── */
button:focus-visible, a:focus-visible {{
    outline: 3px solid {COLOR_BRAND_PRIMARY};
    outline-offset: 2px;
}}
</style>
"""


def render_empty_state(icon: str = "🔍", message: str = "No results found.",
                        hint: str = "") -> str:
    """Return an HTML empty-state block."""
    hint_html = f'<p style="font-size:0.85rem;color:#aaa;">{hint}</p>' if hint else ""
    return (
        f'<div class="empty-state">'
        f'<div style="font-size:3rem;">{icon}</div>'
        f'<p>{message}</p>{hint_html}'
        f'</div>'
    )
```

---

### Task 3 — `app/ui/components/star_rating.py` (SVG-accurate star display)

Render 0–5 star ratings with half-star precision, WCAG-compliant aria-label.

```python
"""Star rating renderer — half-star precision, WCAG aria-label."""

import math


def render_star_rating_html(rating: float | None,
                             max_stars: int = 5,
                             label: str | None = None) -> str:
    """
    Return an HTML span with filled / half / empty star characters and
    an aria-label for screen-reader accessibility.

    Args:
        rating: float 0–5 (None → returns "N/A")
        max_stars: defaults to 5
        label: optional additional aria description (e.g. product name)

    Returns:
        HTML string safe to use with st.markdown(..., unsafe_allow_html=True)

    Examples:
        render_star_rating_html(4.3) →
            <span class="star-rating" aria-label="4.3 out of 5 stars" role="img">
              ★★★★½☆</span>
    """
    if rating is None:
        return '<span class="star-empty" aria-label="No rating">N/A</span>'

    rating = max(0.0, min(float(rating), float(max_stars)))
    aria = f"{rating:.1f} out of {max_stars} stars"
    if label:
        aria = f"{label}: {aria}"

    stars_html = []
    for i in range(max_stars):
        if rating >= i + 1:
            stars_html.append('<span class="star-filled" aria-hidden="true">★</span>')
        elif rating >= i + 0.5:
            stars_html.append('<span class="star-half"  aria-hidden="true">⯨</span>')
        else:
            stars_html.append('<span class="star-empty" aria-hidden="true">☆</span>')

    inner = "".join(stars_html)
    return (
        f'<span class="star-rating" aria-label="{aria}" role="img">'
        f'{inner}</span>'
    )


def star_rating_text(rating: float | None, max_stars: int = 5) -> str:
    """Plain-text fallback (for emails, tooltips). E.g. '★★★★½☆ (4.3)'"""
    if rating is None:
        return "N/A"
    rating = max(0.0, min(float(rating), float(max_stars)))
    stars = []
    for i in range(max_stars):
        if rating >= i + 1:
            stars.append("★")
        elif rating >= i + 0.5:
            stars.append("½")
        else:
            stars.append("☆")
    return f"{''.join(stars)} ({rating:.1f})"
```

---

### Task 4 — Update `app/ui/components/product_card.py`

Enhance with image thumbnails, star ratings, price badge, hover animation,
empty-state when no products.

```python
"""Product card and grid rendering components — v2 (SCRUM-18)."""

import streamlit as st
from app.ui.components.star_rating import render_star_rating_html
from app.ui.design_tokens import render_empty_state

PLACEHOLDER_IMG = "https://placehold.co/300x160/f0f4f8/1f77b4?text=No+Image"


def _product_image_url(product: dict) -> str:
    """Return product image URL or placehold.co fallback."""
    return product.get("image_url") or PLACEHOLDER_IMG


def render_product_card(product: dict) -> None:
    """Render a single product as a styled card — v2."""
    with st.container(border=True):
        # Image
        img_url = _product_image_url(product)
        st.markdown(
            f'<img src="{img_url}" class="product-image" '
            f'alt="{product.get("name", "Product image")}" />',
            unsafe_allow_html=True,
        )

        st.markdown(f"**{product.get('name', 'Unknown')}**")

        # Price badge + star rating side by side
        price = product.get("price")
        rating = product.get("rating")
        price_html = (
            f'<span class="price-badge">${float(price):.2f}</span>'
            if price is not None
            else '<span class="price-badge">N/A</span>'
        )
        stars_html = render_star_rating_html(rating, label=product.get("name"))
        st.markdown(f"{price_html} &nbsp; {stars_html}", unsafe_allow_html=True)

        if product.get("brand"):
            st.caption(f"Brand: {product['brand']} · {product.get('category', '')}")

        # Stock indicator
        stock = product.get("stock")
        if stock is not None:
            if stock > 10:
                st.markdown(
                    f'<span class="stock-badge-ok">✅ In Stock ({stock})</span>',
                    unsafe_allow_html=True,
                )
            elif stock > 0:
                st.markdown(
                    f'<span class="stock-badge-low">⚠️ Low Stock ({stock})</span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<span class="stock-badge-out">❌ Out of Stock</span>',
                    unsafe_allow_html=True,
                )

        if product.get("reason"):
            st.info(f"{product['reason']}")

        if product.get("relevance_score") is not None:
            score = product["relevance_score"]
            st.progress(score, text=f"Relevance: {score:.0%}")


def render_product_grid(products: list[dict], cols: int = 3) -> None:
    """Render a grid of product cards with an empty state if none found."""
    if not products:
        st.markdown(
            render_empty_state(
                icon="🔍",
                message="No products found matching your criteria.",
                hint="Try broadening your search or removing filters.",
            ),
            unsafe_allow_html=True,
        )
        return

    columns = st.columns(cols)
    for i, product in enumerate(products):
        with columns[i % cols]:
            render_product_card(product)
```

---

### Task 5 — Update `app/ui/streamlit_app.py`

Four targeted changes:

**5a — Inject global CSS once at startup (replaces the 2-line inline style block)**
```python
from app.ui.design_tokens import get_global_css
st.markdown(get_global_css(), unsafe_allow_html=True)
```

**5b — Chat timestamps**
```python
import datetime

# In the message display loop:
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("timestamp"):
            ts = datetime.datetime.fromtimestamp(msg["timestamp"]).strftime("%H:%M")
            st.markdown(
                f'<div class="chat-timestamp">{ts}</div>',
                unsafe_allow_html=True,
            )

# When appending messages, include a timestamp:
import time
st.session_state.messages.append({
    "role": "user",
    "content": prompt,
    "timestamp": time.time(),
})
```

**5c — Typing indicator during API calls**
```python
with st.chat_message("assistant"):
    with st.spinner("SmartShop AI is thinking..."):
        # ... existing API call ...
    st.markdown(reply)
    st.markdown(
        f'<div class="chat-timestamp">{datetime.datetime.now().strftime("%H:%M")}</div>',
        unsafe_allow_html=True,
    )
```

**5d — Empty-state pages** (when the user lands on a page before searching):
```python
# e.g. Review Summarization page before query
if not query.strip() and not st.session_state.get("review_submitted"):
    from app.ui.design_tokens import render_empty_state
    st.markdown(
        render_empty_state("⭐", "Enter a product name above to summarise its reviews.",
                           "Try: 'Sony WH-1000XM5' or 'Samsung Galaxy S24'"),
        unsafe_allow_html=True,
    )
```

---

### Task 6 — Update `app/ui/components/review_display.py`

Improve progress bars with WCAG contrast-safe colour labels:

```python
# Replace raw st.progress with labelled versions
for theme_item in pos_themes:
    conf = theme_item["confidence"]
    st.markdown(f"✅ **{theme_item['theme']}**")
    st.progress(conf, text=f"{conf:.0%} of reviewers mention this")

for theme_item in neg_themes:
    conf = theme_item["confidence"]
    st.markdown(f"⚠️ **{theme_item['theme']}**")
    st.progress(conf, text=f"{conf:.0%} of reviewers mention this")
```

---

### Task 7 — Tests (10 new tests, target 251)

#### `tests/test_ui/test_star_rating.py` — 6 tests

```python
"""Unit tests for star_rating component (pure functions — no Streamlit calls)."""

import pytest
from app.ui.components.star_rating import render_star_rating_html, star_rating_text


def test_none_rating_returns_na():
    html = render_star_rating_html(None)
    assert "N/A" in html


def test_full_stars_five():
    html = render_star_rating_html(5.0)
    assert html.count("star-filled") == 5
    assert "star-empty" not in html
    assert "star-half" not in html


def test_half_star_precision():
    html = render_star_rating_html(4.5)
    assert html.count("star-filled") == 4
    assert "star-half" in html
    assert html.count("star-empty") == 0


def test_zero_rating_all_empty():
    html = render_star_rating_html(0.0)
    assert html.count("star-empty") == 5
    assert "star-filled" not in html


def test_aria_label_present():
    html = render_star_rating_html(3.7, label="Widget X")
    assert 'aria-label="Widget X: 3.7 out of 5 stars"' in html
    assert 'role="img"' in html


def test_star_rating_text_plain():
    text = star_rating_text(4.0)
    assert "★★★★" in text
    assert "4.0" in text
```

#### `tests/test_ui/test_design_tokens.py` — 4 tests

```python
"""Unit tests for design_tokens helpers (pure string functions)."""

from app.ui.design_tokens import get_global_css, render_empty_state


def test_get_global_css_returns_style_tag():
    css = get_global_css()
    assert css.startswith("<style>")
    assert css.endswith("</style>\n") or "</style>" in css


def test_get_global_css_contains_brand_color():
    css = get_global_css()
    assert "#1f77b4" in css  # COLOR_BRAND_PRIMARY


def test_render_empty_state_contains_message():
    html = render_empty_state("🔍", "No products found.", "Try broadening your search.")
    assert "No products found." in html
    assert "Try broadening your search." in html
    assert "empty-state" in html


def test_render_empty_state_no_hint():
    html = render_empty_state("⭐", "Enter a query.")
    assert "Enter a query." in html
    # hint paragraph should NOT be present
    assert "<p style=" not in html or "font-size:0.85rem" not in html
```

---

## File Map

| File | Action |
|------|--------|
| `.streamlit/config.toml` | CREATE — brand theme + dark mode |
| `app/ui/design_tokens.py` | CREATE — CSS constants + `get_global_css()` + `render_empty_state()` |
| `app/ui/components/star_rating.py` | CREATE — `render_star_rating_html()` + `star_rating_text()` |
| `app/ui/components/product_card.py` | MODIFY — image thumbnails, star rating, price badge, empty state |
| `app/ui/components/review_display.py` | MODIFY — WCAG progress bars |
| `app/ui/streamlit_app.py` | MODIFY — inject CSS, timestamps, typing indicator, empty states |
| `tests/test_ui/test_star_rating.py` | CREATE |
| `tests/test_ui/test_design_tokens.py` | CREATE |

---

## Dependencies

- **No new pip packages required** — `placehold.co` images are loaded client-side
  by the browser; no server-side image processing needed.
- Streamlit's built-in dark mode (hamburger ▸ Settings ▸ Theme) handles dark mode
  toggling; `.streamlit/config.toml` sets the light brand palette.
- `app.ui.components.star_rating` and `app.ui.design_tokens` are pure Python —
  no Streamlit calls — making them fully unit-testable.

---

## Manual QA Checklist (to be verified before marking Done)

- [ ] Open app at 1280×800 — cards display in 3-column grid
- [ ] Open app at 375×812 (mobile) — Streamlit collapses to single column
- [ ] Toggle dark mode via hamburger ▸ Settings ▸ Theme — brand colours invert correctly
- [ ] Hover over a product card — subtle shadow lift visible
- [ ] 4.5-star product shows 4 filled + 1 half-star
- [ ] Product without an image shows grey placehold.co placeholder
- [ ] Chat message shows timestamp after assistant reply
- [ ] "Clear Conversation" button resets history and timestamp
- [ ] Empty Pricing Insights page (before search) shows empty-state block
- [ ] Run Lighthouse accessibility audit — score ≥ 85

---

## Test Count Verification

| Layer | New Tests |
|-------|----------|
| `test_star_rating.py` | 6 |
| `test_design_tokens.py` | 4 |
| **Total new** | **10** |
| **Cumulative** | **251** |
