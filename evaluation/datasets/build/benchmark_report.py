# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/benchmark_report.py — single entry point for
the NSLB v1.0 characterization report. READ-ONLY over
evaluation/datasets/raw/*.jsonl and corpus_inventory/* — writes only
under evaluation/reports/.

    python -m evaluation.datasets.build.benchmark_report

Produces, all under evaluation/reports/:
  benchmark_statistics.json        — the full stats dict
  benchmark_summary.md             — the characterization report (Markdown)
  benchmark_summary.pdf            — the same content as a structured PDF
  benchmark_tables.csv             — all 5 tables, concatenated
  tables/table{1..5}_*.csv         — each table individually
  figures/0{1..7}_*.{png,svg}      — 7 charts, print quality (200 DPI PNG + SVG)
"""

from __future__ import annotations

import json

from evaluation.datasets.build.analyze_benchmark import compute_all
from evaluation.datasets.build.benchmark_charts import generate_all as generate_charts
from evaluation.datasets.build.benchmark_pdf import build_pdf
from evaluation.datasets.build.benchmark_summary_md import build_markdown
from evaluation.datasets.build.benchmark_tables import build_all_tables, write_tables
from evaluation.datasets.build.common import REPO_ROOT

REPORTS_DIR = REPO_ROOT / "evaluation" / "reports"


def main() -> None:
    print("Computing benchmark statistics (read-only)...")
    stats = compute_all()

    stats_path = REPORTS_DIR / "benchmark_statistics.json"
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  wrote {stats_path.relative_to(REPO_ROOT)}")

    print("Writing tables (Markdown + CSV)...")
    table_md = write_tables(stats)
    tables = build_all_tables(stats)

    print("Generating figures (PNG + SVG)...")
    figure_names = generate_charts(stats)
    print(f"  wrote {len(figure_names)} figures x2 formats")

    print("Writing benchmark_summary.md...")
    md_content = build_markdown(stats, table_md)
    md_path = REPORTS_DIR / "benchmark_summary.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"  wrote {md_path.relative_to(REPO_ROOT)}")

    print("Writing benchmark_summary.pdf...")
    build_pdf(stats, tables)
    print(f"  wrote {(REPORTS_DIR / 'benchmark_summary.pdf').relative_to(REPO_ROOT)}")

    print("\nDone. All outputs under evaluation/reports/:")
    for p in sorted(REPORTS_DIR.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
