# -*- coding: utf-8 -*-
"""
evaluation/runners/ipc_bns_mapping.py

Full end-to-end evaluation of LexValidator.get_mapping()'s 3-tier cascade
(RAG -> hardcoded table -> Groq zero-shot) via POST /api/compliance,
scored against a labeled expected_bns per (act, section). Reports
tier_distribution alongside accuracy specifically so a change like the
RAGMapping initialization fix (Phase 3 handoff) is visible as a shift in
WHICH tier answers, not just a possible change in the accuracy number.
"""

from __future__ import annotations

from collections import Counter

from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.metrics.calibration_metrics import expected_calibration_error
from evaluation.metrics.classification_metrics import exact_match
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


def _tier_of(mapping: dict) -> str:
    if mapping.get("rag_sourced"):
        return "rag"
    if mapping.get("ai_generated"):
        return "ai"
    if mapping.get("new") in (None, "UNKNOWN"):
        return "not_found"
    return "hardcoded_table"


@register("ipc_bns_mapping")
class IPCBNSMappingEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "ipc_bns_mapping", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        # Compliance takes free text; embed the reference inside a short
        # sentence the same way the dataset's text_context is meant to,
        # so SectionExtractor's regex actually finds it (extraction
        # phrasing sensitivity is itself a robustness finding, tracked
        # separately in robustness.yaml, not silently worked around here).
        text = record.text_context or f"Charged under {record.act} {record.section}."
        resp = self.api.compliance(text)
        if not resp.ok:
            return {"output": None, "latency_ms": resp.latency_ms,
                     "error": resp.error or f"HTTP {resp.status_code}"}
        body = resp.json_body or {}
        key = f"{record.act} {record.section}"
        match = next((m for m in body.get("mappings", []) if m.get("old") == key), None)
        if match is None:
            return {"output": {"found": False, "tier": "not_found"}, "latency_ms": resp.latency_ms}
        return {
            "output": {
                "found": True,
                "bns": match.get("new"),
                "name": match.get("name"),
                "confidence": match.get("confidence"),
                "tier": _tier_of(match),
            },
            "latency_ms": resp.latency_ms,
        }

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        valid = [(r, o) for r, o in zip(records, outcomes) if o.get("output")]

        predictions = [o["output"].get("bns", "UNKNOWN") if o["output"].get("found") else "UNKNOWN" for _, o in valid]
        references = [r.expected_bns for r, _ in valid]
        acc = exact_match(predictions, references)

        tiers = [o["output"]["tier"] for _, o in valid]
        tier_dist = MetricResult(name="tier_distribution", value=None, n=len(tiers), details=dict(Counter(tiers)))

        confidences = [o["output"].get("confidence") for _, o in valid if o["output"].get("confidence") is not None]
        correctness = [p == r for p, r, (_, o) in zip(predictions, references, valid) if o["output"].get("confidence") is not None]
        calibration = expected_calibration_error(confidences, correctness) if confidences else MetricResult("expected_calibration_error", None, n=0)

        latencies = [o.get("latency_ms", 0.0) for o in outcomes]
        from evaluation.metrics.latency_metrics import latency_percentiles
        return {
            "exact_match": acc,
            "tier_distribution": tier_dist,
            "confidence_calibration": calibration,
            "latency_ms": latency_percentiles(latencies),
        }
