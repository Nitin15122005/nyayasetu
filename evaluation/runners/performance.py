# -*- coding: utf-8 -*-
"""
evaluation/runners/performance.py

Replays a workload spec (endpoint + payload template, from
performance_workload.jsonl) at each configured concurrency level using a
thread pool (the backend calls are I/O-bound HTTP requests, so threads —
not asyncio — are the right tool here and keep this evaluator dependency-
free). Reports latency percentiles/throughput/error-rate PER concurrency
level, not just pooled, since "how does latency degrade under load" is
the actual question — a single blended number would hide that.

peak_memory_mb requires `psutil` and measures THIS PROCESS (the load
generator), not the backend server — measuring the server's memory would
need an in-process hook or an OS-level sampler on the server's PID, out
of scope for a black-box HTTP client. Documented as a known limitation.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from evaluation.datasets.loader import load_dataset
from evaluation.metrics.base import MetricResult
from evaluation.metrics.latency_metrics import error_rate, latency_percentiles, throughput_rps
from evaluation.runners.base import BaseEvaluator
from evaluation.runners.registry import register


@dataclass
class ConcurrencyRunRecord:
    id: str
    concurrency: int


@register("performance")
class PerformanceEvaluator(BaseEvaluator):

    def load_dataset(self) -> list:
        levels = self.config.params.get("concurrency_levels", [1, 4, 8])
        return [ConcurrencyRunRecord(id=f"concurrency_{c}", concurrency=c) for c in levels]

    def run_single(self, record: ConcurrencyRunRecord) -> dict:
        path = self.config.resolved_dataset_path()
        workload = load_dataset(path, "performance_workload") if path and path.exists() else []
        if not workload:
            return {"output": None, "error": "no performance_workload dataset populated — see "
                                                "evaluation/datasets/templates/performance_workload.jsonl.template"}

        duration_s = self.config.params.get("duration_s", 30)
        warmup = self.config.params.get("warmup_requests", 3)

        def _one_call(item):
            resp = self.api.raw("POST", item.endpoint, json=item.payload)
            return resp.ok, resp.latency_ms

        # Warmup (excluded from measured stats — cold-start effects, e.g.
        # a Groq/Colab connection being established, would otherwise
        # distort p99 on the very first requests).
        for item in (workload * ((warmup // len(workload)) + 1))[:warmup]:
            _one_call(item)

        latencies, oks = [], []
        start = time.perf_counter()
        with ThreadPoolExecutor(max_workers=record.concurrency) as pool:
            futures = []
            i = 0
            while time.perf_counter() - start < duration_s:
                item = workload[i % len(workload)]
                futures.append(pool.submit(_one_call, item))
                i += 1
                if len(futures) >= record.concurrency:
                    for f in as_completed(futures[:record.concurrency]):
                        ok, lat = f.result()
                        oks.append(ok)
                        latencies.append(lat)
                    futures = futures[record.concurrency:]
            for f in as_completed(futures):
                ok, lat = f.result()
                oks.append(ok)
                latencies.append(lat)
        elapsed = time.perf_counter() - start

        peak_memory_mb = None
        try:
            import psutil
            peak_memory_mb = psutil.Process().memory_info().rss / (1024 * 1024)
        except ImportError:
            pass

        return {
            "output": {
                "concurrency": record.concurrency,
                "latencies_ms": latencies,
                "oks": oks,
                "elapsed_s": elapsed,
                "peak_memory_mb": peak_memory_mb,
            }
        }

    def compute_metrics(self, records, outcomes) -> dict[str, MetricResult]:
        per_level = {}
        for r, o in zip(records, outcomes):
            if not o.get("output"):
                continue
            out = o["output"]
            lat = latency_percentiles(out["latencies_ms"])
            tput = throughput_rps(len(out["latencies_ms"]), out["elapsed_s"])
            err = error_rate(out["oks"])
            per_level[str(out["concurrency"])] = {
                "latency": lat.details, "throughput_rps": tput.value, "error_rate": err.value,
                "peak_memory_mb": out.get("peak_memory_mb"),
            }

        return {
            "latency_p50": MetricResult("latency_p50", value=None, n=len(per_level), details=per_level),
            "latency_p95": MetricResult("latency_p95", value=None, n=len(per_level), details=per_level),
            "latency_p99": MetricResult("latency_p99", value=None, n=len(per_level), details=per_level),
            "throughput_rps": MetricResult("throughput_rps", value=None, n=len(per_level), details=per_level),
            "error_rate": MetricResult("error_rate", value=None, n=len(per_level), details=per_level),
            "peak_memory_mb": MetricResult("peak_memory_mb", value=None, n=len(per_level),
                                            details={"note": "measures the load generator process, not the "
                                                               "backend server — see module docstring",
                                                      **per_level}),
        }
