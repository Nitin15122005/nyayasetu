# -*- coding: utf-8 -*-
"""
evaluation/runners/translation.py

Calls POST /api/translate (the full Colab NLLB -> Gemini -> Groq cascade,
as a real user experiences it) and scores against reference translations
with chrF. Also reports engine_distribution — which tier actually
answered each record — because, per the Phase 1/2 handoff, the cascade's
behavior IS part of what needs evaluating, not just final text quality.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from evaluation.config.schema import REPO_ROOT
from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.metrics.generation_metrics import chrf
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


@register("translation")
class TranslationEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "translation", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        resp = self.api.translate(record.source_text, record.source_lang, record.target_lang)
        if not resp.ok:
            return {"output": None, "latency_ms": resp.latency_ms,
                     "error": resp.error or f"HTTP {resp.status_code}: {resp.text_body[:200]}"}
        body = resp.json_body or {}
        return {
            "output": {
                "translated_text": body.get("translated_text", ""),
                "engine": body.get("engine", "unknown"),
                "confidence": body.get("confidence"),
            },
            "latency_ms": resp.latency_ms,
        }

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        valid = [(r, o) for r, o in zip(records, outcomes) if o.get("output")]
        predictions = [o["output"]["translated_text"] for _, o in valid]
        references = [r.reference_translation for r, _ in valid]

        chrf_result = chrf(predictions, references) if predictions else MetricResult("chrf", None, n=0)

        engines = [o["output"]["engine"] for _, o in valid]
        engine_dist = MetricResult(
            name="engine_distribution", value=None, n=len(engines),
            details=dict(Counter(engines)),
        )

        expected_engine_matches = [
            1.0 if r.expected_engine and o["output"]["engine"] == r.expected_engine else 0.0
            for r, o in valid if r.expected_engine
        ]
        exact_match_engine = MetricResult(
            name="exact_match_engine_expected",
            value=(sum(expected_engine_matches) / len(expected_engine_matches)) if expected_engine_matches else None,
            n=len(expected_engine_matches),
        )

        latencies = [o.get("latency_ms", 0.0) for o in outcomes]
        from evaluation.metrics.latency_metrics import latency_percentiles
        latency = latency_percentiles(latencies)

        return {
            "chrf": chrf_result,
            "engine_distribution": engine_dist,
            "exact_match_engine_expected": exact_match_engine,
            "latency_ms": latency,
        }
