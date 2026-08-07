# -*- coding: utf-8 -*-
"""
evaluation/results/schema.py — result record shapes

Every run produces exactly three files under
evaluation/results/runs/<suite>/<run_id>/:
  manifest.json    — one RunManifest: what produced this run, when, from
                      what config/code version, and whether it finished.
  records.jsonl     — one RecordResult per input record, appended as the
                      run progresses (so a crash mid-run still leaves
                      partial, honest results instead of nothing).
  aggregate.json    — the aggregate MetricResult dicts computed at the end.

This three-way split (not one big JSON) is deliberate: records.jsonl is
streamable and diffable, manifest.json is the reproducibility anchor, and
aggregate.json is the small file reporting/plots actually read most often.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class RunManifest:
    run_id: str
    suite: str
    config: dict
    environment: dict
    started_at: str
    finished_at: Optional[str] = None
    status: str = "running"          # running | completed | failed
    error: Optional[str] = None
    n_records: int = 0
    n_errors: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RunManifest":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class RecordResult:
    record_id: str
    input: dict
    output: dict
    metrics: dict = field(default_factory=dict)
    latency_ms: float = 0.0
    error: Optional[str] = None
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "RecordResult":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SuiteResult:
    manifest: RunManifest
    records: list[RecordResult]
    aggregate_metrics: dict[str, Any]

    @property
    def n_records(self) -> int:
        return len(self.records)

    @property
    def n_errors(self) -> int:
        return sum(1 for r in self.records if r.error)
