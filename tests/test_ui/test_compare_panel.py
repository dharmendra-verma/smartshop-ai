"""Unit tests for compare_panel component — SCRUM-62."""

from unittest.mock import MagicMock, patch


PRODUCT_A = {
    "id": "P001",
    "name": "Phone Alpha",
    "price": 499.99,
    "brand": "BrandA",
    "category": "Smartphone",
    "rating": 4.5,
    "review_count": 120,
    "description": "A flagship phone with great camera.",
    "image_url": "https://example.com/alpha.jpg",
}

PRODUCT_B = {
    "id": "P002",
    "name": "Phone Beta",
    "price": 399.99,
    "brand": "BrandB",
    "category": "Smartphone",
    "rating": 4.0,
    "review_count": 80,
    "description": "A budget-friendly phone with solid performance.",
    "image_url": "https://example.com/beta.jpg",
}

PRODUCT_NO_IMG = {
    "id": "P003",
    "name": "Phone Gamma",
    "price": 299.99,
    "brand": "BrandC",
    "category": "Smartphone",
    "rating": 3.5,
    "review_count": 30,
    "description": "An entry-level smartphone.",
    "image_url": None,
}


@patch("app.ui.components.compare_panel.st")
def test_render_compare_panel_two_products(mock_st):
    """Panel renders without error given two valid products."""
    from app.ui.components.compare_panel import render_compare_panel

    render_compare_panel(PRODUCT_A, PRODUCT_B)
    assert mock_st.markdown.call_count >= 2  # header + table


@patch("app.ui.components.compare_panel.st")
def test_diff_highlighting_applied_when_values_differ(mock_st):
    """compare-row-diff class used when field values differ."""
    from app.ui.components.compare_panel import render_compare_panel

    render_compare_panel(PRODUCT_A, PRODUCT_B)
    table_html = mock_st.markdown.call_args_list[-1][0][0]
    assert "compare-row-diff" in table_html


@patch("app.ui.components.compare_panel.st")
def test_no_diff_class_when_values_same(mock_st):
    """compare-row class used when field values are identical."""
    from app.ui.components.compare_panel import render_compare_panel

    same_product = {**PRODUCT_A}
    render_compare_panel(same_product, same_product)
    table_html = mock_st.markdown.call_args_list[-1][0][0]
    assert "compare-row-diff" not in table_html


@patch("app.ui.components.compare_panel.st")
def test_get_field_price_format(mock_st):
    """Price formatted as $XX.XX."""
    from app.ui.components.compare_panel import _get_field

    assert _get_field({"price": 99.99}, "price") == "$99.99"
    assert _get_field({"price": 1000}, "price") == "$1000.00"


@patch("app.ui.components.compare_panel.st")
def test_get_field_rating_stars(mock_st):
    """Rating rendered with star emoji + numeric."""
    from app.ui.components.compare_panel import _get_field

    result = _get_field({"rating": 4.5}, "rating")
    assert "⭐" in result
    assert "4.5" in result


@patch("app.ui.components.compare_panel.st")
def test_get_field_missing_key_returns_dash(mock_st):
    """Missing fields return dash."""
    from app.ui.components.compare_panel import _get_field

    assert _get_field({}, "brand") == "—"
    assert _get_field({"price": None}, "price") == "—"


@patch("app.ui.components.compare_panel.st")
def test_image_row_renders_thumbnails(mock_st):
    """Image row renders <img> tags for both products."""
    from app.ui.components.compare_panel import render_compare_panel

    render_compare_panel(PRODUCT_A, PRODUCT_B)
    table_html = mock_st.markdown.call_args_list[-1][0][0]
    assert "compare-thumb" in table_html
    assert "alpha.jpg" in table_html
    assert "beta.jpg" in table_html


@patch("app.ui.components.compare_panel.st")
def test_description_field_shown(mock_st):
    """Description included in comparison table."""
    from app.ui.components.compare_panel import render_compare_panel

    render_compare_panel(PRODUCT_A, PRODUCT_B)
    table_html = mock_st.markdown.call_args_list[-1][0][0]
    assert "flagship phone" in table_html
    assert "budget-friendly" in table_html


