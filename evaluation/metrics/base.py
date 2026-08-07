# -*- coding: utf-8 -*-
"""
evaluation/metrics/base.py — the Metric contract

Every metric in this package is a pure function of (predictions,
references, **kwargs) -> MetricResult. "Pure" matters: metrics never call
the network, never read files, never depend on run order — that's what
makes them independently unit-testable and safe to reuse across suites
(e.g. latency_metrics.percentiles() is used by translation, retrieval,
performance, and robustness alike).

Evaluators call metrics AFTER collecting raw (prediction, reference,
extra) data from the harness — metrics never see the harness.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol


@dataclass
class MetricResult:
    name: str
    value: Optional[float]          # the headline aggregate number; None if not computable (e.g. empty input)
    details: dict[str, Any] = field(default_factory=dict)   # per-item breakdown, histograms, etc.
    n: int = 0                       # number of items the metric was computed over

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value, "n": self.n, "details": self.details}


class Metric(Protocol):
    """Structural type — a metric is any callable matching this signature.
    Using Protocol (not ABC) so plain functions qualify without
    subclassing boilerplate; see retrieval_metrics.py etc. for examples."""

    def __call__(self, predictions: list, references: list, **kwargs) -> MetricResult:
        ...
