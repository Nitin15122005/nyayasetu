# -*- coding: utf-8 -*-
"""
evaluation/metrics/robustness_metrics.py

Each robustness record (see datasets/schema.py::RobustnessRecord) encodes
an explicit contract via `expected_behavior` — "what SHOULD happen" — so
these metrics score against that contract, not against "did it not
crash". A 500 with a stack trace leaking to the client (a real finding
from the architectural audit — api.py returns raw str(e) in several
handlers) should score as a FAILURE even though the process didn't crash.
"""

from __future__ import annotations

from evaluation.metrics.base import MetricResult

_LEAKY_MARKERS = ("Traceback (most recent call last)", "  File \"", "raise ", ".py\", line")


def _looks_like_leaked_internals(text: str) -> bool:
    return any(marker in text for marker in _LEAKY_MARKERS)


def graceful_degradation_rate(outcomes: list[dict], **_) -> MetricResult:
    """
    outcomes: list of {"expected_behavior": str, "status_code": int,
                        "body_text": str, "crashed": bool}
    "Graceful" means: matches the declared contract AND doesn't leak
    internals (stack traces, file paths) in the response body.
    """
    if not outcomes:
        return MetricResult(name="graceful_degradation_rate", value=None, n=0)

    graceful_flags = []
    for o in outcomes:
        expected = o.get("expected_behavior", "")
        status = o.get("status_code", -1)
        body = o.get("body_text", "") or ""
        crashed = o.get("crashed", False)

        if crashed:
            graceful_flags.append(False)
            continue
        if _looks_like_leaked_internals(body):
            graceful_flags.append(False)
            continue

        if expected == "clean_4xx":
            graceful_flags.append(400 <= status < 500)
        elif expected == "graceful_fallback":
            graceful_flags.append(200 <= status < 300)
        elif expected == "clear_error_message":
            graceful_flags.append(status >= 400 and len(body) > 0)
        else:
            # Unknown contract type — can't score confidently either way;
            # excluded from the rate rather than silently counted as pass.
            continue

    if not graceful_flags:
        return MetricResult(name="graceful_degradation_rate", value=None, n=0)
    rate = sum(graceful_flags) / len(graceful_flags)
    return MetricResult(name="graceful_degradation_rate", value=rate, n=len(graceful_flags),
                         details={"per_item": graceful_flags})


def crash_rate(outcomes: list[dict], **_) -> MetricResult:
    if not outcomes:
        return MetricResult(name="crash_rate", value=None, n=0)
    crashes = [1.0 if o.get("crashed") else 0.0 for o in outcomes]
    return MetricResult(name="crash_rate", value=sum(crashes) / len(crashes), n=len(crashes),
                         details={"per_item": crashes})


def error_message_quality(outcomes: list[dict], **_) -> MetricResult:
    """Heuristic: an error response is 'quality' if it (a) doesn't leak
    internals, (b) is non-empty, (c) is under 500 chars (not a wall of
    text). This is intentionally a coarse proxy, not a claim of rigor —
    documented as such so nobody over-trusts it in a paper without
    checking the per-item detail."""
    if not outcomes:
        return MetricResult(name="error_message_quality", value=None, n=0)
    scores = []
    for o in outcomes:
        body = o.get("body_text", "") or ""
        status = o.get("status_code", -1)
        if status < 400:
            continue
        ok = bool(body) and not _looks_like_leaked_internals(body) and len(body) < 500
        scores.append(1.0 if ok else 0.0)
    if not scores:
        return MetricResult(name="error_message_quality", value=None, n=0)
    return MetricResult(name="error_message_quality", value=sum(scores) / len(scores), n=len(scores),
                         details={"per_item": scores, "caveat": "coarse heuristic, not a rigor claim"})
