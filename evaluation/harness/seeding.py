# -*- coding: utf-8 -*-
"""
evaluation/harness/seeding.py — reproducibility utilities

Two concerns:
  1. Seed whatever local randomness the evaluation framework itself uses
     (e.g. sampling a subset of a large dataset). This does NOT and
     cannot seed the LLMs/notebook — those are external services with
     their own (often nondeterministic) sampling. That asymmetry is
     itself worth recording, which is why capture_environment() exists.
  2. Capture enough environment metadata that a result can be explained
     six months later: what code version produced it, what the backend
     URL was, what package versions were active.
"""

from __future__ import annotations

import os
import platform
import random
import subprocess
import sys
from pathlib import Path
from typing import Optional


def seed_everything(seed: int) -> None:
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass


def _git_commit(repo_root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def _git_dirty(repo_root: Path) -> Optional[bool]:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=5,
        )
        return bool(out.stdout.strip()) if out.returncode == 0 else None
    except Exception:
        return None


def _package_versions(names: list[str]) -> dict:
    versions = {}
    for name in names:
        try:
            mod = __import__(name)
            versions[name] = getattr(mod, "__version__", "unknown")
        except ImportError:
            versions[name] = None
    return versions


def capture_environment(repo_root: Optional[Path] = None) -> dict:
    from evaluation.config.schema import REPO_ROOT as _ROOT
    repo_root = repo_root or _ROOT
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "hostname": platform.node(),
        "git_commit": _git_commit(repo_root),
        "git_dirty": _git_dirty(repo_root),
        "package_versions": _package_versions(
            ["numpy", "pandas", "sklearn", "matplotlib", "requests", "yaml", "jinja2"]
        ),
        "env_overrides": {
            "NYAYASETU_EVAL_BASE_URL": os.getenv("NYAYASETU_EVAL_BASE_URL"),
            "COLAB_BASE_URL": os.getenv("COLAB_BASE_URL"),
        },
    }
