"""Tests for query-level fallback cache."""

import time
import pytest
from unittest.mock import patch

from app.core.query_cache import (
    cache_response,
    get_cached_response,
    reset_query_cache,
    _make_key,
)


@pytest.fixture(autouse=True)
def _clean_cache():
    reset_query_cache()
    yield
    reset_query_cache()


class TestMakeKey:
    def test_deterministic(self):
        assert _make_key("agent", "hello") == _make_key("agent", "hello")

    def test_case_insensitive(self):
        assert _make_key("agent", "Hello World") == _make_key("agent", "hello world")

    def test_strips_whitespace(self):
        assert _make_key("agent", "  hello  ") == _make_key("agent", "hello")

    def test_different_agents_different_keys(self):
        assert _make_key("a", "query") != _make_key("b", "query")


class TestCacheRoundTrip:
    def test_cache_and_retrieve(self):
        cache_response("rec", "best phones", {"items": [1, 2, 3]})
        result = get_cached_response("rec", "best phones")
        assert result is not None
        assert result["items"] == [1, 2, 3]
        assert result["from_cache"] is True
        assert "cache_warning" in result

    def test_miss_returns_none(self):
        assert get_cached_response("rec", "no such query") is None

    def test_expired_entry_returns_none(self):
        cache_response("rec", "old query", {"x": 1})
        # Patch time to simulate expiry
        with patch("app.core.query_cache.time") as mock_time:
            mock_time.time.return_value = time.time() + 90000  # 25 hours
            assert get_cached_response("rec", "old query") is None

    def test_reset_clears_all(self):
        cache_response("rec", "q1", {"a": 1})
        cache_response("rev", "q2", {"b": 2})
        reset_query_cache()
        assert get_cached_response("rec", "q1") is None
        assert get_cached_response("rev", "q2") is None

    def test_does_not_mutate_original(self):
        original = {"value": 42}
        cache_response("rec", "q", original)
        result = get_cached_response("rec", "q")
        result["value"] = 999
        # Original cached data should be unchanged
        result2 = get_cached_response("rec", "q")
        assert result2["value"] == 42
