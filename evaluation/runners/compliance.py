# -*- coding: utf-8 -*-
"""
evaluation/runners/compliance.py

Evaluates the compliance SCORE/GRADE as a whole via POST /api/compliance
— including the regex-based new-reference counting that runs independently
of the RAG/AI mapping tiers (see the Phase 2 pipeline trace). A document
with zero old references scores 100/A by construction; datasets should
include such cases deliberately, not just documents expected to score low.
"""

from __future__ import annotations

from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register

_GRADE_ORDER = ["F", "D", "C", "B", "A"]


@register("compliance")
class ComplianceEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "compliance", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        resp = self.api.compliance(record.text)
        if not resp.ok:
            return {"output": None, "latency_ms": resp.latency_ms,
                     "error": resp.error or f"HTTP {resp.status_code}"}
        body = resp.json_body or {}
        return {"output": {"score": body.get("score"), "grade": body.get("grade")}, "latency_ms": resp.latency_ms}

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        valid = [(r, o) for r, o in zip(records, outcomes) if o.get("output") and o["output"].get("score") is not None]

        errors = []
        in_range = []
        grade_matches = []
        grade_within_one = []
        for r, o in valid:
            score = o["output"]["score"]
            mid = (r.expected_score_min + r.expected_score_max) / 2
            errors.append(abs(score - mid))
            in_range.append(r.expected_score_min <= score <= r.expected_score_max)
            if r.expected_grade:
                actual_grade = o["output"]["grade"]
                grade_matches.append(actual_grade == r.expected_grade)
                if actual_grade in _GRADE_ORDER and r.expected_grade in _GRADE_ORDER:
                    dist = abs(_GRADE_ORDER.index(actual_grade) - _GRADE_ORDER.index(r.expected_grade))
                    grade_within_one.append(dist <= 1)

        score_mae = MetricResult(
            name="score_mae", value=(sum(errors) / len(errors)) if errors else None, n=len(errors),
            details={"in_expected_range_rate": (sum(1 for x in in_range if x) / len(in_range)) if in_range else None},
        )
        grade_exact = MetricResult(name="grade_exact_match",
                                    value=(sum(1 for g in grade_matches if g) / len(grade_matches)) if grade_matches else None,
                                    n=len(grade_matches))
        grade_within = MetricResult(name="grade_within_one_band",
                                     value=(sum(1 for g in grade_within_one if g) / len(grade_within_one)) if grade_within_one else None,
                                     n=len(grade_within_one))

        latencies = [o.get("latency_ms", 0.0) for o in outcomes]
        from evaluation.metrics.latency_metrics import latency_percentiles
        return {
            "score_mae": score_mae,
            "grade_exact_match": grade_exact,
            "grade_within_one_band": grade_within,
            "latency_ms": latency_percentiles(latencies),
        }
