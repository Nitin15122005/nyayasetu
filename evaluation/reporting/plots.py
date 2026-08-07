# -*- coding: utf-8 -*-
"""
evaluation/reporting/plots.py — matplotlib chart functions

Headless (Agg backend, set below before pyplot is imported anywhere) —
this runs in scripts and CI, never a GUI. Every function takes plain
Python data (not MetricResult objects directly, though callers usually
pass `.details`/`.value` from one) and a Path to save to, and returns
that same Path — small, composable, easy to call from report_builder.py
or ad hoc in a notebook while writing a paper.

Colors are picked once here (not per-call) so every figure in a report
looks like it came from the same document.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from pathlib import Path
from typing import Optional

_ACCENT = "#3949ab"
_MUTED = "#8890a3"
_GOOD = "#2e7d4f"
_BAD = "#b3261e"
_GRID = "#e2e5ea"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": _GRID,
    "axes.grid": True,
    "grid.color": _GRID,
    "grid.linewidth": 0.6,
    "font.size": 10,
})


def _save(fig, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_metric_bar(values: dict[str, Optional[float]], title: str, out_path: Path,
                      ylabel: str = "score") -> Path:
    """One bar per metric name -> scalar value. None values are skipped
    (not plotted as zero, which would misrepresent 'not computed')."""
    items = [(k, v) for k, v in values.items() if v is not None]
    fig, ax = plt.subplots(figsize=(max(4, len(items) * 0.9), 4))
    if not items:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", color=_MUTED)
        ax.set_axis_off()
    else:
        names, vals = zip(*items)
        ax.bar(names, vals, color=_ACCENT)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        plt.xticks(rotation=30, ha="right")
    return _save(fig, out_path)


def plot_latency_histogram(latencies_ms: list[float], out_path: Path, title: str = "Latency distribution") -> Path:
    fig, ax = plt.subplots(figsize=(6, 4))
    if not latencies_ms:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", color=_MUTED)
        ax.set_axis_off()
    else:
        ax.hist(latencies_ms, bins=min(30, max(5, len(latencies_ms) // 3)), color=_ACCENT, edgecolor="white")
        ax.set_xlabel("latency (ms)")
        ax.set_ylabel("count")
        ax.set_title(title)
    return _save(fig, out_path)


def plot_calibration_curve(bins_details: dict, out_path: Path, title: str = "Reliability diagram") -> Path:
    """bins_details is calibration_metrics.expected_calibration_error()'s
    `details["bins"]` — plots avg_confidence vs accuracy per bin against
    the perfect-calibration diagonal."""
    fig, ax = plt.subplots(figsize=(5, 5))
    bins = [b for b in bins_details.get("bins", []) if b.get("n", 0) > 0]
    ax.plot([0, 1], [0, 1], linestyle="--", color=_MUTED, label="perfect calibration")
    if bins:
        xs = [b["avg_confidence"] for b in bins]
        ys = [b["accuracy"] for b in bins]
        sizes = [20 + 200 * (b["n"] / max(bn["n"] for bn in bins)) for b in bins]
        ax.scatter(xs, ys, s=sizes, color=_ACCENT, alpha=0.8, label="observed bins")
    else:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", color=_MUTED)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("predicted confidence")
    ax.set_ylabel("observed accuracy")
    ax.set_title(title)
    ax.legend(loc="upper left", fontsize=8)
    return _save(fig, out_path)


def plot_distribution(counts: dict[str, int], out_path: Path, title: str) -> Path:
    """Bar chart for a categorical distribution — e.g. tier_distribution
    (rag/hardcoded_table/ai/not_found) or engine_distribution."""
    fig, ax = plt.subplots(figsize=(max(4, len(counts) * 1.1), 4))
    if not counts:
        ax.text(0.5, 0.5, "no data", ha="center", va="center", color=_MUTED)
        ax.set_axis_off()
    else:
        ax.bar(list(counts.keys()), list(counts.values()), color=_ACCENT)
        ax.set_ylabel("count")
        ax.set_title(title)
        plt.xticks(rotation=20, ha="right")
    return _save(fig, out_path)


def plot_radar_summary(scores: dict[str, float], out_path: Path, title: str = "Capability summary") -> Path:
    """One axis per capability, 0-1 normalized headline score — the
    single figure meant for a paper's front page / an executive summary.
    Callers are responsible for normalizing scores to [0, 1] beforehand
    (this function doesn't know each metric's natural range)."""
    import math
    items = [(k, v) for k, v in scores.items() if v is not None]
    fig = plt.figure(figsize=(6, 6))
    if len(items) < 3:
        ax = fig.add_subplot(111)
        ax.text(0.5, 0.5, "need >= 3 capabilities with scores for a radar chart",
                 ha="center", va="center", color=_MUTED)
        ax.set_axis_off()
        return _save(fig, out_path)

    labels, values = zip(*items)
    n = len(labels)
    angles = [i / n * 2 * math.pi for i in range(n)] + [0]
    values = list(values) + [values[0]]

    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles, values, color=_ACCENT, linewidth=2)
    ax.fill(angles, values, color=_ACCENT, alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_title(title, pad=20)
    return _save(fig, out_path)


def plot_run_comparison(runs: dict[str, dict[str, Optional[float]]], metric_name: str, out_path: Path) -> Path:
    """Grouped bar chart comparing one metric across multiple runs/labels
    — e.g. 'before RAGMapping fix' vs 'after', for exactly the ablation
    reporting the Phase 3 handoff flagged as needed."""
    fig, ax = plt.subplots(figsize=(max(4, len(runs) * 1.2), 4))
    labels = list(runs.keys())
    values = [runs[l].get(metric_name) for l in labels]
    colors = [_ACCENT if v is not None else _MUTED for v in values]
    ax.bar(labels, [v if v is not None else 0 for v in values], color=colors)
    ax.set_ylabel(metric_name)
    ax.set_title(f"{metric_name} across runs")
    plt.xticks(rotation=20, ha="right")
    return _save(fig, out_path)
