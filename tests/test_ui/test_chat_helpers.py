"""Unit tests for chat_helpers — SCRUM-83 product link formatting."""

from app.ui.components.chat_helpers import (
    format_recommendation_message,
    format_review_message,
    _product_link_md,
)


class TestProductLinkMd:
    def test_returns_link_with_product_id(self):
        result = _product_link_md("Test Product", "PROD001")
        assert result == "[Test Product](#PROD001)"

    def test_returns_plain_name_without_product_id(self):
        result = _product_link_md("Test Product", None)
        assert result == "Test Product"

    def test_returns_plain_name_with_empty_string_id(self):
        result = _product_link_md("Test Product", "")
        assert result == "Test Product"


class TestFormatRecommendationWithLinks:
    def test_recommendation_with_product_id_has_link(self):
        data = {
            "query": "headphones",
            "recommendations": [
                {
                    "name": "Sony WH-1000XM5",
                    "product_id": "HP001",
                    "price": 299.99,
                    "rating": 4.5,
                    "reason": "Great noise cancellation",
                }
            ],
        }
        result = format_recommendation_message(data)
        assert "[Sony WH-1000XM5](#HP001)" in result

    def test_recommendation_without_product_id_no_link(self):
        data = {
            "query": "headphones",
            "recommendations": [
                {
                    "name": "Sony WH-1000XM5",
                    "price": 299.99,
                    "reason": "Great",
                }
            ],
        }
        result = format_recommendation_message(data)
        assert "Sony WH-1000XM5" in result
        assert "[Sony WH-1000XM5]" not in result

    def test_recommendation_uses_id_field_as_fallback(self):
        data = {
            "query": "phones",
            "recommendations": [
                {
                    "name": "Galaxy S24",
                    "id": "PH001",
                    "price": 799.0,
                    "reason": "Top pick",
                }
            ],
        }
        result = format_recommendation_message(data)
        assert "[Galaxy S24](#PH001)" in result

    def test_multiple_recommendations_all_get_links(self):
        data = {
            "query": "laptops",
            "recommendations": [
                {"name": "MacBook Pro", "product_id": "LP001", "price": 1999.0},
                {"name": "ThinkPad X1", "product_id": "LP002", "price": 1499.0},
                {"name": "Dell XPS 15", "product_id": "LP003", "price": 1299.0},
            ],
        }
        result = format_recommendation_message(data)
        assert "[MacBook Pro](#LP001)" in result
        assert "[ThinkPad X1](#LP002)" in result
        assert "[Dell XPS 15](#LP003)" in result

    def test_empty_recommendations_returns_fallback(self):
        data = {"query": "nothing", "recommendations": []}
        result = format_recommendation_message(data)
        assert "couldn't find" in result.lower()

    def test_reasoning_summary_included(self):
        data = {
            "query": "test",
            "recommendations": [{"name": "P1", "product_id": "X1", "price": 10.0}],
            "reasoning_summary": "Based on your preferences",
        }
        result = format_recommendation_message(data)
        assert "Based on your preferences" in result


class TestFormatReviewWithLinks:
    def test_review_with_product_id_has_link(self):
        data = {
            "product_name": "Sony WH-1000XM5",
            "product_id": "HP001",
            "total_reviews": 100,
            "average_rating": 4.5,
            "sentiment_score": 0.85,
            "positive_themes": [],
            "negative_themes": [],
        }
        result = format_review_message(data)
        assert "[Sony WH-1000XM5](#HP001)" in result

    def test_review_without_product_id_no_link(self):
        data = {
            "product_name": "Sony WH-1000XM5",
            "total_reviews": 100,
            "average_rating": 4.5,
            "sentiment_score": 0.85,
            "positive_themes": [],
            "negative_themes": [],
        }
        result = format_review_message(data)
        assert "Sony WH-1000XM5" in result
        assert "[Sony WH-1000XM5]" not in result

    def test_review_uses_id_field_as_fallback(self):
        data = {
            "product_name": "Galaxy S24",
            "id": "PH001",
            "total_reviews": 50,
            "average_rating": 4.0,
            "sentiment_score": 0.80,
            "positive_themes": [],
            "negative_themes": [],
        }
        result = format_review_message(data)
        assert "[Galaxy S24](#PH001)" in result
