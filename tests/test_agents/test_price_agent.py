"""Tests for PriceComparisonAgent."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.price.agent import PriceComparisonAgent
from app.agents.base import AgentResponse


@pytest.fixture
def mock_deps(db_session):
    from app.agents.dependencies import AgentDependencies
    from app.core.config import get_settings
    return AgentDependencies(db=db_session, settings=get_settings())


@pytest.mark.asyncio
async def test_process_returns_success(mock_deps):
    agent = PriceComparisonAgent()
    mock_output = MagicMock()
    # Mocking the Pydantic model structure
    product_mock = MagicMock()
    product_mock.product_id = "PROD001"
    product_mock.name = "Samsung Galaxy S24"
    product_mock.our_price = 799.99
    product_mock.competitor_prices = [
        {"source": "Amazon", "price": 749.99, "is_best": True},
        {"source": "BestBuy", "price": 819.99, "is_best": False},
        {"source": "Walmart", "price": 699.99, "is_best": False},
    ]
    product_mock.best_price = 699.99
    product_mock.best_source = "Walmart"
    product_mock.savings_pct = 12.5
    product_mock.rating = 4.5
    product_mock.brand = "Samsung"
    product_mock.category = "smartphones"
    product_mock.is_cached = False
    
    # model_dump needs to be a method that returns a dict
    product_mock.model_dump.return_value = {
        "product_id": "PROD001", "name": "Samsung Galaxy S24",
        "our_price": 799.99, "competitor_prices": product_mock.competitor_prices, 
        "best_price": 699.99,
        "best_source": "Walmart", "savings_pct": 12.5, "rating": 4.5,
        "brand": "Samsung", "category": "smartphones", "is_cached": False,
    }

    mock_output.products = [product_mock]
    mock_output.best_deal = "Samsung Galaxy S24"
    mock_output.recommendation = "Walmart offers the best price at $699.99, saving 12.5%."

    with patch.object(agent._agent, "run", new_callable=AsyncMock) as mock_run:
        result_mock = MagicMock()
        result_mock.output = mock_output
        mock_run.return_value = result_mock
        response = await agent.process(
            "Compare Samsung S24 prices",
            context={"deps": mock_deps},
        )

    assert response.success is True
    assert response.data["best_deal"] == "Samsung Galaxy S24"
    assert response.data["total_compared"] == 1
    assert response.data["agent"] == "price-comparison-agent"


@pytest.mark.asyncio
async def test_process_missing_deps_returns_error():
    agent = PriceComparisonAgent()
    response = await agent.process("Compare phones", context={})
    assert response.success is False
    assert "AgentDependencies not provided" in response.error


@pytest.mark.asyncio
async def test_process_exception_handled(mock_deps):
    agent = PriceComparisonAgent()
    with patch.object(agent._agent, "run", side_effect=Exception("LLM timeout")):
        response = await agent.process("Compare phones", context={"deps": mock_deps})
    assert response.success is False
    assert "Price comparison error" in response.error


def test_price_agent_name():
    agent = PriceComparisonAgent()
    assert agent.name == "price-comparison-agent"


def test_mock_pricing_service_deterministic():
    from app.services.pricing.mock_pricing import MockPricingService
    service = MockPricingService()
    prices1 = service.get_prices("PROD001", 799.99)
    prices2 = service.get_prices("PROD001", 799.99)
    assert prices1 == prices2  # deterministic


def test_mock_pricing_service_sources():
    from app.services.pricing.mock_pricing import MockPricingService
    service = MockPricingService()
    prices = service.get_prices("PROD001", 100.0)
    assert set(prices.keys()) == {"Amazon", "BestBuy", "Walmart"}
    for source, price in prices.items():
        assert price > 0
        assert price != 100.0  # should differ from base
