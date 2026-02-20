"""Tests for POST /api/v1/recommendations endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app
from app.agents.base import AgentResponse


def make_mock_db():
    db = MagicMock()
    return db


def make_success_response(recommendations=None):
    return AgentResponse(
        success=True,
        data={
            "query": "budget phones",
            "recommendations": recommendations or [
                {
                    "id": "PROD001",
                    "name": "Budget Phone X1",
                    "price": "299.99",
                    "brand": "TechCo",
                    "category": "smartphones",
                    "rating": 4.2,
                    "stock": 50,
                    "relevance_score": 0.92,
                    "reason": "Best value in budget segment",
                },
            ],
            "total_found": 1,
            "reasoning_summary": "Found one budget phone under $500.",
            "agent": "recommendation-agent",
        },
    )


@pytest.fixture(autouse=True)
def override_db():
    app.dependency_overrides[get_db] = make_mock_db
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


class TestRecommendationsEndpoint:
    def test_valid_request_returns_200(self):
        """POST with valid query returns 200 and recommendations list."""
        with patch(
            "app.api.v1.recommendations._agent.process",
            new_callable=AsyncMock,
            return_value=make_success_response(),
        ):
            resp = client.post(
                "/api/v1/recommendations",
                json={"query": "budget smartphones under $500", "max_results": 5},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data
        assert data["query"] == "budget phones"
        assert data["total_found"] == 1

    def test_recommendation_item_fields_present(self):
        """Each recommendation contains required fields."""
        with patch(
            "app.api.v1.recommendations._agent.process",
            new_callable=AsyncMock,
            return_value=make_success_response(),
        ):
            resp = client.post(
                "/api/v1/recommendations",
                json={"query": "headphones", "max_results": 3},
            )
        assert resp.status_code == 200
        rec = resp.json()["recommendations"][0]
        for field in ("id", "name", "price", "category", "relevance_score", "reason", "image_url"):
            assert field in rec, f"Missing field: {field}"

    def test_query_too_short_returns_422(self):
        """Query shorter than 3 characters fails validation."""
        resp = client.post("/api/v1/recommendations", json={"query": "ab"})
        assert resp.status_code == 422

    def test_missing_query_returns_422(self):
        """Missing query field fails validation."""
        resp = client.post("/api/v1/recommendations", json={"max_results": 5})
        assert resp.status_code == 422

    def test_agent_failure_returns_500(self):
        """When agent returns success=False, endpoint returns 500."""
        error_response = AgentResponse(
            success=False, data={}, error="LLM timeout"
        )
        with patch(
            "app.api.v1.recommendations._agent.process",
            new_callable=AsyncMock,
            return_value=error_response,
        ):
            resp = client.post(
                "/api/v1/recommendations",
                json={"query": "phones"},
            )
        assert resp.status_code == 500
        assert "LLM timeout" in resp.json()["detail"]

    def test_optional_filters_accepted(self):
        """max_price, min_price, category, min_rating are optional and accepted."""
        with patch(
            "app.api.v1.recommendations._agent.process",
            new_callable=AsyncMock,
            return_value=make_success_response([]),
        ):
            resp = client.post(
                "/api/v1/recommendations",
                json={
                    "query": "smartphones",
                    "max_results": 3,
                    "max_price": 500.0,
                    "min_price": 100.0,
                    "category": "smartphones",
                    "min_rating": 4.0,
                },
            )
        assert resp.status_code == 200

    def test_empty_recommendations_list_valid(self):
        """Empty recommendations list is a valid response."""
        with patch(
            "app.api.v1.recommendations._agent.process",
            new_callable=AsyncMock,
            return_value=AgentResponse(
                success=True,
                data={
                    "query": "unobtainium phone",
                    "recommendations": [],
                    "total_found": 0,
                    "reasoning_summary": "No products matched.",
                    "agent": "recommendation-agent",
                },
            ),
        ):
            resp = client.post(
                "/api/v1/recommendations",
                json={"query": "unobtainium phone"},
            )
        assert resp.json()["total_found"] == 0
        assert resp.json()["recommendations"] == []

    def test_recommendation_image_url_propagates_from_product(self):
        """image_url from product dict is propagated to recommendation schema."""
        test_url = "https://picsum.photos/seed/999/400/300"
        with patch(
            "app.api.v1.recommendations._agent.process",
            new_callable=AsyncMock,
            return_value=make_success_response(recommendations=[
                {
                    "id": "PROD002",
                    "name": "Phone Y",
                    "price": 400.0,
                    "category": "smartphones",
                    "relevance_score": 0.8,
                    "reason": "Good",
                    "image_url": test_url
                }
            ])
        ):
            resp = client.post(
                "/api/v1/recommendations",
                json={"query": "test query"},
            )
        assert resp.status_code == 200
        recs = resp.json()["recommendations"]
        assert len(recs) == 1
        assert recs[0]["image_url"] == test_url
