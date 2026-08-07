# -*- coding: utf-8 -*-
"""
evaluation/tests/test_infrastructure.py — self-test for the framework itself

IMPORTANT: every number in this file is synthetic/hand-constructed to
verify the PLUMBING (config loading, metric math, storage round-trip,
plotting, report rendering) works correctly. Nothing here calls the
NyayaSetu backend or notebook, and nothing here is or should ever be
mistaken for an evaluation RESULT of NyayaSetu itself — see
evaluation/README.md's "What this phase deliberately did not do".

Runnable standalone (no pytest dependency required, though pytest can
also collect these as functions if pytest is available):

    python -m evaluation.tests.test_infrastructure
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_PASS, _FAIL = [], []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        _PASS.append(name)
        print(f"  PASS  {name}")
    else:
        _FAIL.append((name, detail))
        print(f"  FAIL  {name}  {detail}")


def test_config_layer():
    print("\n[1/7] config layer")
    from evaluation.config.schema import GlobalConfig, load_experiment_config, list_available_suites

    gc = GlobalConfig.load()
    check("GlobalConfig.load() returns a GlobalConfig", isinstance(gc, GlobalConfig))
    check("GlobalConfig has the expected default backend URL",
          gc.backend_base_url == "http://localhost:8001", gc.backend_base_url)

    suites = list_available_suites()
    check("15 experiment YAMLs are discoverable", len(suites) == 15, f"found {len(suites)}: {suites}")

    cfg = load_experiment_config("translation")
    check("load_experiment_config resolves suite='translation'", cfg.suite == "translation")
    check("config_hash() is deterministic",
          cfg.config_hash() == load_experiment_config("translation").config_hash())

    cfg_limited = load_experiment_config("translation", overrides={"sample_limit": 3})
    check("CLI-style override applies (sample_limit)", cfg_limited.sample_limit == 3)


def test_dataset_layer(tmp_dir: Path):
    print("\n[2/7] dataset layer")
    from evaluation.datasets.loader import load_dataset, DatasetValidationError

    good_path = tmp_dir / "translation_synthetic.jsonl"
    good_path.write_text(
        '{"id": "t1", "source_text": "SYNTHETIC — not a real legal document", '
        '"source_lang": "hi", "target_lang": "en", "reference_translation": "SYNTHETIC translation"}\n',
        encoding="utf-8",
    )
    records = load_dataset(good_path, "translation")
    check("loader parses a valid JSONL record", len(records) == 1 and records[0].id == "t1")

    bad_path = tmp_dir / "translation_bad.jsonl"
    bad_path.write_text('{"id": "t1", "not_a_real_field": true}\n', encoding="utf-8")
    try:
        load_dataset(bad_path, "translation")
        check("loader rejects an unknown field", False, "did not raise")
    except DatasetValidationError as e:
        check("loader rejects an unknown field", "unknown field" in str(e), str(e))


def test_metrics_layer():
    print("\n[3/7] metrics layer (pure functions, hand-computed expected values)")
    from evaluation.metrics.classification_metrics import exact_match, precision_recall_f1
    from evaluation.metrics.retrieval_metrics import mrr, precision_at_k, ndcg_at_k
    from evaluation.metrics.calibration_metrics import expected_calibration_error, brier_score
    from evaluation.metrics.latency_metrics import latency_percentiles, error_rate
    from evaluation.metrics.generation_metrics import chrf, rouge_l

    r = exact_match(["A", "B", "C"], ["A", "X", "C"])
    check("exact_match: 2/3 correct -> 0.6667", abs(r.value - (2 / 3)) < 1e-6, r.value)

    r = precision_at_k([["a", "b", "x"]], [{"relevant_ids": ["a", "b", "c"]}], k=3)
    check("precision_at_3: 2 of top-3 relevant -> 0.6667", abs(r.value - (2 / 3)) < 1e-6, r.value)

    r = mrr([["x", "b", "a"]], [{"relevant_ids": ["a", "b"]}])
    check("mrr: first relevant at rank 2 -> 0.5", abs(r.value - 0.5) < 1e-6, r.value)

    r = ndcg_at_k([["a", "b", "c"]], [{"relevance_grades": {"a": 3, "b": 2, "c": 1}}], k=3)
    check("ndcg_at_3: perfect ranking -> 1.0", abs(r.value - 1.0) < 1e-6, r.value)

    # A perfectly calibrated toy set: 10 predictions all at confidence 0.8,
    # exactly 8 correct -> ECE should be ~0.
    confidences = [0.8] * 10
    correctness = [True] * 8 + [False] * 2
    r = expected_calibration_error(confidences, correctness, n_bins=10)
    check("expected_calibration_error: well-calibrated toy set -> ~0", r.value < 1e-6, r.value)

    r = brier_score([1.0, 0.0], [True, False])
    check("brier_score: perfect predictions -> 0.0", r.value == 0.0, r.value)

    r = latency_percentiles([100, 200, 300, 400, 500])
    check("latency_percentiles: p50 of [100..500] -> 300", r.details["p50"] == 300, r.details)

    r = error_rate([True, True, False, True])
    check("error_rate: 1 of 4 failed -> 0.25", abs(r.value - 0.25) < 1e-6, r.value)

    r = chrf(["hello world"], ["hello world"])
    check("chrf: identical strings -> 1.0", abs(r.value - 1.0) < 1e-6, r.value)

    r = rouge_l(["the cat sat"], ["the cat sat"])
    check("rouge_l: identical strings -> 1.0", abs(r.value - 1.0) < 1e-6, r.value)


def test_results_layer(tmp_run_root: Path):
    print("\n[4/7] results storage round-trip")
    import evaluation.results.store as store_mod
    from evaluation.results.schema import RecordResult

    # Redirect RUNS_ROOT to a temp dir for this test only, so the
    # self-test never writes into the real results/runs/ directory.
    original_root = store_mod.RUNS_ROOT
    store_mod.RUNS_ROOT = tmp_run_root
    try:
        writer = store_mod.RunWriter("synthetic_suite", {"config_hash": "test0000"}, {"note": "synthetic environment"})
        with writer:
            writer.write_record(RecordResult(record_id="r1", input={"x": 1}, output={"y": 2}, latency_ms=12.3))
            writer.write_record(RecordResult(record_id="r2", input={"x": 2}, output={"y": 4}, latency_ms=15.1))
            writer.finalize({"synthetic_metric": {"name": "synthetic_metric", "value": 0.5, "n": 2}})

        loaded = store_mod.load_run("synthetic_suite", writer.run_id)
        check("round-trip: n_records == 2", loaded.n_records == 2, loaded.n_records)
        check("round-trip: manifest status == completed", loaded.manifest.status == "completed")
        check("round-trip: aggregate metric preserved",
              loaded.aggregate_metrics["synthetic_metric"]["value"] == 0.5)
        check("resolve_run_id('latest') resolves to the run just written",
              store_mod.resolve_run_id("synthetic_suite", "latest") == writer.run_id)
    finally:
        store_mod.RUNS_ROOT = original_root


def test_registry():
    print("\n[5/7] evaluator registry")
    from evaluation.runners.registry import list_registered_suites, get_evaluator_class
    from evaluation.runners.base import BaseEvaluator

    suites = list_registered_suites()
    check("all 15 evaluators registered", len(suites) == 15, f"found {len(suites)}: {suites}")
    for suite in suites:
        cls = get_evaluator_class(suite)
        check(f"'{suite}' evaluator subclasses BaseEvaluator", issubclass(cls, BaseEvaluator))


def test_reporting_layer(tmp_dir: Path):
    print("\n[6/7] plotting + report generation (synthetic data)")
    from evaluation.reporting import plots
    from evaluation.reporting.report_builder import build_report
    from evaluation.results.schema import RunManifest, RecordResult, SuiteResult

    fig_path = plots.plot_metric_bar({"synthetic_a": 0.7, "synthetic_b": 0.4}, "synthetic title",
                                       tmp_dir / "fig1.png")
    check("plot_metric_bar writes a PNG", fig_path.exists() and fig_path.stat().st_size > 0)

    fig_path = plots.plot_latency_histogram([100, 120, 90, 200, 150], tmp_dir / "fig2.png")
    check("plot_latency_histogram writes a PNG", fig_path.exists() and fig_path.stat().st_size > 0)

    fig_path = plots.plot_calibration_curve(
        {"bins": [{"bin": 0, "n": 5, "avg_confidence": 0.5, "accuracy": 0.4}]}, tmp_dir / "fig3.png")
    check("plot_calibration_curve writes a PNG", fig_path.exists() and fig_path.stat().st_size > 0)

    fig_path = plots.plot_radar_summary({"cap_a": 0.8, "cap_b": 0.6, "cap_c": 0.9}, tmp_dir / "fig4.png")
    check("plot_radar_summary writes a PNG", fig_path.exists() and fig_path.stat().st_size > 0)

    manifest = RunManifest(
        run_id="synthetic_run_0001", suite="synthetic_suite",
        config={"description": "SYNTHETIC self-test run — not a real evaluation", "config_hash": "test0000"},
        environment={"git_commit": "0000000", "git_dirty": False},
        started_at="2026-01-01T00:00:00+00:00", finished_at="2026-01-01T00:00:05+00:00",
        status="completed", n_records=2, n_errors=0,
    )
    records = [
        RecordResult(record_id="r1", input={"x": 1}, output={"y": 2}, latency_ms=100.0),
        RecordResult(record_id="r2", input={"x": 2}, output={"y": 4}, latency_ms=150.0),
    ]
    aggregate = {"synthetic_metric": {"name": "synthetic_metric", "value": 0.5, "n": 2, "details": {}}}
    suite_result = SuiteResult(manifest=manifest, records=records, aggregate_metrics=aggregate)

    report_path = build_report([suite_result], tmp_dir / "report_out", title="SYNTHETIC self-test report")
    content = report_path.read_text(encoding="utf-8")
    check("build_report writes report.md", report_path.exists())
    check("report contains the suite name", "synthetic_suite" in content)
    check("report contains the aggregate metric", "synthetic_metric" in content)


def test_cli():
    print("\n[7/7] CLI")
    from evaluation.cli import build_parser, cmd_list_suites

    parser = build_parser()
    args = parser.parse_args(["list-suites"])
    rc = cmd_list_suites(args)
    check("cli list-suites exits 0", rc == 0)


def main() -> int:
    print("=" * 70)
    print("evaluation framework infrastructure self-test")
    print("(all data below is synthetic — this is NOT a NyayaSetu evaluation)")
    print("=" * 70)

    tmp_dir = Path(tempfile.mkdtemp(prefix="nyayasetu_eval_selftest_"))
    try:
        test_config_layer()
        test_dataset_layer(tmp_dir)
        test_metrics_layer()
        test_results_layer(tmp_dir / "runs_root")
        test_registry()
        test_reporting_layer(tmp_dir)
        test_cli()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n" + "=" * 70)
    print(f"RESULT: {len(_PASS)} passed, {len(_FAIL)} failed")
    if _FAIL:
        print("Failures:")
        for name, detail in _FAIL:
            print(f"  - {name}: {detail}")
    print("=" * 70)
    return 1 if _FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
