"""Tests for app.agents.utils query builders."""

from app.agents.utils import build_recommendation_query, build_review_query


def test_recommendation_query_with_max_price():
    result = build_recommendation_query("laptop", {"max_price": 1000}, 5)
    assert "Maximum price: $1000" in result
    assert "laptop" in result


def test_recommendation_query_no_hints():
    result = build_recommendation_query("laptop", {}, 5)
    assert "Return top 5 recommendations." in result
    assert "Maximum price" not in result


def test_recommendation_query_all_hints():
    hints = {"max_price": 500, "min_price": 100, "category": "phones", "min_rating": 4}
    result = build_recommendation_query("phone", hints, 3)
    assert "Maximum price: $500" in result
    assert "Minimum price: $100" in result
    assert "Category: phones" in result
    assert "Minimum rating: 4/5" in result


def test_review_query_with_product_id():
    result = build_review_query("reviews for X", product_id="P123", max_reviews=10)
    assert "P123" in result
    assert "5 positive" in result


def test_review_query_no_product_id():
    result = build_review_query("reviews", product_id=None, max_reviews=10)
    assert "Product ID" not in result
    assert "5 positive" in result
