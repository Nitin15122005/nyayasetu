# -*- coding: utf-8 -*-
"""
evaluation/runners/document_analysis.py

Evaluates the full document analyzer via POST /api/analyze: document-type
classification, overall risk verdict, and missing-clause detection,
against human-labeled fixture documents.
"""

from __future__ import annotations

from evaluation.config.schema import REPO_ROOT
from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.metrics.classification_metrics import exact_match
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


def _set_f1(predicted: list[str], expected: list[str]) -> float:
    p, e = set(predicted), set(expected)
    if not p and not e:
        return 1.0
    if not p or not e:
        return 0.0
    tp = len(p & e)
    precision, recall = tp / len(p), tp / len(e)
    return 0.0 if (precision + recall) == 0 else 2 * precision * recall / (precision + recall)


@register("document_analysis")
class DocumentAnalysisEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "document_analysis", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        fixtures_dir = REPO_ROOT / "evaluation" / "datasets" / "raw" / "fixtures"
        file_path = fixtures_dir / record.file_path
        resp = self.api.analyze(file_path)
        if not resp.ok:
            return {"output": None, "latency_ms": resp.latency_ms,
                     "error": resp.error or f"HTTP {resp.status_code}: {resp.text_body[:200]}"}
        body = resp.json_body or {}
        missing = [c.get("clause_name", c) if isinstance(c, dict) else c
                   for c in body.get("missing_clauses", [])]
        return {
            "output": {
                "document_type": body.get("document_type"),
                "overall_risk": (body.get("signature_verdict") or {}).get("verdict")
                                or body.get("overall_risk"),
                "missing_clauses": missing,
                "session_id": body.get("session_id"),
            },
            "latency_ms": resp.latency_ms,
        }

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        valid = [(r, o) for r, o in zip(records, outcomes) if o.get("output")]

        doc_type_pred = [o["output"]["document_type"] for _, o in valid]
        doc_type_ref = [r.expected_document_type for r, _ in valid]
        doc_type_acc = exact_match(doc_type_pred, doc_type_ref)

        risk_pairs = [(o["output"]["overall_risk"], r.expected_overall_risk)
                      for r, o in valid if r.expected_overall_risk]
        risk_agreement = exact_match([p for p, _ in risk_pairs], [e for _, e in risk_pairs]) if risk_pairs else \
            MetricResult("risk_level_agreement", None, n=0)
        risk_agreement.name = "risk_level_agreement"

        f1_scores = [_set_f1(o["output"]["missing_clauses"], r.expected_missing_clauses)
                     for r, o in valid if r.expected_missing_clauses]
        missing_clause_f1 = MetricResult(name="missing_clause_f1",
                                          value=(sum(f1_scores) / len(f1_scores)) if f1_scores else None,
                                          n=len(f1_scores))

        verdict_agreement = MetricResult(name="verdict_agreement", value=risk_agreement.value, n=risk_agreement.n)

        latencies = [o.get("latency_ms", 0.0) for o in outcomes]
        from evaluation.metrics.latency_metrics import latency_percentiles
        return {
            "doc_type_accuracy": doc_type_acc,
            "risk_level_agreement": risk_agreement,
            "missing_clause_f1": missing_clause_f1,
            "verdict_agreement": verdict_agreement,
            "latency_ms": latency_percentiles(latencies),
        }
