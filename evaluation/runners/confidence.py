# -*- coding: utf-8 -*-
"""
evaluation/runners/confidence.py

The only evaluator that doesn't call the live system at all — it's a
post-hoc analysis over OTHER suites' already-written results. Run
ipc_bns_mapping / legal_qa / document_analysis first; this suite reads
their `records.jsonl` (via evaluation.results.store.load_run), pulls out
every (confidence, was_it_correct) pair those suites' own metrics already
computed, pools them, and asks: is "confidence" a meaningful number
system-wide, or just a label?
"""

from __future__ import annotations

from dataclasses import dataclass

from evaluation.metrics.base import MetricResult
from evaluation.metrics.calibration_metrics import brier_score, expected_calibration_error, reliability_bins
from evaluation.results.store import load_run
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


@dataclass
class ConfidenceSourceRecord:
    id: str
    suite: str
    run: str = "latest"


@register("confidence")
class ConfidenceEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        sources = self.config.params.get("source_runs", [])
        return [ConfidenceSourceRecord(id=f"source_{s['suite']}", suite=s["suite"], run=s.get("run", "latest"))
                for s in sources]

    def run_single(self, record: ConfidenceSourceRecord) -> dict:
        try:
            suite_result = load_run(record.suite, record.run)
        except FileNotFoundError as e:
            return {"output": None, "error": str(e)}

        pairs = []
        for rec in suite_result.records:
            conf = (rec.output or {}).get("confidence")
            if conf is None:
                continue
            # "correct" isn't stored directly on the record — it's implicit
            # in whether the suite's own accuracy-style metric counted this
            # record as a hit. Suites that want to feed this evaluator
            # should store an explicit `correct` bool in their output dict;
            # documented here as the contract rather than reverse-engineered.
            correct = (rec.output or {}).get("correct")
            if correct is None:
                continue
            pairs.append((float(conf), bool(correct)))

        return {"output": {"pairs": pairs, "run_id": suite_result.manifest.run_id, "n_available": len(pairs)}}

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        all_pairs = []
        per_source = {}
        for r, o in zip(records, outcomes):
            if not o.get("output"):
                continue
            pairs = o["output"]["pairs"]
            per_source[r.suite] = len(pairs)
            all_pairs.extend(pairs)

        if not all_pairs:
            note = MetricResult(
                name="expected_calibration_error", value=None, n=0,
                details={"note": "No (confidence, correct) pairs available. Either the source suites "
                                   "haven't been run yet, or they don't populate an explicit `correct` "
                                   "field in their output dict — see this evaluator's run_single() "
                                   "docstring for the contract.", "per_source_counts": per_source},
            )
            return {"expected_calibration_error": note,
                    "brier_score": MetricResult("brier_score", None, n=0),
                    "reliability_bins": MetricResult("reliability_bins", None, n=0)}

        confidences = [c for c, _ in all_pairs]
        correctness = [ok for _, ok in all_pairs]
        n_bins = self.config.params.get("n_bins", 10)

        ece = expected_calibration_error(confidences, correctness, n_bins=n_bins)
        brier = brier_score(confidences, correctness)
        bins = reliability_bins(confidences, correctness, n_bins=n_bins)
        for m in (ece, brier, bins):
            m.details["per_source_counts"] = per_source
        return {"expected_calibration_error": ece, "brier_score": brier, "reliability_bins": bins}
