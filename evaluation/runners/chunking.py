# -*- coding: utf-8 -*-
"""
evaluation/runners/chunking.py

Runs modules/m2_rag/ingest.py's real chunk_pages() via the direct-import
adapter (no HTTP surface exists for this stage) and checks the
chunk-size distribution against the embedding model's token budget — the
oversize_chunk_rate metric exists specifically because of the risk
flagged in the Phase 2 handoff: 512-char chunks vs a ~128-token default
max_seq_length can silently truncate longer chunks before embedding.
This suite does NOT change the chunking parameters — it only measures
what the current ones produce.
"""

from __future__ import annotations

from pathlib import Path

from evaluation.config.schema import REPO_ROOT
from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


@register("chunking")
class ChunkingEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "chunking", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        from evaluation.harness.direct_adapter import chunk_pdf
        pdf_path = REPO_ROOT / "data" / "statutes" / record.source_pdf
        if not pdf_path.exists():
            # Also try the eval fixtures dir, for chunking tests that don't
            # depend on the (gitignored) real statute PDFs.
            pdf_path = REPO_ROOT / "evaluation" / "datasets" / "raw" / "fixtures" / record.source_pdf
        chunks = chunk_pdf(pdf_path)
        lengths = [len(c["text"]) for c in chunks]
        return {"output": {"n_chunks": len(chunks), "lengths": lengths}}

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        approx_chars_per_token = self.config.params.get("approx_chars_per_token", 4.5)
        max_tokens = self.config.params.get("embedder_max_seq_length_tokens", 128)
        oversize_char_threshold = max_tokens * approx_chars_per_token

        valid = [o["output"] for o in outcomes if o.get("output")]
        counts = [o["n_chunks"] for o in valid]
        all_lengths = [l for o in valid for l in o["lengths"]]

        chunk_count = MetricResult(name="chunk_count", value=(sum(counts) / len(counts)) if counts else None,
                                    n=len(counts), details={"per_document": counts})

        length_stats = MetricResult(
            name="chunk_length_stats",
            value=(sum(all_lengths) / len(all_lengths)) if all_lengths else None,
            n=len(all_lengths),
            details={"min": min(all_lengths) if all_lengths else None,
                     "max": max(all_lengths) if all_lengths else None},
        )

        oversize = [1.0 if l > oversize_char_threshold else 0.0 for l in all_lengths]
        oversize_rate = MetricResult(
            name="oversize_chunk_rate",
            value=(sum(oversize) / len(oversize)) if oversize else None,
            n=len(oversize),
            details={"threshold_chars": oversize_char_threshold,
                     "note": "chunks over this size may be silently truncated by the "
                              "embedding model's default max_seq_length before vectorization"},
        )

        expectation_hits = []
        for r, o in zip(records, outcomes):
            if not o.get("output"):
                continue
            n = o["output"]["n_chunks"]
            if r.expected_min_chunks is not None:
                expectation_hits.append(n >= r.expected_min_chunks)
            if r.expected_max_chunks is not None:
                expectation_hits.append(n <= r.expected_max_chunks)
        boundary_sanity = MetricResult(
            name="boundary_sanity",
            value=(sum(1 for h in expectation_hits if h) / len(expectation_hits)) if expectation_hits else None,
            n=len(expectation_hits),
        )

        return {
            "chunk_count": chunk_count,
            "chunk_length_stats": length_stats,
            "oversize_chunk_rate": oversize_rate,
            "boundary_sanity": boundary_sanity,
        }
