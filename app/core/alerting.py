"""Lightweight rolling-window failure alerting."""

import time
import logging
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

ALERT_THRESHOLD = 10  # failures within window to trigger CRITICAL
ALERT_WINDOW_SECONDS = 300  # 5 minutes

_failure_counts: dict[str, deque] = defaultdict(lambda: deque(maxlen=100))


def record_failure(component: str) -> None:
    """Record a failure and log CRITICAL if threshold exceeded."""
    _failure_counts[component].append(time.time())
    cutoff = time.time() - ALERT_WINDOW_SECONDS
    recent = [t for t in _failure_counts[component] if t > cutoff]
    if len(recent) >= ALERT_THRESHOLD:
        logger.critical(
            "ALERT: %s has %d failures in the last %ds — check immediately!",
            component,
            len(recent),
            ALERT_WINDOW_SECONDS,
        )


def get_alert_status() -> dict:
    """Return current failure counts within the alert window per component."""
    now = time.time()
    cutoff = now - ALERT_WINDOW_SECONDS
    return {
        component: len([t for t in times if t > cutoff])
        for component, times in _failure_counts.items()
    }


def reset_alerts() -> None:
    """Clear all failure records (for tests)."""
    _failure_counts.clear()
