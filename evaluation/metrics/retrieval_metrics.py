# -*- coding: utf-8 -*-
"""
evaluation/metrics/retrieval_metrics.py — standard IR metrics

predictions: list[list[str]]   — per query, a ranked list of retrieved item ids
references:  list[dict]        — per query: {"relevant_ids": [...], "relevance_grades": {id: int}}

Used by: retrieval.yaml (ChromaDB statute search) and, via a wrapper,
research.yaml treats IndianKanoon results the same way with binary
relevance (grades default to 1 for anything in relevant_ids).
"""

from __future__ import annotations

import math

from evaluation.metrics.base import MetricResult


def _relevant_set(reference: dict) -> set:
    return set(reference.get("relevant_ids", []))


def precision_at_k(predictions: list[list[str]], references: list[dict], k: int = 3, **_) -> MetricResult:
    scores = []
    for pred, ref in zip(predictions, references):
        relevant = _relevant_set(ref)
        top_k = pred[:k]
        if not top_k:
            scores.append(0.0)
            continue
        hits = sum(1 for item in top_k if item in relevant)
        scores.append(hits / len(top_k))
    value = sum(scores) / len(scores) if scores else None
    return MetricResult(name=f"precision_at_{k}", value=value, n=len(scores), details={"per_query": scores})


def recall_at_k(predictions: list[list[str]], references: list[dict], k: int = 3, **_) -> MetricResult:
    scores = []
    for pred, ref in zip(predictions, references):
        relevant = _relevant_set(ref)
        if not relevant:
            continue   # undefined for queries with no known relevant items — excluded, not zeroed
        top_k = set(pred[:k])
        hits = len(top_k & relevant)
        scores.append(hits / len(relevant))
    value = sum(scores) / len(scores) if scores else None
    return MetricResult(name=f"recall_at_{k}", value=value, n=len(scores), details={"per_query": scores})


def mrr(predictions: list[list[str]], references: list[dict], **_) -> MetricResult:
    """Mean Reciprocal Rank — position of the FIRST relevant item, averaged."""
    scores = []
    for pred, ref in zip(predictions, references):
        relevant = _relevant_set(ref)
        rr = 0.0
        for rank, item in enumerate(pred, start=1):
            if item in relevant:
                rr = 1.0 / rank
                break
        scores.append(rr)
    value = sum(scores) / len(scores) if scores else None
    return MetricResult(name="mrr", value=value, n=len(scores), details={"per_query": scores})


def ndcg_at_k(predictions: list[list[str]], references: list[dict], k: int = 3, **_) -> MetricResult:
    """Normalized Discounted Cumulative Gain. Uses relevance_grades if
    present (graded relevance), else falls back to binary (1 if in
    relevant_ids, else 0)."""
    scores = []
    for pred, ref in zip(predictions, references):
        grades = ref.get("relevance_grades") or {rid: 1 for rid in ref.get("relevant_ids", [])}
        if not grades:
            continue
        dcg = sum(
            grades.get(item, 0) / math.log2(rank + 1)
            for rank, item in enumerate(pred[:k], start=1)
        )
        ideal_order = sorted(grades.values(), reverse=True)[:k]
        idcg = sum(g / math.log2(rank + 1) for rank, g in enumerate(ideal_order, start=1))
        scores.append(dcg / idcg if idcg > 0 else 0.0)
    value = sum(scores) / len(scores) if scores else None
    return MetricResult(name=f"ndcg_at_{k}", value=value, n=len(scores), details={"per_query": scores})
