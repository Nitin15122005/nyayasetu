# -*- coding: utf-8 -*-
"""
evaluation/results/store.py — run persistence

Layout: evaluation/results/runs/<suite>/<run_id>/{manifest.json,
records.jsonl, aggregate.json}. run_id is timestamp-prefixed so
directory listing == chronological order, with a short config hash
suffix so two runs of the same suite at the same second (rare, but
happens in scripted sweeps) don't collide.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from evaluation.config.schema import REPO_ROOT
from evaluation.results.schema import RunManifest, RecordResult, SuiteResult

RUNS_ROOT = REPO_ROOT / "evaluation" / "results" / "runs"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_run_id(config_hash: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{ts}-{config_hash}"


def _run_dir(suite: str, run_id: str) -> Path:
    return RUNS_ROOT / suite / run_id


class RunWriter:
    """
    Streaming writer used by BaseEvaluator.run(). Usage:

        with RunWriter(suite, config, environment) as w:
            for record in dataset:
                w.write_record(record_result)
            w.finalize(aggregate_metrics)

    If the `with` block raises, __exit__ still finalizes the manifest with
    status="failed" and the exception message, so a crashed run is
    visible in the results directory rather than silently absent.
    """

    def __init__(self, suite: str, config: dict, environment: dict, run_id: Optional[str] = None):
        self.suite = suite
        self.run_id = run_id or new_run_id(config.get("config_hash", "nohash"))
        self.dir = _run_dir(suite, self.run_id)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.manifest = RunManifest(
            run_id=self.run_id, suite=suite, config=config, environment=environment,
            started_at=_now_iso(), status="running",
        )
        self._records_path = self.dir / "records.jsonl"
        self._records_file = open(self._records_path, "w", encoding="utf-8")
        self._write_manifest()
        self._n_records = 0
        self._n_errors = 0

    def _write_manifest(self) -> None:
        with open(self.dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(self.manifest.to_dict(), f, indent=2, default=str)

    def write_record(self, record: RecordResult) -> None:
        if not record.timestamp:
            record.timestamp = _now_iso()
        self._records_file.write(json.dumps(record.to_dict(), default=str) + "\n")
        self._records_file.flush()
        self._n_records += 1
        if record.error:
            self._n_errors += 1

    def finalize(self, aggregate_metrics: dict, status: str = "completed", error: Optional[str] = None) -> None:
        self._records_file.close()
        with open(self.dir / "aggregate.json", "w", encoding="utf-8") as f:
            json.dump(aggregate_metrics, f, indent=2, default=str)
        self.manifest.finished_at = _now_iso()
        self.manifest.status = status
        self.manifest.error = error
        self.manifest.n_records = self._n_records
        self.manifest.n_errors = self._n_errors
        self._write_manifest()

    def __enter__(self) -> "RunWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is not None and not self._records_file.closed:
            self.finalize({}, status="failed", error=f"{exc_type.__name__}: {exc_val}")
        return False   # never suppress the exception


def list_runs(suite: str) -> list[str]:
    suite_dir = RUNS_ROOT / suite
    if not suite_dir.exists():
        return []
    return sorted((p.name for p in suite_dir.iterdir() if p.is_dir()))


def resolve_run_id(suite: str, run: str = "latest") -> str:
    if run != "latest":
        return run
    runs = list_runs(suite)
    if not runs:
        raise FileNotFoundError(f"No runs found for suite '{suite}' under {RUNS_ROOT / suite}")
    return runs[-1]   # run_id is timestamp-prefixed, so lexicographic == chronological


def load_run(suite: str, run: str = "latest") -> SuiteResult:
    run_id = resolve_run_id(suite, run)
    run_dir = _run_dir(suite, run_id)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run not found: {run_dir}")

    with open(run_dir / "manifest.json", "r", encoding="utf-8") as f:
        manifest = RunManifest.from_dict(json.load(f))

    records = []
    records_path = run_dir / "records.jsonl"
    if records_path.exists():
        with open(records_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(RecordResult.from_dict(json.loads(line)))

    aggregate = {}
    agg_path = run_dir / "aggregate.json"
    if agg_path.exists():
        with open(agg_path, "r", encoding="utf-8") as f:
            aggregate = json.load(f)

    return SuiteResult(manifest=manifest, records=records, aggregate_metrics=aggregate)
