"""
End-to-end integration tests for the review summarization flow.

Chain tested: TestClient -> /api/v1/reviews/summarize -> ReviewSummarizationAgent(TestModel) -> JSON.
"""

from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_db
from app.agents.base import AgentResponse


def make_mock_db():
    return MagicMock()


SAMPLE_REVIEW_DATA = {
    "product_id": "PROD001",
    "product_name": "Budget Phone X1",
    "total_reviews": 100,
    "sentiment_score": 0.75,
    "average_rating": 4.0,
    "rating_distribution": {
        "five_star": 40, "four_star": 35, "three_star": 15,
        "two_star": 6, "one_star": 4,
    },
    "positive_themes": [{"theme": "Battery", "confidence": 0.85, "example_quote": None}],
    "negative_themes": [{"theme": "Camera", "confidence": 0.70, "example_quote": None}],
    "overall_summary": "Good value phone.",
    "cached": False,
    "agent": "review-summarization-agent",
}


@pytest.fixture(autouse=True)
def override_db():
    app.dependency_overrides[get_db] = make_mock_db
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


class TestE2EReviews:
    def test_successful_summary_chain(self):
        """Full chain with mocked agent returns 200 and correct schema."""
        import app.api.v1.reviews as review_module

        with patch.object(
            review_module._agent, "process",
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
        assert isinstance(data["positive_themes"], list)
        assert isinstance(data["negative_themes"], list)
        assert "rating_distribution" in data

    def test_product_id_passed_through_to_agent_context(self):
        """product_id from request is correctly forwarded in agent context."""
        import app.api.v1.reviews as review_module

        with patch.object(
            review_module._agent, "process",
            new_callable=AsyncMock,
            return_value=AgentResponse(success=True, data=SAMPLE_REVIEW_DATA),
        ) as mock_process:
            client.post(
                "/api/v1/reviews/summarize",
                json={"query": "reviews", "product_id": "PROD001", "max_reviews": 10},
            )

        _, context = mock_process.call_args[0]
        assert context["product_id"] == "PROD001"
        assert context["max_reviews"] == 10

    def test_agent_error_returns_500(self):
        """Agent failure returns 500 with detail message."""
        import app.api.v1.reviews as review_module

        with patch.object(
            review_module._agent, "process",
            new_callable=AsyncMock,
            return_value=AgentResponse(success=False, data={}, error="Cache timeout"),
        ):
            resp = client.post(
                "/api/v1/reviews/summarize",
                json={"query": "review summary"},
            )

        assert resp.status_code == 500
        assert "Cache timeout" in resp.json()["detail"]

    def test_validation_error_before_agent(self):
        """max_reviews=100 (>50) is rejected by schema before hitting agent."""
        resp = client.post(
            "/api/v1/reviews/summarize",
            json={"query": "review summary", "max_reviews": 100},
        )
        assert resp.status_code == 422

    def test_latency_header_present(self):
        """RequestLoggingMiddleware adds X-Process-Time-Ms to all responses."""
        import app.api.v1.reviews as review_module

        with patch.object(
            review_module._agent, "process",
            new_callable=AsyncMock,
            return_value=AgentResponse(success=True, data=SAMPLE_REVIEW_DATA),
        ):
            resp = client.post(
                "/api/v1/reviews/summarize",
                json={"query": "review summary"},
            )

        assert "X-Process-Time-Ms" in resp.headers

    def test_e2e_scenario_find_budget_phones(self):
        """Jira scenario 1: 'Find budget smartphones under $500' -> recommendations."""
        import app.api.v1.recommendations as rec_module

        with patch.object(
            rec_module._agent, "process",
            new_callable=AsyncMock,
            return_value=AgentResponse(
                success=True,
                data={
                    "query": "budget smartphones under $500",
                    "recommendations": [
                        {
                            "id": "PROD001", "name": "Budget Phone X1",
                            "price": "299.99", "brand": "TechCo",
                            "category": "smartphones", "rating": 4.2,
                            "stock": 50, "relevance_score": 0.95,
                            "reason": "Best value in budget segment",
                        }
                    ],
                    "total_found": 1,
                    "reasoning_summary": "Found 1 budget phone under $500.",
                    "agent": "recommendation-agent",
                },
            ),
        ):
            resp = client.post(
                "/api/v1/recommendations",
                json={"query": "budget smartphones under $500", "max_price": 500},
            )

        assert resp.status_code == 200
        recs = resp.json()["recommendations"]
        assert len(recs) >= 1
        assert float(recs[0]["price"]) < 500

    def test_e2e_scenario_summarize_reviews(self):
        """Jira scenario 2: 'Summarize reviews for [product]' -> sentiment summary."""
        import app.api.v1.reviews as review_module

        with patch.object(
            review_module._agent, "process",
            new_callable=AsyncMock,
            return_value=AgentResponse(success=True, data=SAMPLE_REVIEW_DATA),
        ):
            resp = client.post(
                "/api/v1/reviews/summarize",
                json={"query": "Summarize reviews for Budget Phone X1"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["overall_summary"]
        assert len(data["positive_themes"]) > 0 or len(data["negative_themes"]) > 0

    def test_e2e_scenario_api_timeout_graceful_error(self):
        """Jira scenario 3: API timeout -> api_client returns error dict (no exception)."""
        import requests as req_lib
        from app.ui.api_client import get_recommendations

        with patch(
            "app.ui.api_client.requests.post",
            side_effect=req_lib.exceptions.Timeout("timed out"),
        ):
            result = get_recommendations("http://localhost:8080", "phones")

        assert result["success"] is False
        assert result["error"] is not None
        assert isinstance(result["error"], str)