@patch("app.ui.components.compare_panel.st")
def test_compare_panel_handles_missing_image_url(mock_st):
    """Falls back to placehold.co when image_url is None."""
    from app.ui.components.compare_panel import render_compare_panel

    render_compare_panel(PRODUCT_A, PRODUCT_NO_IMG)
    table_html = mock_st.markdown.call_args_list[-1][0][0]
    assert "placehold.co" in table_html


@patch("app.ui.components.compare_panel.st")
def test_product_names_in_column_headers(mock_st):
    """Product names appear as column headers in HTML."""
    from app.ui.components.compare_panel import render_compare_panel

    render_compare_panel(PRODUCT_A, PRODUCT_B)
    table_html = mock_st.markdown.call_args_list[-1][0][0]
    assert "Phone Alpha" in table_html
    assert "Phone Beta" in table_html
    assert "compare-col-header" in table_html


# ---------------------------------------------------------------------------
# AI-powered comparison tests
# ---------------------------------------------------------------------------

MOCK_SUMMARY_A = {
    "product_name": "Phone Alpha",
    "total_reviews": 120,
    "sentiment_score": 0.85,
    "average_rating": 4.5,
    "positive_themes": [],
    "negative_themes": [],
    "rating_distribution": {},
    "overall_summary": "Great phone overall.",
}

MOCK_SUMMARY_B = {
    "product_name": "Phone Beta",
    "total_reviews": 80,
    "sentiment_score": 0.72,
    "average_rating": 4.0,
    "positive_themes": [],
    "negative_themes": [],
    "rating_distribution": {},
    "overall_summary": "Good value phone.",
}


@patch("app.ui.components.compare_panel.st")
def test_render_compare_panel_no_ai_calls(mock_st):
    """render_compare_panel never triggers AI calls — table only."""
    from app.ui.components.compare_panel import render_compare_panel

    render_compare_panel(PRODUCT_A, PRODUCT_B)
    mock_st.subheader.assert_not_called()


@patch("app.ui.components.review_display.render_review_summary")
@patch("app.ui.api_client.summarize_reviews")
@patch("app.ui.components.compare_panel.st")
def test_render_ai_comparison_fetches_summaries(mock_st, mock_summarize, mock_render):
    """render_ai_comparison fetches and renders review summaries."""
    mock_st.session_state = {}
    mock_spinner = MagicMock()
    mock_st.spinner.return_value = mock_spinner
    mock_spinner.__enter__ = lambda s: s
    mock_spinner.__exit__ = MagicMock(return_value=False)
    mock_col_a, mock_col_b = MagicMock(), MagicMock()
    mock_st.columns.return_value = (mock_col_a, mock_col_b)
    mock_col_a.__enter__ = lambda s: s
    mock_col_a.__exit__ = MagicMock(return_value=False)
    mock_col_b.__enter__ = lambda s: s
    mock_col_b.__exit__ = MagicMock(return_value=False)
    mock_summarize.side_effect = [
        {"success": True, "data": MOCK_SUMMARY_A, "error": None},
        {"success": True, "data": MOCK_SUMMARY_B, "error": None},
    ]
    from app.ui.components.compare_panel import render_ai_comparison

    render_ai_comparison(PRODUCT_A, PRODUCT_B, api_url="http://test:8000")
    assert mock_summarize.call_count == 2
    assert mock_render.call_count == 2


@patch("app.ui.api_client.summarize_reviews")
@patch("app.ui.components.compare_panel.st")
def test_review_summaries_cached_in_session_state(mock_st, mock_summarize):
    """Summaries cached — second call doesn't re-fetch."""
    mock_st.session_state = {
        "compare_summary_P001": MOCK_SUMMARY_A,
        "compare_summary_P002": MOCK_SUMMARY_B,
    }
    mock_col = MagicMock()
    mock_st.columns.return_value = (mock_col, mock_col)
    mock_col.__enter__ = lambda s: s
    mock_col.__exit__ = MagicMock(return_value=False)
    from app.ui.components.compare_panel import _fetch_review_summary

    result = _fetch_review_summary("http://test:8000", PRODUCT_A)
    assert result == MOCK_SUMMARY_A
    mock_summarize.assert_not_called()


@patch("app.ui.api_client.chat")
@patch("app.ui.components.compare_panel.st")
def test_verdict_cached_in_session_state(mock_st, mock_chat):
    """Verdict cached — second call doesn't re-fetch."""
    mock_st.session_state = {"compare_verdict_P001_P002": "Alpha is better."}
    from app.ui.components.compare_panel import _fetch_verdict

    result = _fetch_verdict("http://test:8000", PRODUCT_A, PRODUCT_B)
    assert result == "Alpha is better."
    mock_chat.assert_not_called()


