"""Tests for performance metrics tracker."""

import pytest
from app.core.metrics import record_latency, get_p95, get_metrics_summary, reset_metrics


@pytest.fixture(autouse=True)
def _reset():
    reset_metrics()
    yield
    reset_metrics()


def test_record_latency_adds_sample():
    record_latency("/api/v1/chat", 150.0)
    summary = get_metrics_summary()
    assert "/api/v1/chat" in summary
    assert summary["/api/v1/chat"]["sample_count"] == 1


def test_p95_returns_none_on_empty():
    assert get_p95("/nonexistent") is None


def test_p95_returns_value_with_samples():
    for i in range(100):
        record_latency("/test", float(i))
    p95 = get_p95("/test")
    assert p95 is not None
    assert 90 <= p95 <= 99


def test_get_metrics_summary_includes_all_endpoints():
    record_latency("/a", 10.0)
    record_latency("/b", 20.0)
    summary = get_metrics_summary()
    assert "/a" in summary
    assert "/b" in summary
    assert summary["/a"]["p50_ms"] == 10.0
    assert summary["/b"]["p50_ms"] == 20.0


def test_metrics_rolling_window_max_200():
    for i in range(250):
        record_latency("/overflow", float(i))
    summary = get_metrics_summary()
    assert summary["/overflow"]["sample_count"] == 200
