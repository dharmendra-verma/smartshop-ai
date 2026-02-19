"""TestClient tests for POST /api/v1/price/compare."""
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.agents.base import AgentResponse

client = TestClient(app)


def mock_price_response(products=None, best_deal="Samsung S24", recommendation="Best deal at Walmart."):
    return AgentResponse(
        success=True,
        data={
            "query": "Compare phones",
            "products": products or [{
                "product_id": "PROD001",
                "name": "Samsung S24",
                "our_price": 799.99,
                "competitor_prices": [
                    {"source": "Amazon", "price": 749.99, "is_best": True},
                    {"source": "BestBuy", "price": 829.99, "is_best": False},
                    {"source": "Walmart", "price": 699.99, "is_best": False},
                ],
                "best_price": 699.99,
                "best_source": "Walmart",
                "savings_pct": 12.5,
                "rating": 4.5,
                "brand": "Samsung",
                "category": "smartphones",
                "is_cached": False,
            }],
            "best_deal": best_deal,
            "recommendation": recommendation,
            "total_compared": 1,
            "agent": "price-comparison-agent",
        }
    )


def test_compare_prices_success():
    with patch("app.api.v1.price._agent.process", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = mock_price_response()
        resp = client.post("/api/v1/price/compare", json={"query": "Compare Samsung S24 and Pixel 8"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["best_deal"] == "Samsung S24"
    assert data["total_compared"] == 1
    assert len(data["products"]) == 1
    assert data["products"][0]["best_source"] == "Walmart"


def test_compare_prices_empty_query():
    resp = client.post("/api/v1/price/compare", json={"query": ""})
    assert resp.status_code == 422


def test_compare_prices_query_too_short():
    resp = client.post("/api/v1/price/compare", json={"query": "ab"})
    assert resp.status_code == 422


def test_compare_prices_missing_query():
    resp = client.post("/api/v1/price/compare", json={})
    assert resp.status_code == 422


def test_compare_prices_agent_failure():
    with patch("app.api.v1.price._agent.process", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = AgentResponse(
            success=False, data={}, error="Product not found in catalog"
        )
        resp = client.post("/api/v1/price/compare", json={"query": "Compare XYZ123 and ABC456"})
    assert resp.status_code == 500
    assert "Product not found" in resp.json()["detail"]


def test_compare_prices_competitor_prices_in_response():
    with patch("app.api.v1.price._agent.process", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = mock_price_response()
        resp = client.post("/api/v1/price/compare", json={"query": "Compare Samsung S24 prices"})
    product = resp.json()["products"][0]
    assert len(product["competitor_prices"]) == 3
    sources = [pp["source"] for pp in product["competitor_prices"]]
    assert "Amazon" in sources
    assert "BestBuy" in sources
    assert "Walmart" in sources


def test_compare_prices_savings_pct_present():
    with patch("app.api.v1.price._agent.process", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = mock_price_response()
        resp = client.post("/api/v1/price/compare", json={"query": "best laptop deal"})
    assert resp.json()["products"][0]["savings_pct"] == 12.5
