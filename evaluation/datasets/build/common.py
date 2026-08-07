# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/common.py — shared helpers for the dataset
build scripts under this package.

Every build_*.py script in this directory extracts ground truth from a
specific already-existing project source (ChromaDB, lex_validator.py,
data/*.json, the one real sample document) and writes
evaluation/datasets/raw/<suite>.jsonl. No script here calls an LLM to
invent a label — see each script's module docstring for its specific
source of truth and the DATASET_DESIGN.md doc for the full inventory.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "evaluation" / "datasets" / "raw"
DATA_DIR = REPO_ROOT / "data"
BACKEND_DIR = REPO_ROOT / "backend"

for _p in (str(BACKEND_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def append_jsonl(new_records: list, filename: str) -> tuple[Path, int, int]:
    """Read the existing raw/filename (if any), add new_records on top
    WITHOUT touching existing rows, and rewrite sorted by id. Raises if
    any new record's id collides with an existing one — corpus-expansion
    build scripts must use a distinct id namespace (see
    corpus/build_from_corpus.py's `nslb_` prefix) specifically so this
    can never silently overwrite a phase-1 record.
    Returns (path, n_existing, n_added)."""
    out_path = RAW_DIR / filename
    existing: list[dict] = []
    if out_path.exists():
        with open(out_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("//"):
                    existing.append(json.loads(line))

    existing_ids = {r["id"] for r in existing}
    new_rows = [asdict(r) if is_dataclass(r) else r for r in new_records]
    colliding = [r["id"] for r in new_rows if r["id"] in existing_ids]
    if colliding:
        raise ValueError(f"append_jsonl({filename}): id collision with existing records: {colliding}")

    combined = existing + new_rows
    combined.sort(key=lambda r: r["id"])
    with open(out_path, "w", encoding="utf-8") as f:
        for row in combined:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[APPEND] {filename}: {len(existing)} existing + {len(new_rows)} new = {len(combined)} total")
    return out_path, len(existing), len(new_rows)


def write_jsonl(records: list, filename: str) -> Path:
    """Write a list of dataclass records (or dicts) to RAW_DIR/filename,
    one JSON object per line, sorted by id for reproducible diffs."""
    out_path = RAW_DIR / filename
    rows = [asdict(r) if is_dataclass(r) else r for r in records]
    rows.sort(key=lambda r: r["id"])
    with open(out_path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"[BUILD] wrote {len(rows)} records -> {out_path.relative_to(REPO_ROOT)}")
    return out_path


_MOJIBAKE_MAP = {
    # PDF text extraction of the ipc_bns.pdf gazette table decoded curly
    # quotes/dashes as U+FFFD-adjacent control artifacts on the machine
    # that built data/ipc_bns_mappings.json. Observed corrupted bytes are
    # narrow and consistent (always wrapping a section name), so a direct
    # substitution is safe and auditable — NOT a rewrite of the content,
    # only of the punctuation glyphs the encoder mangled.
    "�": '"',
}


def clean_mojibake(text: str) -> str:
    """Strip the specific PDF-extraction encoding artifact seen in
    data/ipc_bns_mappings.json's `name` field (replacement-character runs
    standing in for smart quotes). Returns the text with those glyphs
    normalized to plain double quotes; does not alter any other
    character, so a diff against the original is always inspectable."""
    cleaned = _MOJIBAKE_MAP_PATTERN.sub('"', text)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


_MOJIBAKE_MAP_PATTERN = re.compile("[�\x81\x8d\x8f\x90\x9d]+")


def load_json(relative_path: str) -> dict:
    path = DATA_DIR / relative_path
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
