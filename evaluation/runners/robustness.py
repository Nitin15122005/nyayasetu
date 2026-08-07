# -*- coding: utf-8 -*-
"""
evaluation/runners/robustness.py

Sends each dataset record's payload to its declared endpoint via the raw
HTTP escape hatch (client.raw()) and scores the response against the
record's own `expected_behavior` contract — see
metrics/robustness_metrics.py for why "didn't crash" isn't the bar.
"""

from __future__ import annotations

from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.metrics.robustness_metrics import crash_rate, error_message_quality, graceful_degradation_rate
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


@register("robustness")
class RobustnessEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "robustness", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        resp = self.api.raw("POST", record.endpoint, json=record.payload)
        crashed = resp.error is not None and resp.status_code == -1
        return {
            "output": {
                "status_code": resp.status_code,
                "body_text": resp.text_body or str(resp.json_body or ""),
                "crashed": crashed,
                "category": record.category,
                "expected_behavior": record.expected_behavior,
            },
            "latency_ms": resp.latency_ms,
        }

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        valid_outputs = [o["output"] for o in outcomes if o.get("output")]

        graceful = graceful_degradation_rate(valid_outputs)
        crashes = crash_rate(valid_outputs)
        msg_quality = error_message_quality(valid_outputs)

        by_category: dict[str, list[float]] = {}
        for o in valid_outputs:
            by_category.setdefault(o["category"], []).append(1.0 if not o["crashed"] else 0.0)
        graceful.details["by_category_survival_rate"] = {
            cat: sum(v) / len(v) for cat, v in by_category.items()
        }

        latencies = [o.get("latency_ms", 0.0) for o in outcomes]
        from evaluation.metrics.latency_metrics import latency_percentiles
        return {
            "graceful_degradation_rate": graceful,
            "crash_rate": crashes,
            "error_message_quality": msg_quality,
            "latency_ms": latency_percentiles(latencies),
        }
