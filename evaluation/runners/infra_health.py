# -*- coding: utf-8 -*-
"""
evaluation/runners/infra_health.py — pre-flight checks

Dataset-free: the "dataset" is the fixed checklist in
config/experiments/infra_health.yaml's params.checks. Run this suite
first, before any other — a red result here explains every other suite's
failures in one place instead of forcing someone to debug fifteen
separate suites that are all failing for the same root cause (e.g. the
backend isn't running).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from evaluation.metrics.base import MetricResult
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


@dataclass
class HealthCheckRecord:
    id: str
    check: str


@register("infra_health")
class InfraHealthEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        checks = self.config.params.get("checks", [])
        return [HealthCheckRecord(id=f"check_{c}", check=c) for c in checks]

    def run_single(self, record: HealthCheckRecord) -> dict:
        method = getattr(self, f"_check_{record.check}", None)
        if method is None:
            return {"output": {"status": "unknown_check"}, "error": f"No check implemented for '{record.check}'"}
        return method()

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        statuses = [o.get("output", {}).get("healthy", False) for o in outcomes]
        availability = sum(1 for s in statuses if s) / len(statuses) if statuses else None
        details = {
            r.check: o.get("output", {})
            for r, o in zip(records, outcomes)
        }
        latencies = [o.get("latency_ms", 0.0) for o in outcomes]
        return {
            "availability": MetricResult(name="availability", value=availability, n=len(statuses), details=details),
            "latency_ms": MetricResult(name="latency_ms", value=(sum(latencies) / len(latencies)) if latencies else None,
                                        n=len(latencies), details={"per_check": dict(zip((r.check for r in records), latencies))}),
        }

    # ── Individual checks ────────────────────────────────────────────────────
    def _check_backend_health(self) -> dict:
        resp = self.api.health()
        return {"output": {"healthy": resp.ok, "status_code": resp.status_code, "body": resp.json_body},
                "latency_ms": resp.latency_ms, "error": resp.error}

    def _check_notebook_health(self) -> dict:
        resp = self.notebook.health()
        return {"output": {"healthy": resp.ok, "status_code": resp.status_code, "body": resp.json_body,
                            "note": "Colab notebooks use ephemeral ngrok URLs — a failure here often just "
                                    "means the notebook isn't currently running, not a code defect."},
                "latency_ms": resp.latency_ms, "error": resp.error}

    def _check_required_env_vars(self) -> dict:
        required = ["GROQ_API_KEY", "GEMINI_API_KEY", "JWT_SECRET_KEY"]
        present = {k: bool(os.getenv(k)) for k in required}
        return {"output": {"healthy": all(present.values()), "present": present}, "latency_ms": 0.0}

    def _check_chromadb_reachable(self) -> dict:
        import time
        start = time.perf_counter()
        try:
            from evaluation.harness.direct_adapter import get_chromadb_collection
            coll = get_chromadb_collection()
            count = coll.count()
            return {"output": {"healthy": count > 0, "chunk_count": count},
                    "latency_ms": (time.perf_counter() - start) * 1000}
        except Exception as e:
            return {"output": {"healthy": False}, "latency_ms": (time.perf_counter() - start) * 1000,
                    "error": f"{type(e).__name__}: {e}"}

    def _check_database_reachable(self) -> dict:
        import sqlite3
        import time
        start = time.perf_counter()
        try:
            from evaluation.config.schema import REPO_ROOT
            db_path = REPO_ROOT / "backend" / "nyayasetu.db"
            conn = sqlite3.connect(str(db_path), timeout=5)
            cur = conn.execute("SELECT COUNT(*) FROM users")
            count = cur.fetchone()[0]
            conn.close()
            return {"output": {"healthy": True, "user_count": count, "db_path": str(db_path)},
                    "latency_ms": (time.perf_counter() - start) * 1000}
        except Exception as e:
            return {"output": {"healthy": False}, "latency_ms": (time.perf_counter() - start) * 1000,
                    "error": f"{type(e).__name__}: {e}"}
