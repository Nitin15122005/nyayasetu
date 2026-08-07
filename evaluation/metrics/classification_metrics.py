# -*- coding: utf-8 -*-
"""
evaluation/metrics/classification_metrics.py

predictions, references: list[str] (or any hashable label) of equal length.
Used by: ipc_bns_mapping (exact section-code match), document_analysis
(document-type / risk-level agreement), compliance (grade agreement).
"""

from __future__ import annotations

from collections import Counter

from evaluation.metrics.base import MetricResult


def exact_match(predictions: list, references: list, **_) -> MetricResult:
    if not predictions:
        return MetricResult(name="exact_match", value=None, n=0)
    matches = [1.0 if p == r else 0.0 for p, r in zip(predictions, references)]
    return MetricResult(name="exact_match", value=sum(matches) / len(matches), n=len(matches),
                         details={"per_item": matches})


def accuracy(predictions: list, references: list, **_) -> MetricResult:
    """Alias of exact_match under the more familiar name for classification tasks."""
    r = exact_match(predictions, references)
    return MetricResult(name="accuracy", value=r.value, n=r.n, details=r.details)


def precision_recall_f1(predictions: list, references: list, positive_label=None, **_) -> MetricResult:
    """
    Macro-averaged precision/recall/F1 across all labels seen in
    `references`, unless `positive_label` is given for binary scoring.
    """
    labels = sorted(set(references) | set(predictions)) if positive_label is None else [positive_label]
    per_label = {}
    for label in labels:
        tp = sum(1 for p, r in zip(predictions, references) if p == label and r == label)
        fp = sum(1 for p, r in zip(predictions, references) if p == label and r != label)
        fn = sum(1 for p, r in zip(predictions, references) if p != label and r == label)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        per_label[str(label)] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}

    if not per_label:
        return MetricResult(name="f1", value=None, n=len(predictions))
    macro_f1 = sum(v["f1"] for v in per_label.values()) / len(per_label)
    return MetricResult(name="f1", value=macro_f1, n=len(predictions), details={"per_label": per_label})


def confusion_matrix(predictions: list, references: list, **_) -> MetricResult:
    labels = sorted(set(references) | set(predictions))
    idx = {label: i for i, label in enumerate(labels)}
    matrix = [[0] * len(labels) for _ in labels]
    for p, r in zip(predictions, references):
        matrix[idx[r]][idx[p]] += 1
    return MetricResult(
        name="confusion_matrix", value=None, n=len(predictions),
        details={"labels": labels, "matrix": matrix},
    )


def label_distribution(labels: list, **_) -> MetricResult:
    """Not a scoring metric — a diagnostic showing how predicted/expected
    labels are distributed, useful for spotting a model that always
    predicts the majority class."""
    counts = dict(Counter(labels))
    return MetricResult(name="label_distribution", value=None, n=len(labels), details=counts)
