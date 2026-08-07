# -*- coding: utf-8 -*-
"""
evaluation/config/schema.py — Experiment configuration schema

Two layers of config, merged at load time:

  1. GlobalConfig  (evaluation/config/defaults.yaml)
     Environment-level settings shared by every suite: where the backend
     and notebook live, timeouts, output locations, reproducibility seed.

  2. ExperimentConfig  (evaluation/config/experiments/<suite>.yaml)
     Per-suite settings: which capability it evaluates, which dataset,
     which metrics, sample limits, suite-specific parameters.

A suite YAML only needs to declare what's different from the defaults —
load_experiment_config() merges the two, so adding a new suite is a small
YAML file, not new Python.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

import yaml

_THIS_DIR = Path(__file__).resolve().parent
CONFIG_DIR = _THIS_DIR
EXPERIMENTS_DIR = _THIS_DIR / "experiments"
DEFAULTS_PATH = _THIS_DIR / "defaults.yaml"

# Repo root — evaluation/ is a sibling of backend/, frontend/, modules/
REPO_ROOT = _THIS_DIR.parent.parent
EVAL_ROOT = _THIS_DIR.parent


@dataclass
class GlobalConfig:
    """Environment-level defaults, shared by every experiment."""

    backend_base_url: str = "http://localhost:8001"
    notebook_base_url_env: str = "COLAB_BASE_URL"  # read from backend/colab_config.py's env if unset
    request_timeout_s: float = 30.0
    colab_timeout_s: float = 120.0
    random_seed: int = 42
    results_dir: str = "evaluation/results/runs"
    datasets_dir: str = "evaluation/datasets/raw"
    log_level: str = "INFO"
    max_concurrency: int = 4

    @classmethod
    def load(cls, path: Path = DEFAULTS_PATH) -> "GlobalConfig":
        if not path.exists():
            return cls()
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls(**{**asdict(cls()), **raw})


@dataclass
class ExperimentConfig:
    """
    One evaluation suite. `suite` must match a key registered in
    evaluation/runners/registry.py.
    """

    suite: str
    description: str = ""
    dataset_file: Optional[str] = None          # relative to GlobalConfig.datasets_dir
    sample_limit: Optional[int] = None          # cap dataset size for a quick smoke run
    metrics: list[str] = field(default_factory=list)
    repeat: int = 1                              # repetitions per record (for latency/robustness stats)
    params: dict[str, Any] = field(default_factory=dict)  # suite-specific knobs
    global_config: GlobalConfig = field(default_factory=GlobalConfig)

    def resolved_dataset_path(self) -> Optional[Path]:
        if not self.dataset_file:
            return None
        return REPO_ROOT / self.global_config.datasets_dir / self.dataset_file

    def config_hash(self) -> str:
        """Stable hash of this config, stored in the run manifest so a
        result can always be traced back to exactly what produced it."""
        payload = {
            "suite": self.suite,
            "dataset_file": self.dataset_file,
            "sample_limit": self.sample_limit,
            "metrics": sorted(self.metrics),
            "repeat": self.repeat,
            "params": self.params,
        }
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:12]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["config_hash"] = self.config_hash()
        return d


def load_experiment_config(suite: str, overrides: Optional[dict] = None) -> ExperimentConfig:
    """
    Load evaluation/config/experiments/<suite>.yaml, merged over
    defaults.yaml. `overrides` (e.g. from CLI flags like --limit 20) wins
    over the YAML.
    """
    global_cfg = GlobalConfig.load()

    suite_path = EXPERIMENTS_DIR / f"{suite}.yaml"
    if not suite_path.exists():
        raise FileNotFoundError(
            f"No experiment config at {suite_path}. "
            f"Available suites: {list_available_suites()}"
        )
    with open(suite_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    raw.setdefault("suite", suite)
    if overrides:
        raw.update({k: v for k, v in overrides.items() if v is not None})

    known_fields = {"suite", "description", "dataset_file", "sample_limit", "metrics", "repeat", "params"}
    clean = {k: v for k, v in raw.items() if k in known_fields}
    return ExperimentConfig(global_config=global_cfg, **clean)


def list_available_suites() -> list[str]:
    if not EXPERIMENTS_DIR.exists():
        return []
    return sorted(p.stem for p in EXPERIMENTS_DIR.glob("*.yaml"))
