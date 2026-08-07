# -*- coding: utf-8 -*-
"""
evaluation/cli.py — single entrypoint for the evaluation framework

    python -m evaluation.cli list-suites
    python -m evaluation.cli run --suite translation [--limit 20]
    python -m evaluation.cli run --all [--limit 5]
    python -m evaluation.cli report --suite translation [--run latest]
    python -m evaluation.cli report --all-latest
    python -m evaluation.cli compare --suite ipc_bns_mapping --runs before=<run_id> after=latest

Every subcommand is a thin wrapper over the library code in
config/, runners/, results/, reporting/ — this file has no logic of its
own beyond argument parsing and printing, so everything it does is also
directly callable from a notebook or a script for programmatic use.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from evaluation.config.schema import EVAL_ROOT, list_available_suites, load_experiment_config
from evaluation.runners.registry import get_evaluator_class, list_registered_suites


def cmd_list_suites(args) -> int:
    configured = set(list_available_suites())
    registered = set(list_registered_suites())
    print(f"{'suite':<22} {'config':<8} {'evaluator':<10}")
    for suite in sorted(configured | registered):
        print(f"{suite:<22} {'yes' if suite in configured else 'no':<8} {'yes' if suite in registered else 'no':<10}")
    return 0


def _run_one(suite: str, limit: int | None) -> int:
    print(f"\n=== Running suite: {suite} ===")
    try:
        config = load_experiment_config(suite, overrides={"sample_limit": limit} if limit else None)
        evaluator_cls = get_evaluator_class(suite)
        evaluator = evaluator_cls(config)
        result = evaluator.run()
    except FileNotFoundError as e:
        print(f"  SKIPPED — {e}")
        return 1
    except Exception as e:
        print(f"  FAILED — {type(e).__name__}: {e}")
        return 1

    print(f"  run_id: {result.manifest.run_id}")
    print(f"  records: {result.n_records} ({result.n_errors} errors)")
    for name, m in result.aggregate_metrics.items():
        val = m.get("value") if isinstance(m, dict) else None
        print(f"  {name}: {val if val is not None else '—'}")
    return 0


def cmd_run(args) -> int:
    if args.all:
        suites = list_registered_suites()
        failures = sum(_run_one(s, args.limit) for s in suites)
        return 1 if failures else 0
    if not args.suite:
        print("error: --suite <name> or --all is required", file=sys.stderr)
        return 2
    return _run_one(args.suite, args.limit)


def cmd_report(args) -> int:
    from evaluation.results.store import load_run
    from evaluation.reporting.report_builder import build_report

    if args.all_latest:
        suites = list_registered_suites()
        results = []
        for s in suites:
            try:
                results.append(load_run(s, "latest"))
            except FileNotFoundError:
                continue
        if not results:
            print("No runs found for any suite yet — run `python -m evaluation.cli run --all` first.")
            return 1
    else:
        if not args.suite:
            print("error: --suite <name> or --all-latest is required", file=sys.stderr)
            return 2
        results = [load_run(args.suite, args.run)]

    out_dir = Path(args.out) if args.out else (EVAL_ROOT / "results" / "reports" / "latest")
    report_path = build_report(results, out_dir)
    print(f"Report written to: {report_path}")
    return 0


def cmd_compare(args) -> int:
    from evaluation.reporting.compare import compare_runs, diff_summary

    run_labels = {}
    for pair in args.runs:
        if "=" not in pair:
            print(f"error: --runs entries must be label=run_id, got '{pair}'", file=sys.stderr)
            return 2
        label, run_id = pair.split("=", 1)
        run_labels[label] = run_id

    out_dir = Path(args.out) if args.out else (EVAL_ROOT / "results" / "reports" / f"compare_{args.suite}")
    results = compare_runs(args.suite, run_labels, out_dir)
    summary = diff_summary(results)
    print(f"\nComparison for suite '{args.suite}':")
    for metric_name, row in summary.items():
        print(f"  {metric_name}: {row}")
    print(f"\nFigures written under: {out_dir / 'figures'}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m evaluation.cli", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list-suites", help="show every suite with config/evaluator registration status")
    p_list.set_defaults(func=cmd_list_suites)

    p_run = sub.add_parser("run", help="run one suite (or all) against the configured dataset")
    p_run.add_argument("--suite", help="suite name, e.g. translation")
    p_run.add_argument("--all", action="store_true", help="run every registered suite")
    p_run.add_argument("--limit", type=int, default=None, help="cap dataset size for a quick smoke run")
    p_run.set_defaults(func=cmd_run)

    p_report = sub.add_parser("report", help="build a Markdown+figures report from existing run results")
    p_report.add_argument("--suite", help="suite name")
    p_report.add_argument("--run", default="latest", help="run_id, or 'latest' (default)")
    p_report.add_argument("--all-latest", action="store_true", help="report across every suite's latest run")
    p_report.add_argument("--out", default=None, help="output directory (default: evaluation/results/reports/latest)")
    p_report.set_defaults(func=cmd_report)

    p_compare = sub.add_parser("compare", help="compare multiple runs of one suite (e.g. before/after a fix)")
    p_compare.add_argument("--suite", required=True)
    p_compare.add_argument("--runs", nargs="+", required=True, metavar="label=run_id",
                             help="e.g. --runs before=20260101-120000-abc123 after=latest")
    p_compare.add_argument("--out", default=None)
    p_compare.set_defaults(func=cmd_compare)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
