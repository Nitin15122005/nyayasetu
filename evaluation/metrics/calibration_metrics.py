# -*- coding: utf-8 -*-
"""
evaluation/metrics/calibration_metrics.py — confidence calibration

predictions: list[float]  — the system's own confidence for each prediction
                             (RAGMapping's cosine-derived confidence, a
                             clause-risk confidence, a Q&A confidence, ...)
references:  list[bool]   — whether that prediction was actually correct

Used by confidence.yaml, reading (confidence, correct) pairs already
captured in other suites' result files — see runners/confidence.py.

A well-calibrated system's confidence should MEAN something: of all
predictions it says it's 80% confident about, roughly 80% should be
correct. This is exactly what the compliance pipeline's 0.3 RAG
confidence threshold assumes is true — these metrics test that
assumption directly instead of leaving it as a hand-picked constant.
"""

from __future__ import annotations

from evaluation.metrics.base import MetricResult


def expected_calibration_error(predictions: list[float], references: list[bool], n_bins: int = 10, **_) -> MetricResult:
    """ECE: bin predictions by confidence, compare each bin's average
    confidence to its actual accuracy, weight by bin size."""
    if not predictions:
        return MetricResult(name="expected_calibration_error", value=None, n=0)

    bins = [[] for _ in range(n_bins)]
    for conf, correct in zip(predictions, references):
        bin_idx = min(int(conf * n_bins), n_bins - 1)
        bins[bin_idx].append((conf, correct))

    total = len(predictions)
    ece = 0.0
    bin_details = []
    for i, bucket in enumerate(bins):
        if not bucket:
            bin_details.append({"bin": i, "range": [i / n_bins, (i + 1) / n_bins], "n": 0,
                                 "avg_confidence": None, "accuracy": None})
            continue
        avg_conf = sum(c for c, _ in bucket) / len(bucket)
        acc = sum(1 for _, correct in bucket if correct) / len(bucket)
        ece += (len(bucket) / total) * abs(avg_conf - acc)
        bin_details.append({"bin": i, "range": [i / n_bins, (i + 1) / n_bins], "n": len(bucket),
                             "avg_confidence": avg_conf, "accuracy": acc})

    return MetricResult(name="expected_calibration_error", value=ece, n=total,
                         details={"bins": bin_details})


def brier_score(predictions: list[float], references: list[bool], **_) -> MetricResult:
    """Mean squared error between confidence and outcome (0/1). Lower is
    better; 0 is perfect, 0.25 is what a constant 0.5 guesser gets on a
    balanced set."""
    if not predictions:
        return MetricResult(name="brier_score", value=None, n=0)
    scores = [(conf - (1.0 if correct else 0.0)) ** 2 for conf, correct in zip(predictions, references)]
    return MetricResult(name="brier_score", value=sum(scores) / len(scores), n=len(scores),
                         details={"per_item": scores})


def reliability_bins(predictions: list[float], references: list[bool], n_bins: int = 10, **_) -> MetricResult:
    """Just the binned (avg_confidence, accuracy) pairs, for plotting a
    reliability diagram — see reporting/plots.plot_calibration_curve()."""
    ece_result = expected_calibration_error(predictions, references, n_bins=n_bins)
    return MetricResult(name="reliability_bins", value=None, n=ece_result.n,
                         details=ece_result.details)
