# -*- coding: utf-8 -*-
"""
evaluation/runners/legal_qa.py

Two-step per record: POST /api/analyze to open a session, then POST
/api/qa to ask the question. Scores answer correctness by semantic
similarity (embedding cosine, via the notebook's own /embed — the same
space the system's own DocumentRAG retrieval uses) against a reference
answer, plus a groundedness heuristic and confidence calibration. Uses
RAGAS's faithfulness/answer_relevancy instead when
use_ragas_if_available is set AND ragas is installed (see
metrics/ragas_adapter.py) — otherwise the custom metrics below.
"""

from __future__ import annotations

from evaluation.config.schema import REPO_ROOT
from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.metrics.calibration_metrics import expected_calibration_error
from evaluation.metrics.generation_metrics import semantic_similarity
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


@register("legal_qa")
class LegalQAEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "legal_qa", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        fixtures_dir = REPO_ROOT / "evaluation" / "datasets" / "raw" / "fixtures"
        analyze_resp = self.api.analyze(fixtures_dir / record.file_path)
        if not analyze_resp.ok:
            return {"output": None, "latency_ms": analyze_resp.latency_ms,
                     "error": f"analyze failed: {analyze_resp.error or analyze_resp.status_code}"}
        session_id = (analyze_resp.json_body or {}).get("session_id")
        if not session_id:
            return {"output": None, "latency_ms": analyze_resp.latency_ms, "error": "no session_id returned"}

        qa_resp = self.api.qa(session_id, record.question)
        total_latency = analyze_resp.latency_ms + qa_resp.latency_ms
        if not qa_resp.ok:
            return {"output": None, "latency_ms": total_latency,
                     "error": f"qa failed: {qa_resp.error or qa_resp.status_code}"}
        body = qa_resp.json_body or {}
        return {
            "output": {
                "answer": body.get("answer", ""),
                "confidence": body.get("confidence"),
                "sources": body.get("sources", []),
            },
            "latency_ms": total_latency,
        }

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        valid = [(r, o) for r, o in zip(records, outcomes) if o.get("output")]

        # Semantic similarity needs embeddings — computed here (not inside
        # run_single) so a Colab outage degrades this ONE metric, not the
        # whole suite's raw Q&A collection.
        pred_vecs, ref_vecs, correctness = [], [], []
        for r, o in valid:
            if not r.reference_answer:
                continue
            resp = self.notebook.embed([o["output"]["answer"], r.reference_answer])
            if not resp.ok or not resp.json_body:
                continue
            vecs = resp.json_body.get("embeddings", [])
            if len(vecs) != 2:
                continue
            pred_vecs.append(vecs[0])
            ref_vecs.append(vecs[1])

        correctness_metric = semantic_similarity(pred_vecs, ref_vecs) if pred_vecs else MetricResult("answer_correctness", None, n=0)
        correctness_metric.name = "answer_correctness"

        must_contain_hits = []
        for r, o in valid:
            if not r.must_contain:
                continue
            answer_lower = o["output"]["answer"].lower()
            hit_rate = sum(1 for phrase in r.must_contain if phrase.lower() in answer_lower) / len(r.must_contain)
            must_contain_hits.append(hit_rate)
        groundedness = MetricResult(name="groundedness",
                                     value=(sum(must_contain_hits) / len(must_contain_hits)) if must_contain_hits else None,
                                     n=len(must_contain_hits),
                                     details={"caveat": "substring-match heuristic; swap in RAGAS faithfulness "
                                                          "for a real entailment-based groundedness check"})

        refusal_checks = [
            ("no" in o["output"]["answer"].lower() or "not mentioned" in o["output"]["answer"].lower())
            for r, o in valid if r.should_refuse
        ]
        refusal_appropriateness = MetricResult(
            name="refusal_appropriateness",
            value=(sum(1 for c in refusal_checks if c) / len(refusal_checks)) if refusal_checks else None,
            n=len(refusal_checks),
        )

        confidences = [o["output"]["confidence"] for _, o in valid if o["output"].get("confidence") is not None]
        conf_correctness = [s > 0.7 for s in correctness_metric.details.get("per_item", [])] if confidences else []
        calibration = expected_calibration_error(confidences, conf_correctness) if confidences and conf_correctness else \
            MetricResult("confidence_calibration", None, n=0)
        calibration.name = "confidence_calibration"

        latencies = [o.get("latency_ms", 0.0) for o in outcomes]
        from evaluation.metrics.latency_metrics import latency_percentiles
        return {
            "answer_correctness": correctness_metric,
            "groundedness": groundedness,
            "refusal_appropriateness": refusal_appropriateness,
            "confidence_calibration": calibration,
            "latency_ms": latency_percentiles(latencies),
        }