@patch("app.ui.api_client.chat")
@patch("app.ui.api_client.summarize_reviews")
@patch("app.ui.components.compare_panel.st")
def test_ai_comparison_shows_warnings_when_api_fails(
    mock_st, mock_summarize, mock_chat
):
    """render_ai_comparison shows warnings when API calls fail."""
    mock_st.session_state = {}
    mock_spinner = MagicMock()
    mock_st.spinner.return_value = mock_spinner
    mock_spinner.__enter__ = lambda s: s
    mock_spinner.__exit__ = MagicMock(return_value=False)
    mock_col = MagicMock()
    mock_st.columns.return_value = (mock_col, mock_col)
    mock_col.__enter__ = lambda s: s
    mock_col.__exit__ = MagicMock(return_value=False)
    mock_summarize.return_value = {"success": False, "data": None, "error": "fail"}
    mock_chat.return_value = {"success": False, "data": None, "error": "fail"}
    from app.ui.components.compare_panel import render_ai_comparison

    render_ai_comparison(PRODUCT_A, PRODUCT_B, api_url="http://test:8000")
    assert mock_st.warning.call_count >= 1


@patch("app.ui.api_client.chat")
@patch("app.ui.components.compare_panel.st")
def test_verdict_uses_reasoning_summary(mock_st, mock_chat):
    """Verdict extracted from reasoning_summary field."""
    mock_st.session_state = {}
    mock_chat.return_value = {
        "success": True,
        "data": {"reasoning_summary": "Alpha wins on camera.", "answer": "See above."},
        "error": None,
    }
    from app.ui.components.compare_panel import _fetch_verdict

    result = _fetch_verdict("http://test:8000", PRODUCT_A, PRODUCT_B)
    assert result == "Alpha wins on camera."


@patch("app.ui.api_client.chat")
@patch("app.ui.components.compare_panel.st")
def test_verdict_falls_back_to_answer(mock_st, mock_chat):
    """Verdict falls back to answer when reasoning_summary is empty."""
    mock_st.session_state = {}
    mock_chat.return_value = {
        "success": True,
        "data": {"reasoning_summary": "", "answer": "Beta is the better value."},
        "error": None,
    }
    from app.ui.components.compare_panel import _fetch_verdict

    result = _fetch_verdict("http://test:8000", PRODUCT_A, PRODUCT_B)
    assert result == "Beta is the better value."


@patch("app.ui.api_client.chat")
@patch("app.ui.components.compare_panel.st")
def test_verdict_cache_key_order_independent(mock_st, mock_chat):
    """Cache key is the same regardless of product argument order."""
    mock_st.session_state = {}
    mock_chat.return_value = {
        "success": True,
        "data": {"reasoning_summary": "Verdict text.", "answer": ""},
        "error": None,
    }
    from app.ui.components.compare_panel import _fetch_verdict

    _fetch_verdict("http://test:8000", PRODUCT_A, PRODUCT_B)
    # Same cache key should exist for B-vs-A
    assert "compare_verdict_P001_P002" in mock_st.session_state
    # Calling with reversed order should hit cache
    mock_chat.reset_mock()
    result = _fetch_verdict("http://test:8000", PRODUCT_B, PRODUCT_A)
    assert result == "Verdict text."
    mock_chat.assert_not_called()


@patch("app.ui.api_client.summarize_reviews")
@patch("app.ui.components.compare_panel.st")
def test_ai_review_summaries_uses_columns(mock_st, mock_summarize):
    """Side-by-side layout uses st.columns(2)."""
    mock_st.session_state = {}
    mock_col = MagicMock()
    mock_st.columns.return_value = (mock_col, mock_col)
    mock_col.__enter__ = lambda s: s
    mock_col.__exit__ = MagicMock(return_value=False)
    mock_summarize.return_value = {
        "success": True,
        "data": MOCK_SUMMARY_A,
        "error": None,
    }
    from app.ui.components.compare_panel import _render_ai_review_summaries

    _render_ai_review_summaries(PRODUCT_A, PRODUCT_B, "http://test:8000")
    mock_st.columns.assert_called_with(2)
