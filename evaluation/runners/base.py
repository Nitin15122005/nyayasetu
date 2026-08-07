# -*- coding: utf-8 -*-
"""
evaluation/runners/base.py — the BaseEvaluator contract

Every capability evaluator implements exactly three methods:

  load_dataset()                       -> list of records
  run_single(record)                   -> dict {output, latency_ms, error}
  compute_metrics(records, outcomes)   -> dict[str, MetricResult]

run() (implemented here, not overridden) wires them together: iterate the
dataset, call the system once per record via run_single(), stream every
result to disk via RunWriter as it happens (so a crash mid-run still
leaves honest partial results), then call compute_metrics() ONCE over the
full batch — batch, not per-record, because most of the metrics in
metrics/*.py (precision@k, latency percentiles, ECE, ...) are only
meaningful computed across many records at once.

A record's own dataclass may or may not be JSON-serializable directly
(some hold nested dicts already); to_dict() below normalizes either case.
"""

from __future__ import annotations

import dataclasses
import time
from abc import ABC, abstractmethod
from typing import Any

from evaluation.config.schema import ExperimentConfig
from evaluation.harness.client import NyayaSetuAPIClient
from evaluation.harness.notebook_client import NotebookClient
from evaluation.harness.seeding import capture_environment, seed_everything
from evaluation.metrics.base import MetricResult
from evaluation.results.schema import RecordResult
from evaluation.results.store import RunWriter, load_run


def _to_dict(record: Any) -> dict:
    if dataclasses.is_dataclass(record):
        return dataclasses.asdict(record)
    if isinstance(record, dict):
        return record
    return {"value": record}


class BaseEvaluator(ABC):
    suite: str = ""   # set automatically by @registry.register("...")

    def __init__(self, config: ExperimentConfig):
        self.config = config
        gc = config.global_config
        self.api = NyayaSetuAPIClient(base_url=gc.backend_base_url, timeout_s=gc.request_timeout_s)
        self.notebook = NotebookClient(timeout_s=gc.colab_timeout_s)
        seed_everything(gc.random_seed)

    # ── Subclasses implement these three ────────────────────────────────────
    @abstractmethod
    def load_dataset(self) -> list:
        """Return the list of records this suite evaluates. For
        dataset-free suites (infra_health, confidence) this returns a
        synthetic list of check/source specs instead of loading JSONL."""

    @abstractmethod
    def run_single(self, record) -> dict:
        """Call the system (via self.api / self.notebook / a direct
        adapter) for one record. Must return a dict with at least
        {"output": ..., "latency_ms": float}. Raise on unrecoverable
        errors — run() catches it and records it as a failed record
        rather than aborting the whole suite."""

    @abstractmethod
    def compute_metrics(self, records: list, outcomes: list[dict]) -> dict[str, MetricResult]:
        """Compute this suite's metrics over the FULL batch of
        (record, outcome) pairs, using functions from evaluation.metrics.
        Return {metric_name: MetricResult}."""

    # ── Shared machinery — not overridden ───────────────────────────────────
    def run(self):
        dataset = self.load_dataset()
        if self.config.sample_limit is not None:
            dataset = dataset[: self.config.sample_limit]

        environment = capture_environment()
        writer = RunWriter(self.suite, self.config.to_dict(), environment)
        outcomes: list[dict] = []
        try:
            with writer:
                for record in dataset:
                    outcome = self._run_single_safe(record)
                    outcomes.append(outcome)
                    writer.write_record(RecordResult(
                        record_id=_to_dict(record).get("id", "unknown"),
                        input=_to_dict(record),
                        output=outcome.get("output"),
                        latency_ms=outcome.get("latency_ms", 0.0),
                        error=outcome.get("error"),
                    ))

                metric_results = self.compute_metrics(dataset, outcomes)
                aggregate = {name: mr.to_dict() for name, mr in metric_results.items()}
                writer.finalize(aggregate, status="completed")
        except Exception:
            # __exit__ on RunWriter already finalizes as "failed" with the
            # exception recorded — re-raise so the CLI reports non-zero exit.
            raise

        return load_run(self.suite, writer.run_id)

    def _run_single_safe(self, record) -> dict:
        start = time.perf_counter()
        try:
            outcome = self.run_single(record)
            outcome.setdefault("latency_ms", (time.perf_counter() - start) * 1000)
            outcome.setdefault("error", None)
            return outcome
        except Exception as e:
            return {
                "output": None,
                "latency_ms": (time.perf_counter() - start) * 1000,
                "error": f"{type(e).__name__}: {e}",
            }
