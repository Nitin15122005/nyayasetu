# -*- coding: utf-8 -*-
"""
evaluation/runners/end_to_end.py

Mirrors the manual pipeline trace from the Phase 2 handoff, automated:
translate -> analyze -> compliance -> qa, for one uploaded document, with
per-stage completion tracked explicitly. A stage that raises is recorded
as incomplete for THAT stage but doesn't abort the remaining ones where
possible, so a translation failure doesn't hide whether analyze/compliance
still work on the (untranslated) original text — exactly the kind of
"was a stage silently bypassed" question this suite exists to answer.
"""

from __future__ import annotations

from evaluation.config.schema import REPO_ROOT
from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


@register("end_to_end")
class EndToEndEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "end_to_end", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        stages_completed = []
        stage_latencies = {}
        fixtures_dir = REPO_ROOT / "evaluation" / "datasets" / "raw" / "fixtures"

        # Stage: analyze (this is the stage that does translation
        # internally too, per document_analyzer.py's Phase 1 pipeline —
        # tracked as one combined "analyze" stage since /api/analyze
        # doesn't expose translation as a separately-callable step)
        analyze_resp = self.api.analyze(fixtures_dir / record.file_path)
        stage_latencies["analyze"] = analyze_resp.latency_ms
        if not analyze_resp.ok:
            return {"output": {"stages_completed": stages_completed, "stage_latencies": stage_latencies},
                     "latency_ms": sum(stage_latencies.values()),
                     "error": f"analyze failed: {analyze_resp.error or analyze_resp.status_code}"}
        stages_completed.append("analyze")
        analyze_body = analyze_resp.json_body or {}
        session_id = analyze_body.get("session_id")

        # Stage: compliance (independent call, same source text)
        compliance_resp = self.api.compliance(analyze_body.get("original_text", "") or record.question)
        stage_latencies["compliance"] = compliance_resp.latency_ms
        if compliance_resp.ok:
            stages_completed.append("compliance")

        # Stage: qa (depends on the session opened by analyze)
        final_output_valid = False
        if session_id and record.question:
            qa_resp = self.api.qa(session_id, record.question)
            stage_latencies["qa"] = qa_resp.latency_ms
            if qa_resp.ok:
                stages_completed.append("qa")
                final_output_valid = bool((qa_resp.json_body or {}).get("answer"))

        return {
            "output": {
                "stages_completed": stages_completed,
                "stage_latencies": stage_latencies,
                "final_output_valid": final_output_valid,
                "document_type": analyze_body.get("document_type"),
            },
            "latency_ms": sum(stage_latencies.values()),
        }

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        valid = [(r, o) for r, o in zip(records, outcomes) if o.get("output")]

        completion_rates = []
        stage_latency_agg: dict[str, list[float]] = {}
        for r, o in valid:
            expected = r.expected_stages
            completed = o["output"]["stages_completed"]
            completion_rates.append(len(set(completed) & set(expected)) / len(expected) if expected else 0.0)
            for stage, lat in o["output"]["stage_latencies"].items():
                stage_latency_agg.setdefault(stage, []).append(lat)

        stage_completion = MetricResult(
            name="stage_completion_rate",
            value=(sum(completion_rates) / len(completion_rates)) if completion_rates else None,
            n=len(completion_rates),
        )

        stage_breakdown = {
            stage: {"mean_ms": sum(lats) / len(lats), "n": len(lats)}
            for stage, lats in stage_latency_agg.items()
        }
        stage_latency = MetricResult(name="stage_latency_breakdown", value=None,
                                      n=sum(len(v) for v in stage_latency_agg.values()), details=stage_breakdown)

        validity = [1.0 if o["output"]["final_output_valid"] else 0.0 for _, o in valid]
        final_validity = MetricResult(name="final_output_validity",
                                       value=(sum(validity) / len(validity)) if validity else None, n=len(validity))

        return {
            "stage_completion_rate": stage_completion,
            "stage_latency_breakdown": stage_latency,
            "final_output_validity": final_validity,
        }
