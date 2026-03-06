"""Unit tests for inline review panel component (SCRUM-61)."""

from unittest.mock import patch

from app.ui.components.review_panel import _SENTIMENT_BADGE, _render_single_review


class TestSentimentBadge:
    def test_positive_badge(self):
        assert "Positive" in _SENTIMENT_BADGE["positive"]
        assert "#2ca02c" in _SENTIMENT_BADGE["positive"]

    def test_negative_badge(self):
        assert "Negative" in _SENTIMENT_BADGE["negative"]
        assert "#d62728" in _SENTIMENT_BADGE["negative"]

    def test_neutral_badge(self):
        assert "Neutral" in _SENTIMENT_BADGE["neutral"]

    def test_unknown_sentiment_returns_empty(self):
        assert _SENTIMENT_BADGE.get("unknown", "") == ""
        assert _SENTIMENT_BADGE.get(None, "") == ""


class TestRenderSingleReview:
    """Test _render_single_review via st.markdown calls."""

    @patch("app.ui.components.review_panel.st.markdown")
    def test_contains_rating_stars(self, mock_md):
        review = {
            "rating": 4.5,
            "sentiment": "positive",
            "review_date": "2025-01-15",
            "text": "Awesome!",
        }
        _render_single_review(review)
        call_args = mock_md.call_args[0][0]
        assert "star-rating" in call_args
        assert "star-filled" in call_args

    @patch("app.ui.components.review_panel.st.markdown")
    def test_handles_missing_text(self, mock_md):
        review = {"rating": 3.0, "sentiment": None, "review_date": "", "text": None}
        _render_single_review(review)
        call_args = mock_md.call_args[0][0]
        assert "No review text provided" in call_args

    @patch("app.ui.components.review_panel.st.markdown")
    def test_renders_sentiment_badge(self, mock_md):
        review = {
            "rating": 2.0,
            "sentiment": "negative",
            "review_date": "2025-03-01",
            "text": "Bad",
        }
        _render_single_review(review)
        call_args = mock_md.call_args[0][0]
        assert "Negative" in call_args
        assert "#d62728" in call_args

    @patch("app.ui.components.review_panel.st.markdown")
    def test_renders_date(self, mock_md):
        review = {
            "rating": 5.0,
            "sentiment": "positive",
            "review_date": "2025-06-20",
            "text": "Perfect",
        }
        _render_single_review(review)
        call_args = mock_md.call_args[0][0]
        assert "2025-06-20" in call_args

    @patch("app.ui.components.review_panel.st.markdown")
    def test_review_card_class_applied(self, mock_md):
        review = {"rating": 4.0, "text": "Good"}
        _render_single_review(review)
        call_args = mock_md.call_args[0][0]
        assert "review-card" in call_args
