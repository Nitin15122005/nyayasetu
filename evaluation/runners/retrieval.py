# -*- coding: utf-8 -*-
"""
evaluation/runners/retrieval.py

Evaluates the statute ChromaDB RAG tier IN ISOLATION from the downstream
Groq extraction step — i.e. pure vector-search quality: given a query
embedding (via the same backend/local_models.embed_texts() path
RAGMapping itself uses), does ChromaDB return the chunks a human would
consider relevant, in the right order? See ipc_bns_mapping.py for the
full end-to-end tier (including the LLM extraction and the 0.3 confidence
gate) — deliberately a separate suite so a retrieval regression and an
extraction-prompt regression don't get conflated into one number.
"""

from __future__ import annotations

from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.metrics.retrieval_metrics import mrr, ndcg_at_k, precision_at_k, recall_at_k
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


@register("retrieval")
class RetrievalEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "retrieval", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        from evaluation.harness.direct_adapter import embed_query_via_colab, query_chromadb_direct
        top_k = self.config.params.get("top_k", 3)

        query_vec = embed_query_via_colab(record.query)
        if query_vec is None:
            return {"output": None, "error": "Colab embedding unavailable — record skipped, not scored as a failure"}

        results = query_chromadb_direct(query_vec, top_k=top_k)
        retrieved_ids = results.get("ids", [[]])[0]
        distances = results.get("distances", [[]])[0]
        return {"output": {"retrieved_ids": retrieved_ids, "distances": distances}}

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        top_k = self.config.params.get("top_k", 3)
        valid = [(r, o) for r, o in zip(records, outcomes) if o.get("output")]
        skipped = len(records) - len(valid)

        predictions = [o["output"]["retrieved_ids"] for _, o in valid]
        references = [{"relevant_ids": r.relevant_chunk_ids, "relevance_grades": r.relevance_grades} for r, _ in valid]

        results = {
            f"precision_at_{top_k}": precision_at_k(predictions, references, k=top_k),
            f"recall_at_{top_k}": recall_at_k(predictions, references, k=top_k),
            "mrr": mrr(predictions, references),
            f"ndcg_at_{top_k}": ndcg_at_k(predictions, references, k=top_k),
        }
        if skipped:
            results["_note"] = MetricResult(
                name="_note", value=None, n=skipped,
                details={"skipped_records_colab_unreachable": skipped},
            )

        latencies = [o.get("latency_ms", 0.0) for o in outcomes]
        from evaluation.metrics.latency_metrics import latency_percentiles
        results["latency_ms"] = latency_percentiles(latencies)
        return results
