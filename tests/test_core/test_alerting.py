"""Tests for rolling-window failure alerting."""

import logging
import time
import pytest
from unittest.mock import patch

from app.core.alerting import (
    record_failure,
    get_alert_status,
    reset_alerts,
    ALERT_THRESHOLD,
)


@pytest.fixture(autouse=True)
def _clean_alerts():
    reset_alerts()
    yield
    reset_alerts()


class TestRecordFailure:
    def test_single_failure_counted(self):
        record_failure("test-agent")
        status = get_alert_status()
        assert status["test-agent"] == 1

    def test_multiple_failures_accumulated(self):
        for _ in range(5):
            record_failure("agent-a")
        assert get_alert_status()["agent-a"] == 5

    def test_separate_components(self):
        record_failure("agent-a")
        record_failure("agent-b")
        record_failure("agent-b")
        status = get_alert_status()
        assert status["agent-a"] == 1
        assert status["agent-b"] == 2


class TestAlertThreshold:
    def test_critical_log_at_threshold(self, caplog):
        with caplog.at_level(logging.CRITICAL, logger="app.core.alerting"):
            for _ in range(ALERT_THRESHOLD):
                record_failure("overloaded")
        assert any("ALERT" in r.message for r in caplog.records)

    def test_no_critical_below_threshold(self, caplog):
        with caplog.at_level(logging.CRITICAL, logger="app.core.alerting"):
            for _ in range(ALERT_THRESHOLD - 1):
                record_failure("fine")
        assert not any("ALERT" in r.message for r in caplog.records)


class TestAlertStatus:
    def test_empty_status(self):
        assert get_alert_status() == {}

    def test_expired_failures_excluded(self):
        record_failure("old")
        # Move time past the window
        with patch("app.core.alerting.time") as mock_time:
            mock_time.time.return_value = time.time() + 400  # past 300s window
            status = get_alert_status()
            assert status.get("old", 0) == 0

    def test_reset_clears_all(self):
        record_failure("x")
        record_failure("y")
        reset_alerts()
        assert get_alert_status() == {}
