"""Tests for LLM response cache."""

import pytest
from app.agents.base import AgentResponse
from app.core.llm_cache import (
    get_cached_llm_response,
    set_cached_llm_response,
    reset_llm_cache,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_llm_cache()
    yield
    reset_llm_cache()


def _make_response(success=True, data=None) -> AgentResponse:
    return AgentResponse(success=success, data=data or {"answer": "test"})


def test_cache_miss_returns_none():
    assert get_cached_llm_response("agent", "unknown query") is None


def test_cache_hit_after_set():
    resp = _make_response()
    set_cached_llm_response("agent", "hello", resp)
    cached = get_cached_llm_response("agent", "hello")
    assert cached is not None
    assert cached.success is True
    assert cached.data["answer"] == "test"


def test_cached_response_has_from_cache_metadata():
    resp = _make_response()
    set_cached_llm_response("agent", "hello", resp)
    cached = get_cached_llm_response("agent", "hello")
    assert cached.metadata["from_llm_cache"] is True


def test_failed_response_not_cached():
    resp = _make_response(success=False, data={})
    set_cached_llm_response("agent", "fail query", resp)
    assert get_cached_llm_response("agent", "fail query") is None


def test_different_queries_different_keys():
    resp1 = _make_response(data={"answer": "one"})
    resp2 = _make_response(data={"answer": "two"})
    set_cached_llm_response("agent", "query one", resp1)
    set_cached_llm_response("agent", "query two", resp2)
    assert get_cached_llm_response("agent", "query one").data["answer"] == "one"
    assert get_cached_llm_response("agent", "query two").data["answer"] == "two"


def test_same_query_normalized_matches():
    resp = _make_response()
    set_cached_llm_response("agent", "  Hello World  ", resp)
    cached = get_cached_llm_response("agent", "hello world")
    assert cached is not None


def test_reset_llm_cache_clears_singleton():
    resp = _make_response()
    set_cached_llm_response("agent", "hello", resp)
    assert get_cached_llm_response("agent", "hello") is not None
    reset_llm_cache()
    assert get_cached_llm_response("agent", "hello") is None
