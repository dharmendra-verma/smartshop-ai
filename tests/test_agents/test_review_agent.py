"""Tests for ReviewSummarizationAgent, tools, cache, and schemas."""

import time
import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError
from pydantic_ai.models.test import TestModel

from app.agents.review.agent import ReviewSummarizationAgent
from app.agents.dependencies import AgentDependencies
from app.core.cache import TTLCache, RedisCache, get_review_cache, reset_review_cache
from app.core.config import get_settings


def make_mock_db(products=None, reviews=None):
    """Create a mock SQLAlchemy session."""
    db = MagicMock()
    mock_products = []
    for p in (products or []):
        mock_product = MagicMock()
        for key, val in p.items():
            setattr(mock_product, key, val)
        mock_products.append(mock_product)

    if mock_products:
        db.query.return_value.filter.return_value.first.return_value = mock_products[0]
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_products[0]
    else:
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    # Default empty results for group_by and scalar queries
    db.query.return_value.filter.return_value.group_by.return_value.all.return_value = []
    db.query.return_value.filter.return_value.scalar.return_value = None
    db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    return db


SAMPLE_PRODUCTS = [
    {"id": "PROD001", "name": "iPhone 15", "category": "smartphones", "rating": 4.5},
]


# ---- TTLCache Tests ----

class TestTTLCache:
    def test_set_and_get(self):
        cache = TTLCache(default_ttl=60)
        cache.set("key1", {"data": 42})
        assert cache.get("key1") == {"data": 42}

    def test_get_missing_key(self):
        cache = TTLCache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        cache = TTLCache(default_ttl=1)
        cache.set("key1", "value", ttl=1)
        assert cache.get("key1") == "value"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_delete(self):
        cache = TTLCache()
        cache.set("key1", "value")
        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self):
        cache = TTLCache()
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.size == 2
        cache.clear()
        assert cache.size == 0

    def test_max_size_eviction(self):
        cache = TTLCache(max_size=2)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)  # should evict oldest
        assert cache.size == 2
        assert cache.get("c") == 3

    def test_get_review_cache_singleton(self):
        reset_review_cache()
        c1 = get_review_cache()
        c2 = get_review_cache()
        assert c1 is c2
        reset_review_cache()

    def test_fallback_to_ttlcache_when_redis_unavailable(self):
        """get_review_cache falls back to TTLCache when Redis is unreachable."""
        reset_review_cache()
        with patch("app.core.cache.RedisCache") as MockRedis:
            MockRedis.return_value._client.ping.side_effect = ConnectionError("refused")
            cache = get_review_cache()
            assert isinstance(cache, TTLCache)
        reset_review_cache()


# ---- RedisCache Tests (mocked) ----

class TestRedisCache:
    def test_set_and_get(self):
        mock_client = MagicMock()
        mock_client.get.return_value = '{"data": 42}'

        with patch("redis.Redis.from_url", return_value=mock_client):
            cache = RedisCache("redis://localhost:6379/0")
            cache.set("key1", {"data": 42}, ttl=60)
            mock_client.set.assert_called_once_with("smartshop:key1", '{"data": 42}', ex=60)

            result = cache.get("key1")
            assert result == {"data": 42}

    def test_get_missing_key(self):
        mock_client = MagicMock()
        mock_client.get.return_value = None

        with patch("redis.Redis.from_url", return_value=mock_client):
            cache = RedisCache("redis://localhost:6379/0")
            assert cache.get("nonexistent") is None

    def test_get_corrupt_value(self):
        mock_client = MagicMock()
        mock_client.get.return_value = "not-valid-json{{"

        with patch("redis.Redis.from_url", return_value=mock_client):
            cache = RedisCache("redis://localhost:6379/0")
            assert cache.get("bad_key") is None
            mock_client.delete.assert_called_once_with("smartshop:bad_key")

    def test_delete(self):
        mock_client = MagicMock()

        with patch("redis.Redis.from_url", return_value=mock_client):
            cache = RedisCache("redis://localhost:6379/0")
            cache.delete("key1")
            mock_client.delete.assert_called_once_with("smartshop:key1")

    def test_clear(self):
        mock_client = MagicMock()
        mock_client.scan.return_value = (0, ["smartshop:a", "smartshop:b"])

        with patch("redis.Redis.from_url", return_value=mock_client):
            cache = RedisCache("redis://localhost:6379/0")
            cache.clear()
            mock_client.delete.assert_called_once_with("smartshop:a", "smartshop:b")

    def test_custom_prefix(self):
        mock_client = MagicMock()
        mock_client.get.return_value = '"hello"'

        with patch("redis.Redis.from_url", return_value=mock_client):
            cache = RedisCache("redis://localhost:6379/0", key_prefix="myapp:")
            cache.get("key1")
            mock_client.get.assert_called_once_with("myapp:key1")


# ---- Agent Tests ----

class TestReviewAgentInit:
    def test_agent_initialises(self):
        agent = ReviewSummarizationAgent()
        assert agent.name == "review-summarization-agent"
        assert agent._agent is not None

    def test_agent_repr(self):
        agent = ReviewSummarizationAgent()
        assert "ReviewSummarizationAgent" in repr(agent)


