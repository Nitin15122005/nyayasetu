# -*- coding: utf-8 -*-
"""
evaluation/reporting/report_builder.py — assemble a Markdown report

Turns one or more SuiteResult objects into a single report.md (+ a
figures/ dir of PNGs), suitable for pasting straight into a paper's
results section or attaching to a PR. Deliberately generates Markdown,
not HTML, as the primary artifact — it's diffable in git, renders on
GitHub, and converts to PDF/HTML trivially with pandoc if needed; adding
an HTML variant later is a template addition, not a redesign.

Each suite decides its own figures via _FIGURE_BUILDERS below — a small,
explicit dispatch table rather than every evaluator knowing about
plotting, keeping the plotting concerns in one place.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from evaluation.reporting import plots
from evaluation.results.schema import SuiteResult

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def _fmt_value(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def _build_figures(suite: SuiteResult, figures_dir: Path) -> list[dict]:
    figures = []
    agg = suite.aggregate_metrics
    suite_name = suite.manifest.suite

    def add(fn, *args, caption, **kwargs):
        out_path = figures_dir / f"{suite_name}_{fn.__name__}.png"
        fn(*args, out_path=out_path, **kwargs)
        figures.append({"rel_path": f"figures/{out_path.name}", "caption": caption})

    # Distribution-style metrics (tier_distribution, engine_distribution, ...)
    for metric_name, metric in agg.items():
        details = metric.get("details") if isinstance(metric, dict) else None
        if not isinstance(details, dict):
            continue
        if metric_name.endswith("_distribution"):
            counts = {k: v for k, v in details.items() if isinstance(v, (int, float))}
            if counts:
                add(plots.plot_distribution, counts, title=metric_name, caption=f"{metric_name} ({suite_name})")
        if metric_name == "reliability_bins" or "bins" in details:
            bins_container = details if "bins" in details else None
            if bins_container:
                add(plots.plot_calibration_curve, bins_container, title=f"{suite_name} calibration",
                     caption=f"Reliability diagram ({suite_name})")

    # Latency histogram from raw records, if latency data exists
    latencies = [r.latency_ms for r in suite.records if r.latency_ms]
    if latencies:
        add(plots.plot_latency_histogram, latencies, title=f"{suite_name} latency",
             caption=f"Latency distribution ({suite_name})")

    # Headline scalar-metric bar chart
    scalar_values = {name: m.get("value") for name, m in agg.items()
                      if isinstance(m, dict) and isinstance(m.get("value"), (int, float))}
    if scalar_values:
        add(plots.plot_metric_bar, scalar_values, title=f"{suite_name} headline metrics",
             caption=f"Headline metrics ({suite_name})")

    return figures


def _suite_context(suite: SuiteResult, out_dir: Path) -> dict:
    figures_dir = out_dir / "figures"
    figures = _build_figures(suite, figures_dir)

    metrics_ctx = [
        {"name": name, "value_str": _fmt_value(m.get("value") if isinstance(m, dict) else None),
         "n": (m.get("n") if isinstance(m, dict) else 0)}
        for name, m in suite.aggregate_metrics.items()
    ]

    notes = []
    for name, m in suite.aggregate_metrics.items():
        details = m.get("details") if isinstance(m, dict) else None
        if isinstance(details, dict):
            for key in ("note", "_note", "limitation", "caveat"):
                if key in details:
                    notes.append(f"**{name}**: {details[key]}")

    env = suite.manifest.environment or {}
    cfg = suite.manifest.config or {}
    return {
        "suite": suite.manifest.suite,
        "description": cfg.get("description", ""),
        "run_id": suite.manifest.run_id,
        "status": suite.manifest.status,
        "n_records": suite.n_records,
        "n_errors": suite.n_errors,
        "git_commit": env.get("git_commit"),
        "git_dirty": env.get("git_dirty"),
        "config_hash": cfg.get("config_hash"),
        "metrics": metrics_ctx,
        "figures": figures,
        "notes": notes,
    }


def build_report(suite_results: list[SuiteResult], out_dir: Path,
                   title: str = "NyayaSetu Evaluation Report") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=select_autoescape([]))
    template = env.get_template("report.md.j2")

    context = {
        "title": title,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "suites": [_suite_context(s, out_dir) for s in suite_results],
    }
    rendered = template.render(**context)

    report_path = out_dir / "report.md"
    report_path.write_text(rendered, encoding="utf-8")
    return report_path
