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
