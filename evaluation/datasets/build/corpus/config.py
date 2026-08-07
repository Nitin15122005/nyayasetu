# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/corpus/config.py — configurable external corpus
location. The corpus itself lives OUTSIDE this repo (it's not tracked by
git — may contain large binaries and documents that shouldn't be
redistributed) and its path must never be hardcoded into committed code.

Resolution order:
  1. NYAYASETU_CORPUS_DIR environment variable
  2. evaluation/config/corpus.local.yaml (gitignored — see .gitignore and
     corpus.local.yaml.example for the format)
  3. neither set -> raise CorpusNotConfigured with instructions for both

Every corpus_*.py tool in this package calls resolve_corpus_dir() rather
than accepting a hardcoded default, so pointing the whole pipeline at a
different corpus is a one-line env-var or config-file change, never a
code change.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from evaluation.datasets.build.common import REPO_ROOT

_LOCAL_CONFIG_PATH = REPO_ROOT / "evaluation" / "config" / "corpus.local.yaml"
_ENV_VAR = "NYAYASETU_CORPUS_DIR"


class CorpusNotConfigured(RuntimeError):
    pass


def resolve_corpus_dir() -> Path:
    env_val = os.getenv(_ENV_VAR)
    if env_val:
        path = Path(env_val)
        source = f"${_ENV_VAR}"
    elif _LOCAL_CONFIG_PATH.exists():
        with open(_LOCAL_CONFIG_PATH, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        val = raw.get("corpus_dir")
        if not val:
            raise CorpusNotConfigured(
                f"{_LOCAL_CONFIG_PATH} exists but has no 'corpus_dir' key."
            )
        path = Path(val)
        source = str(_LOCAL_CONFIG_PATH.relative_to(REPO_ROOT))
    else:
        raise CorpusNotConfigured(
            f"No external corpus configured. Set one of:\n"
            f"  1. environment variable {_ENV_VAR}=/path/to/corpus\n"
            f"  2. evaluation/config/corpus.local.yaml (copy from "
            f"corpus.local.yaml.example, gitignored, machine-specific)\n"
        )

    if not path.exists() or not path.is_dir():
        raise CorpusNotConfigured(
            f"corpus_dir resolved to '{path}' via {source}, but that path "
            f"does not exist or is not a directory."
        )
    return path


def list_category_dirs(corpus_dir: Path | None = None) -> list[Path]:
    """Every immediate subdirectory of corpus_dir is treated as a document
    category — the corpus's own folder structure IS the category ground
    truth (see DATASET_DESIGN.md's provenance note for expanded datasets)."""
    corpus_dir = corpus_dir or resolve_corpus_dir()
    return sorted(p for p in corpus_dir.iterdir() if p.is_dir())
