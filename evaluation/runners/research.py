# -*- coding: utf-8 -*-
"""
evaluation/runners/research.py

Evaluates POST /api/research/ask — IndianKanoon retrieval (an external
search API, NOT the internal ChromaDB RAG — see retrieval.py's docstring
for why these are scored separately) + Groq synthesis with inline
citation markers like [1], [2].
"""

from __future__ import annotations

import re

from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register

_CITATION_RE = re.compile(r"\[(\d+)\]")


@register("research")
class ResearchEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "research", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        resp = self.api.research_ask(record.query)
        if not resp.ok:
            return {"output": None, "latency_ms": resp.latency_ms,
                     "error": resp.error or f"HTTP {resp.status_code}"}
        body = resp.json_body or {}
        return {
            "output": {
                "response": body.get("response", ""),
                "citations": body.get("citations", []),
            },
            "latency_ms": resp.latency_ms,
        }

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        valid = [(r, o) for r, o in zip(records, outcomes) if o.get("output")]

        validity_scores = []
        citation_counts = []
        for r, o in valid:
            citations = o["output"]["citations"]
            citation_counts.append(len(citations))
            cited_indices = {int(m) for m in _CITATION_RE.findall(o["output"]["response"])}
            valid_indices = set(range(1, len(citations) + 1))
            # "valid" = every inline [N] marker points at a citation that
            # was actually returned — catches hallucinated citation numbers.
            validity_scores.append(1.0 if cited_indices <= valid_indices and cited_indices else 0.0)

        citation_validity = MetricResult(
            name="citation_validity",
            value=(sum(validity_scores) / len(validity_scores)) if validity_scores else None,
            n=len(validity_scores),
        )
        citation_count = MetricResult(
            name="citation_count",
            value=(sum(citation_counts) / len(citation_counts)) if citation_counts else None,
            n=len(citation_counts),
            details={"below_min_rate": (sum(1 for r, c in zip((r for r, _ in valid), citation_counts) if c < r.min_citations)
                                         / len(citation_counts)) if citation_counts else None},
        )

        # answer_relevancy is a placeholder for RAGAS's answer_relevancy
        # (see metrics/ragas_adapter.py) — left unscored by default here
        # since it requires an LLM judge call, which this suite does not
        # make unless explicitly wired up by the caller.
        answer_relevancy = MetricResult(name="answer_relevancy", value=None, n=0,
                                         details={"note": "wire up metrics.ragas_adapter.evaluate_qa_sample "
                                                            "if an LLM-judge relevancy score is needed"})

        latencies = [o.get("latency_ms", 0.0) for o in outcomes]
        from evaluation.metrics.latency_metrics import latency_percentiles
        return {
            "citation_validity": citation_validity,
            "citation_count": citation_count,
            "answer_relevancy": answer_relevancy,
            "latency_ms": latency_percentiles(latencies),
        }
