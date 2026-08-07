# -*- coding: utf-8 -*-
"""
evaluation/metrics/latency_metrics.py — timing and load metrics

predictions here are latency_ms floats (one per request), captured by
harness/client.py — never trusted from server-reported timing, always
measured wall-clock from the caller's side, which is what a real user
experiences. Used by every suite (latency_ms is in every suite's metrics
list) and specifically by performance.yaml for throughput/error rate.
"""

from __future__ import annotations

from evaluation.metrics.base import MetricResult


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * p
    f, c = int(k), min(int(k) + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def latency_percentiles(latencies_ms: list[float], percentiles=(50, 95, 99), **_) -> MetricResult:
    if not latencies_ms:
        return MetricResult(name="latency_percentiles", value=None, n=0)
    s = sorted(latencies_ms)
    details = {f"p{p}": round(_percentile(s, p / 100), 2) for p in percentiles}
    details["min"] = round(s[0], 2)
    details["max"] = round(s[-1], 2)
    details["mean"] = round(sum(s) / len(s), 2)
    return MetricResult(name="latency_percentiles", value=details.get("p50"), n=len(s), details=details)


def throughput_rps(n_requests: int, duration_s: float, **_) -> MetricResult:
    if duration_s <= 0:
        return MetricResult(name="throughput_rps", value=None, n=n_requests)
    return MetricResult(name="throughput_rps", value=n_requests / duration_s, n=n_requests)


def error_rate(statuses: list[bool], **_) -> MetricResult:
    """statuses: list[bool] where True = request succeeded (evaluator's
    own notion of success, not just HTTP 2xx — e.g. a clean validation
    4xx on a robustness record is a SUCCESS, not an error)."""
    if not statuses:
        return MetricResult(name="error_rate", value=None, n=0)
    failures = sum(1 for ok in statuses if not ok)
    return MetricResult(name="error_rate", value=failures / len(statuses), n=len(statuses),
                         details={"failures": failures, "total": len(statuses)})
