"""Tests for POST /api/v1/reviews/summarize endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.agents.base import AgentResponse


def make_mock_db():
    return MagicMock()


SAMPLE_REVIEW_DATA = {
    "product_id": "PROD001",
    "product_name": "Budget Phone X1",
    "total_reviews": 142,
    "sentiment_score": 0.78,
    "average_rating": 4.1,
    "rating_distribution": {
        "five_star": 60, "four_star": 50, "three_star": 20,
        "two_star": 8, "one_star": 4,
    },
    "positive_themes": [
        {"theme": "Battery life", "confidence": 0.88, "example_quote": "Lasts 2 days!"},
        {"theme": "Value for money", "confidence": 0.82, "example_quote": None},
    ],
    "negative_themes": [
        {"theme": "Camera quality", "confidence": 0.71, "example_quote": "Blurry in low light"},
    ],
    "overall_summary": "Customers love the battery but find the camera mediocre.",
    "cached": False,
    "agent": "review-summarization-agent",
}


@pytest.fixture(autouse=True)
def override_db():
    app.dependency_overrides[get_db] = make_mock_db
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


class TestReviewsSummarizeEndpoint:
    def test_valid_request_returns_200(self):
        """POST with valid query returns 200 and review summary."""
        with patch(
            "app.api.v1.reviews._agent.process",
            new_callable=AsyncMock,
            return_value=AgentResponse(success=True, data=SAMPLE_REVIEW_DATA),
        ):
            resp = client.post(
                "/api/v1/reviews/summarize",
                json={"query": "Summarize reviews for Budget Phone X1"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["product_name"] == "Budget Phone X1"
        assert data["total_reviews"] == 142

    def test_response_contains_all_required_fields(self):
        """Response schema has all required fields."""
        with patch(
            "app.api.v1.reviews._agent.process",
            new_callable=AsyncMock,
            return_value=AgentResponse(success=True, data=SAMPLE_REVIEW_DATA),
        ):
            resp = client.post(
                "/api/v1/reviews/summarize",
                json={"query": "review for phone"},
            )
        data = resp.json()
        required = (
            "product_id", "product_name", "total_reviews", "sentiment_score",
            "average_rating", "rating_distribution", "positive_themes",
            "negative_themes", "overall_summary", "cached", "agent",
        )
        for field in required:
            assert field in data, f"Missing: {field}"

    def test_optional_product_id_accepted(self):
        """product_id is optional; when provided it is passed to agent."""
        with patch(
            "app.api.v1.reviews._agent.process",
            new_callable=AsyncMock,
            return_value=AgentResponse(success=True, data=SAMPLE_REVIEW_DATA),
        ) as mock_process:
            resp = client.post(
                "/api/v1/reviews/summarize",
                json={"query": "review for phone", "product_id": "PROD001"},
            )
        assert resp.status_code == 200
        call_context = mock_process.call_args[0][1]  # second positional arg = context
        assert call_context["product_id"] == "PROD001"

    def test_query_too_short_returns_422(self):
        """Query shorter than 3 characters fails validation."""
        resp = client.post("/api/v1/reviews/summarize", json={"query": "ok"})
        assert resp.status_code == 422

    def test_max_reviews_out_of_range_returns_422(self):
        """max_reviews outside 5-50 range fails validation."""
        resp = client.post(
            "/api/v1/reviews/summarize",
            json={"query": "review for phone", "max_reviews": 100},
        )
        assert resp.status_code == 422

    def test_agent_failure_returns_500(self):
        """When agent returns success=False, endpoint returns 500."""
        with patch(
            "app.api.v1.reviews._agent.process",
            new_callable=AsyncMock,
            return_value=AgentResponse(
                success=False, data={}, error="DB connection lost"
            ),
        ):
            resp = client.post(
                "/api/v1/reviews/summarize",
                json={"query": "review summary"},
            )
        assert resp.status_code == 500
        assert "DB connection lost" in resp.json()["detail"]

    def test_cached_response_field_true(self):
        """When agent returns cached=True, response reflects it."""
        cached_data = {**SAMPLE_REVIEW_DATA, "cached": True}
        with patch(
            "app.api.v1.reviews._agent.process",
            new_callable=AsyncMock,
            return_value=AgentResponse(success=True, data=cached_data),
        ):
            resp = client.post(
                "/api/v1/reviews/summarize",
                json={"query": "reviews for phone", "product_id": "PROD001"},
            )
        assert resp.status_code == 200
        assert resp.json()["cached"] is True
