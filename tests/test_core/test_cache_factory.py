"""Tests for app.core.cache_factory.create_cache()."""

from unittest.mock import MagicMock, patch
from app.core.cache_factory import create_cache
from app.core.cache import TTLCache, RedisCache


def test_create_cache_falls_back_to_ttlcache():
    """When Redis is unreachable, returns TTLCache."""
    cache = create_cache(
        redis_url="redis://bad-host:9999",
        key_prefix="x:",
        ttl=60,
        max_size=100,
        name="TestCache",
    )
    assert isinstance(cache, TTLCache)


def test_create_cache_ttlcache_ttl():
    """TTLCache fallback has correct default_ttl."""
    cache = create_cache(
        redis_url="redis://bad-host:9999",
        key_prefix="x:",
        ttl=300,
        max_size=50,
    )
    assert isinstance(cache, TTLCache)
    assert cache._default_ttl == 300


def test_create_cache_uses_redis_when_available():
    """When Redis ping succeeds, returns RedisCache."""
    mock_client = MagicMock()
    mock_redis_cache = MagicMock(spec=RedisCache)
    mock_redis_cache._client = mock_client

    with patch("app.core.cache_factory.RedisCache", return_value=mock_redis_cache):
        cache = create_cache(
            redis_url="redis://localhost:6379",
            key_prefix="test:",
            ttl=60,
            max_size=100,
            name="TestCache",
        )
    assert cache is mock_redis_cache
    mock_client.ping.assert_called_once()


def test_create_cache_redis_key_prefix():
    """RedisCache receives the correct key_prefix."""
    mock_client = MagicMock()
    mock_redis_cache = MagicMock(spec=RedisCache)
    mock_redis_cache._client = mock_client
    mock_redis_cache._key_prefix = "myprefix:"

    with patch(
        "app.core.cache_factory.RedisCache", return_value=mock_redis_cache
    ) as mock_cls:
        create_cache(
            redis_url="redis://localhost:6379",
            key_prefix="myprefix:",
            ttl=60,
            max_size=100,
        )
    _, kwargs = mock_cls.call_args
    assert kwargs.get("key_prefix") == "myprefix:"
