# -*- coding: utf-8 -*-
"""
evaluation/reporting/compare.py — ablation-style run comparison

Purpose-built for exactly the comparison the Phase 3 handoff called out:
"run compliance evaluation once with the RAG tier dead (today's
baseline) and once with the emoji fix applied, and compare." More
generally: any two (or more) runs of the same suite, labeled however the
caller wants ("before" / "after", "gpt-vs-groq", ...).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from evaluation.reporting import plots
from evaluation.results.schema import SuiteResult
from evaluation.results.store import load_run


def compare_runs(suite: str, run_labels: dict[str, str], out_dir: Path,
                   metrics_to_plot: Optional[list[str]] = None) -> dict:
    """
    run_labels: {"before": "20260101-...", "after": "latest"} — label ->
    run_id (or "latest").

    Returns a dict {label: SuiteResult} and writes one comparison PNG per
    metric in metrics_to_plot (defaults to every scalar metric present in
    ALL provided runs) into out_dir/figures/.
    """
    results: dict[str, SuiteResult] = {label: load_run(suite, run_id) for label, run_id in run_labels.items()}

    all_metric_names = [set(r.aggregate_metrics.keys()) for r in results.values()]
    common_metrics = set.intersection(*all_metric_names) if all_metric_names else set()
    if metrics_to_plot is None:
        metrics_to_plot = sorted(
            name for name in common_metrics
            if all(isinstance(r.aggregate_metrics[name].get("value"), (int, float)) for r in results.values())
        )

    figures_dir = out_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    for metric_name in metrics_to_plot:
        runs_for_plot = {label: {metric_name: r.aggregate_metrics[metric_name].get("value")}
                          for label, r in results.items()}
        plots.plot_run_comparison(runs_for_plot, metric_name, figures_dir / f"compare_{suite}_{metric_name}.png")

    return results


def diff_summary(results: dict[str, SuiteResult]) -> dict:
    """Plain-dict summary of what changed, metric by metric — useful for
    printing to console or embedding in a report without generating figures."""
    labels = list(results.keys())
    if len(labels) < 2:
        return {}
    baseline_label = labels[0]
    baseline = results[baseline_label]
    summary = {}
    for metric_name, m in baseline.aggregate_metrics.items():
        baseline_val = m.get("value") if isinstance(m, dict) else None
        row = {baseline_label: baseline_val}
        for label in labels[1:]:
            other = results[label].aggregate_metrics.get(metric_name, {})
            other_val = other.get("value") if isinstance(other, dict) else None
            row[label] = other_val
            if isinstance(baseline_val, (int, float)) and isinstance(other_val, (int, float)):
                row[f"{label}_delta"] = other_val - baseline_val
        summary[metric_name] = row
    return summary
