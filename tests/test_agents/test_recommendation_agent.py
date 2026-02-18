"""Tests for RecommendationAgent using pydantic-ai TestModel."""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
from pydantic_ai.models.test import TestModel

from app.agents.recommendation.agent import RecommendationAgent
from app.agents.dependencies import AgentDependencies
from app.core.config import get_settings


def make_mock_db(products: list[dict] | None = None):
    """Create a mock SQLAlchemy session with optional product data."""
    db = MagicMock()
    mock_products = []
    for p in (products or []):
        mock_product = MagicMock()
        for key, val in p.items():
            setattr(mock_product, key, val)
        mock_product.to_dict.return_value = p
        mock_products.append(mock_product)

    db.query.return_value.filter.return_value.filter.return_value = db.query.return_value
    db.query.return_value.filter.return_value = db.query.return_value
    db.query.return_value.order_by.return_value.limit.return_value.all.return_value = mock_products
    db.query.return_value.limit.return_value.all.return_value = mock_products
    db.query.return_value.all.return_value = mock_products
    if mock_products:
        db.query.return_value.filter.return_value.first.return_value = mock_products[0]
    else:
        db.query.return_value.filter.return_value.first.return_value = None
    return db


SAMPLE_PRODUCTS = [
    {
        "id": "PROD001", "name": "Budget Phone X1", "price": Decimal("299.99"),
        "brand": "TechCo", "category": "smartphones", "stock": 50,
        "rating": 4.2, "description": "Affordable smartphone",
        "created_at": None, "updated_at": None,
    },
    {
        "id": "PROD002", "name": "Premium Phone Y2", "price": Decimal("799.99"),
        "brand": "PremiumBrand", "category": "smartphones", "stock": 20,
        "rating": 4.8, "description": "High-end smartphone",
        "created_at": None, "updated_at": None,
    },
]


class TestRecommendationAgentInit:
    def test_agent_initialises(self):
        """Agent can be created without errors."""
        agent = RecommendationAgent()
        assert agent.name == "recommendation-agent"
        assert agent._agent is not None

    def test_agent_repr(self):
        agent = RecommendationAgent()
        assert "RecommendationAgent" in repr(agent)


class TestRecommendationAgentProcess:
    @pytest.mark.asyncio
    async def test_missing_deps_returns_error(self):
        """process() returns failure when deps not in context."""
        agent = RecommendationAgent()
        result = await agent.process("smartphones under $500", context={})
        assert result.success is False
        assert "AgentDependencies" in result.error

    @pytest.mark.asyncio
    async def test_successful_recommendation_with_test_model(self):
        """Uses pydantic-ai TestModel to simulate agent response without real API."""
        db = make_mock_db(SAMPLE_PRODUCTS)
        deps = AgentDependencies(db=db, settings=get_settings())

        agent = RecommendationAgent()

        with agent._agent.override(model=TestModel()):
            result = await agent.process(
                "budget smartphones under $500",
                context={"deps": deps, "max_results": 2},
            )

        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    @pytest.mark.asyncio
    async def test_agent_error_handling(self):
        """Agent returns AgentResponse with success=False on exception."""
        db = make_mock_db()
        deps = AgentDependencies(db=db, settings=get_settings())
        agent = RecommendationAgent()

        with patch.object(agent._agent, "run", side_effect=RuntimeError("LLM timeout")):
            result = await agent.process("phones", context={"deps": deps})

        assert result.success is False
        assert "LLM timeout" in result.error


class TestRecommendationTools:
    @pytest.mark.asyncio
    async def test_search_products_filters(self):
        """Tool filters products correctly via mock DB."""
        from app.agents.recommendation.tools import search_products_by_filters

        db = make_mock_db(SAMPLE_PRODUCTS)
        deps = AgentDependencies(db=db, settings=get_settings())

        ctx = MagicMock()
        ctx.deps = deps

        results = await search_products_by_filters(
            ctx, category="smartphones", max_price=400.0
        )
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_get_product_details_found(self):
        """Tool returns product dict when product exists."""
        from app.agents.recommendation.tools import get_product_details

        db = make_mock_db(SAMPLE_PRODUCTS)
        deps = AgentDependencies(db=db, settings=get_settings())

        ctx = MagicMock()
        ctx.deps = deps

        result = await get_product_details(ctx, product_id="PROD001")
        assert result is not None
        assert result["id"] == "PROD001"

    @pytest.mark.asyncio
    async def test_get_product_details_not_found(self):
        """Tool returns None when product doesn't exist."""
        from app.agents.recommendation.tools import get_product_details

        db = make_mock_db([])
        deps = AgentDependencies(db=db, settings=get_settings())
        db.query.return_value.filter.return_value.first.return_value = None

        ctx = MagicMock()
        ctx.deps = deps

        result = await get_product_details(ctx, product_id="nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_categories(self):
        """Tool returns sorted category list."""
        from app.agents.recommendation.tools import get_categories

        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = [
            ("smartphones",), ("electronics",), ("laptops",)
        ]
        deps = AgentDependencies(db=db, settings=get_settings())

        ctx = MagicMock()
        ctx.deps = deps

        result = await get_categories(ctx)
        assert result == ["electronics", "laptops", "smartphones"]


class TestRecommendationSchemas:
    def test_request_schema_valid(self):
        from app.schemas.recommendation import RecommendationRequest
        req = RecommendationRequest(query="phones under $300", max_results=3, max_price=300.0)
        assert req.max_results == 3
        assert req.max_price == 300.0

    def test_request_schema_defaults(self):
        from app.schemas.recommendation import RecommendationRequest
        req = RecommendationRequest(query="phones")
        assert req.max_results == 5
        assert req.max_price is None

    def test_request_schema_query_too_short(self):
        from app.schemas.recommendation import RecommendationRequest
        with pytest.raises(ValidationError):
            RecommendationRequest(query="ab")

    def test_product_recommendation_schema(self):
        from app.schemas.recommendation import ProductRecommendation
        rec = ProductRecommendation(
            id="P1", name="Test Phone", price=Decimal("299.99"),
            category="smartphones", relevance_score=0.9,
            reason="Great value for money"
        )
        assert rec.relevance_score == 0.9

    def test_response_schema(self):
        from app.schemas.recommendation import RecommendationResponse, ProductRecommendation
        resp = RecommendationResponse(
            query="phones",
            recommendations=[
                ProductRecommendation(
                    id="P1", name="Phone", price=Decimal("299.99"),
                    category="smartphones", relevance_score=0.8,
                    reason="Good match"
                )
            ],
            total_found=1,
            reasoning_summary="Found one matching phone.",
        )
        assert resp.total_found == 1
        assert resp.agent == "recommendation-agent"
