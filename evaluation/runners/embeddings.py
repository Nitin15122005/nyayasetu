# -*- coding: utf-8 -*-
"""
evaluation/runners/embeddings.py

Calls the notebook's /embed directly (evaluation.harness.notebook_client),
bypassing the backend, since the embedding contract itself — dimension,
determinism, semantic-neighbor behavior — is a property of the notebook's
model, not of the backend's HTTP wrapping of it.
"""

from __future__ import annotations

import math

from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


@register("embeddings")
class EmbeddingsEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        path = self.config.resolved_dataset_path()
        return load_dataset(path, "embeddings", limit=self.config.sample_limit)

    def run_single(self, record) -> dict:
        resp = self.notebook.embed([record.text])
        if not resp.ok or not resp.json_body:
            return {"output": None, "latency_ms": resp.latency_ms,
                     "error": resp.error or f"HTTP {resp.status_code}"}
        vecs = resp.json_body.get("embeddings", [])
        if not vecs:
            return {"output": None, "latency_ms": resp.latency_ms, "error": "empty embeddings list"}
        return {"output": {"vector": vecs[0]}, "latency_ms": resp.latency_ms}

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        expected_dim = self.config.params.get("expected_dim", 384)
        vectors = {r.id: o["output"]["vector"] for r, o in zip(records, outcomes) if o.get("output")}

        dims = [len(v) for v in vectors.values()]
        dim_consistency = MetricResult(
            name="dimension_consistency",
            value=(sum(1 for d in dims if d == expected_dim) / len(dims)) if dims else None,
            n=len(dims), details={"observed_dims": sorted(set(dims)), "expected": expected_dim},
        )

        self_sims = [_cosine(v, v) for v in vectors.values()]  # should be ~1.0; catches NaN/zero-vector bugs
        self_sim = MetricResult(
            name="cosine_self_similarity",
            value=(sum(self_sims) / len(self_sims)) if self_sims else None, n=len(self_sims),
        )

        neighbor_scores = []
        for r in records:
            if r.expect_close_to and r.expect_close_to in vectors and r.id in vectors:
                neighbor_scores.append(("close", r.id, r.expect_close_to,
                                         _cosine(vectors[r.id], vectors[r.expect_close_to])))
            if r.expect_far_from and r.expect_far_from in vectors and r.id in vectors:
                neighbor_scores.append(("far", r.id, r.expect_far_from,
                                         _cosine(vectors[r.id], vectors[r.expect_far_from])))
        neighbor_sanity = MetricResult(
            name="neighbor_sanity", value=None, n=len(neighbor_scores),
            details={"pairs": [{"relation": rel, "a": a, "b": b, "cosine": s} for rel, a, b, s in neighbor_scores]},
        )

        latencies = [o.get("latency_ms", 0.0) for o in outcomes]
        from evaluation.metrics.latency_metrics import latency_percentiles
        return {
            "dimension_consistency": dim_consistency,
            "cosine_self_similarity": self_sim,
            "neighbor_sanity": neighbor_sanity,
            "latency_ms": latency_percentiles(latencies),
        }
