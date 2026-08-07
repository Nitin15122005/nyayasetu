# -*- coding: utf-8 -*-
"""
evaluation/runners/summarization.py

document_analyzer.py's summarize_document() (Colab BART first, Groq
fallback) is only reachable through /api/analyze — there's no standalone
/api/summarize backend route — so this suite uploads a plain-text fixture
wrapped as a minimal document and reads the `summary` field of the
analysis response. engine tracking isn't available from this endpoint
today (the response doesn't say which engine produced the summary) —
recorded as a known limitation rather than guessed at.
"""

from __future__ import annotations

from evaluation.config.schema import REPO_ROOT
from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.metrics.generation_metrics import rouge_l
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


@register("summarization")
class SummarizationEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "summarization", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as f:
            f.write(record.source_text)
            tmp_path = f.name
        try:
            # /api/analyze only accepts pdf/jpg/jpeg/png/webp — a .txt
            # fixture would be rejected by the endpoint's own extension
            # check, so this suite requires PDF fixtures in practice.
            # Left explicit rather than silently renaming the extension.
            from pathlib import Path
            resp = self.api.analyze(Path(tmp_path))
        finally:
            import os
            os.unlink(tmp_path)

        if not resp.ok:
            return {"output": None, "latency_ms": resp.latency_ms,
                     "error": resp.error or f"HTTP {resp.status_code} (note: summarization dataset "
                                              f"records need a real PDF fixture, not raw text — see docstring)"}
        body = resp.json_body or {}
        return {"output": {"summary": body.get("summary", "")}, "latency_ms": resp.latency_ms}

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        valid = [(r, o) for r, o in zip(records, outcomes) if o.get("output") and o["output"].get("summary")]

        predictions = [o["output"]["summary"] for _, o in valid]
        references = [r.reference_summary for r, _ in valid]
        rouge = rouge_l(predictions, references) if predictions else MetricResult("rouge_l", None, n=0)

        length_ok = [len(o["output"]["summary"]) <= r.max_length * 8 for r, o in valid]  # chars, generous vs word-based max_length
        length_compliance = MetricResult(
            name="length_compliance",
            value=(sum(1 for x in length_ok if x) / len(length_ok)) if length_ok else None,
            n=len(length_ok),
        )

        engine_distribution = MetricResult(
            name="engine_distribution", value=None, n=0,
            details={"limitation": "POST /api/analyze does not report which summarization "
                                     "engine (Colab BART vs Groq fallback) produced the summary — "
                                     "would need a small backend change to expose this"},
        )

        latencies = [o.get("latency_ms", 0.0) for o in outcomes]
        from evaluation.metrics.latency_metrics import latency_percentiles
        return {
            "rouge_l": rouge,
            "length_compliance": length_compliance,
            "engine_distribution": engine_distribution,
            "latency_ms": latency_percentiles(latencies),
        }
