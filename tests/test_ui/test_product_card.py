"""Unit tests for product_card component (SCRUM-42)."""

from unittest.mock import MagicMock, patch, call
import pytest


SAMPLE_PRODUCT = {
    "name": "Test Headphones",
    "price": 99.99,
    "rating": 4.5,
    "brand": "TestBrand",
    "category": "Headphone",
    "stock": 25,
    "description": "A great pair of headphones for music lovers.",
    "image_url": "https://example.com/img.jpg",
    "review_count": 42,
}


@pytest.fixture
def mock_st():
    """Patch streamlit in product_card module."""
    with patch("app.ui.components.product_card.st") as mock:
        mock.container.return_value.__enter__ = MagicMock(return_value=None)
        mock.container.return_value.__exit__ = MagicMock(return_value=False)
        yield mock


def test_description_shown_inline_not_expander(mock_st):
    from app.ui.components.product_card import render_product_card
    render_product_card(SAMPLE_PRODUCT)
    # Should NOT use expander
    mock_st.expander.assert_not_called()
    # Should use markdown with product-description class
    markdown_calls = [str(c) for c in mock_st.markdown.call_args_list]
    desc_calls = [c for c in markdown_calls if "product-description" in c]
    assert len(desc_calls) > 0, "Description should be rendered with product-description class"


def test_description_uses_product_description_class(mock_st):
    from app.ui.components.product_card import render_product_card
    render_product_card(SAMPLE_PRODUCT)
    found = False
    for c in mock_st.markdown.call_args_list:
        args = c[0] if c[0] else ()
        if args and "product-description" in str(args[0]):
            assert "A great pair of headphones" in str(args[0])
            found = True
    assert found, "product-description CSS class should contain the description text"


def test_description_missing_renders_no_description_html(mock_st):
    from app.ui.components.product_card import render_product_card
    product = {**SAMPLE_PRODUCT, "description": None}
    render_product_card(product)
    for c in mock_st.markdown.call_args_list:
        args = c[0] if c[0] else ()
        if args:
            assert "product-description" not in str(args[0])


def test_product_name_rendered(mock_st):
    from app.ui.components.product_card import render_product_card
    render_product_card(SAMPLE_PRODUCT)
    found = any("Test Headphones" in str(c) for c in mock_st.markdown.call_args_list)
    assert found, "Product name should be rendered"


def test_price_badge_rendered(mock_st):
    from app.ui.components.product_card import render_product_card
    render_product_card(SAMPLE_PRODUCT)
    found = any("price-badge" in str(c) for c in mock_st.markdown.call_args_list)
    assert found, "Price badge should be rendered"


def test_stock_badge_ok(mock_st):
    from app.ui.components.product_card import render_product_card
    render_product_card(SAMPLE_PRODUCT)
    found = any("stock-badge-ok" in str(c) for c in mock_st.markdown.call_args_list)
    assert found, "Stock badge should show 'ok' for stock > 10"


def test_stock_out_badge(mock_st):
    from app.ui.components.product_card import render_product_card
    product = {**SAMPLE_PRODUCT, "stock": 0}
    render_product_card(product)
    found = any("stock-badge-out" in str(c) for c in mock_st.markdown.call_args_list)
    assert found, "Stock badge should show 'out' for stock == 0"
