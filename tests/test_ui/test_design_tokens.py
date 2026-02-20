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