class TestReviewAgentProcess:
    @pytest.mark.asyncio
    async def test_missing_deps_returns_error(self):
        agent = ReviewSummarizationAgent()
        result = await agent.process("summarize reviews for iPhone", context={})
        assert result.success is False
        assert "AgentDependencies" in result.error

    @pytest.mark.asyncio
    async def test_successful_run_with_test_model(self):
        db = make_mock_db(SAMPLE_PRODUCTS)
        deps = AgentDependencies(db=db, settings=get_settings())
        agent = ReviewSummarizationAgent()

        with agent._agent.override(model=TestModel()):
            result = await agent.process(
                "Summarize reviews for iPhone 15",
                context={"deps": deps},
            )

        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)

    @pytest.mark.asyncio
    async def test_agent_error_handling(self):
        db = make_mock_db()
        deps = AgentDependencies(db=db, settings=get_settings())
        agent = ReviewSummarizationAgent()

        with patch.object(agent._agent, "run", side_effect=RuntimeError("API error")):
            result = await agent.process(
                "summarize reviews",
                context={"deps": deps},
            )

        assert result.success is False
        assert "API error" in result.error

    @pytest.mark.asyncio
    async def test_cache_hit(self):
        agent = ReviewSummarizationAgent()
        agent._cache.clear()

        cached_data = {
            "product_id": "PROD001",
            "product_name": "iPhone 15",
            "total_reviews": 10,
            "sentiment_score": 0.8,
            "average_rating": 4.2,
            "rating_distribution": {"one_star": 1, "two_star": 1, "three_star": 2, "four_star": 3, "five_star": 3},
            "positive_themes": [],
            "negative_themes": [],
            "overall_summary": "Great phone.",
            "cached": False,
            "agent": "review-summarization-agent",
        }
        agent._cache.set("review_summary:PROD001", cached_data, ttl=300)

        db = make_mock_db()
        deps = AgentDependencies(db=db, settings=get_settings())
        result = await agent.process(
            "summarize reviews",
            context={"deps": deps, "product_id": "PROD001"},
        )

        assert result.success is True
        assert result.data["cached"] is True


# ---- Tool Tests ----

class TestReviewTools:
    @pytest.mark.asyncio
    async def test_find_product_by_id(self):
        from app.agents.review.tools import find_product

        db = make_mock_db(SAMPLE_PRODUCTS)
        deps = AgentDependencies(db=db, settings=get_settings())
        ctx = MagicMock()
        ctx.deps = deps

        result = await find_product(ctx, "PROD001")
        assert result is not None
        assert result["id"] == "PROD001"

    @pytest.mark.asyncio
    async def test_find_product_not_found(self):
        from app.agents.review.tools import find_product

        db = make_mock_db([])
        deps = AgentDependencies(db=db, settings=get_settings())
        ctx = MagicMock()
        ctx.deps = deps

        result = await find_product(ctx, "nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_review_stats_empty(self):
        from app.agents.review.tools import get_review_stats

        db = make_mock_db()
        deps = AgentDependencies(db=db, settings=get_settings())
        ctx = MagicMock()
        ctx.deps = deps

        result = await get_review_stats(ctx, "PROD001")
        assert result["total_reviews"] == 0
        assert result["sentiment_score"] == 0.0
        assert result["average_rating"] == 0.0

    @pytest.mark.asyncio
    async def test_get_review_samples_empty(self):
        from app.agents.review.tools import get_review_samples

        db = make_mock_db()
        # Override the chained query for review samples
        db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
        deps = AgentDependencies(db=db, settings=get_settings())
        ctx = MagicMock()
        ctx.deps = deps

        result = await get_review_samples(ctx, "PROD001")
        assert result["positive_reviews"] == []
        assert result["negative_reviews"] == []
        assert result["counts"]["positive"] == 0


# ---- Schema Tests ----

class TestReviewSchemas:
    def test_request_schema_valid(self):
        from app.schemas.review import ReviewSummarizationRequest
        req = ReviewSummarizationRequest(query="Summarize reviews for iPhone 15")
        assert req.max_reviews == 20
        assert req.product_id is None

    def test_request_schema_with_product_id(self):
        from app.schemas.review import ReviewSummarizationRequest
        req = ReviewSummarizationRequest(query="summarize", product_id="PROD001", max_reviews=30)
        assert req.product_id == "PROD001"
        assert req.max_reviews == 30

    def test_request_schema_query_too_short(self):
        from app.schemas.review import ReviewSummarizationRequest
        with pytest.raises(ValidationError):
            ReviewSummarizationRequest(query="ab")

    def test_response_schema(self):
        from app.schemas.review import (
            ReviewSummarizationResponse, SentimentTheme, RatingDistribution
        )
        resp = ReviewSummarizationResponse(
            product_id="PROD001",
            product_name="iPhone 15",
            total_reviews=100,
            sentiment_score=0.75,
            average_rating=4.2,
            rating_distribution=RatingDistribution(
                one_star=5, two_star=10, three_star=15, four_star=35, five_star=35
            ),
            positive_themes=[
                SentimentTheme(theme="Battery life", confidence=0.8, example_quote="Great battery")
            ],
            negative_themes=[
                SentimentTheme(theme="Price", confidence=0.6)
            ],
            overall_summary="Highly rated smartphone.",
        )
        assert resp.sentiment_score == 0.75
        assert resp.cached is False
        assert resp.agent == "review-summarization-agent"

    def test_sentiment_theme_bounds(self):
        from app.schemas.review import SentimentTheme
        with pytest.raises(ValidationError):
            SentimentTheme(theme="Test", confidence=1.5)
