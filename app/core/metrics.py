"""Lightweight in-process performance metrics."""

import statistics
from collections import defaultdict, deque

_latencies: dict[str, deque] = defaultdict(lambda: deque(maxlen=200))


def record_latency(endpoint: str, latency_ms: float) -> None:
    _latencies[endpoint].append(latency_ms)


def get_p95(endpoint: str) -> float | None:
    samples = list(_latencies[endpoint])
    if not samples:
        return None
    if len(samples) < 2:
        return samples[0]
    return statistics.quantiles(samples, n=100)[94]


def get_metrics_summary() -> dict:
    result = {}
    for endpoint, vals in _latencies.items():
        if not vals:
            continue
        samples = list(vals)
        p95 = get_p95(endpoint)
        result[endpoint] = {
            "p50_ms": round(statistics.median(samples), 1),
            "p95_ms": round(p95, 1) if p95 is not None else None,
            "sample_count": len(samples),
        }
    return result


def reset_metrics() -> None:
    _latencies.clear()
