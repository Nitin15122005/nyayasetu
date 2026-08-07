# -*- coding: utf-8 -*-
"""
evaluation/datasets/loader.py — generic JSONL dataset loader

Every dataset is JSONL so it's diffable in git, streamable for large sets,
and trivial to append to. This loader is intentionally the ONLY place that
knows how to read a dataset file — evaluators never open files themselves.
"""

from __future__ import annotations

import json
from dataclasses import fields as dc_fields
from pathlib import Path
from typing import Iterator, TypeVar

from evaluation.datasets.schema import get_schema

T = TypeVar("T")


class DatasetValidationError(ValueError):
    def __init__(self, path: Path, line_no: int, message: str):
        super().__init__(f"{path}:{line_no}: {message}")
        self.path = path
        self.line_no = line_no


def iter_dataset(path: Path, suite: str) -> Iterator[dict]:
    """Yield raw dicts from a JSONL file, one per line, skipping blank lines
    and lines starting with '//' (used in template files as comments)."""
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}\n"
            f"Populate it from the template at "
            f"evaluation/datasets/templates/{suite}.jsonl.template"
        )
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line or line.startswith("//"):
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise DatasetValidationError(path, line_no, f"invalid JSON: {e}") from e


def validate_record(record: dict, schema: type, path: Path, line_no: int) -> dict:
    known = {f.name for f in dc_fields(schema)}
    unknown = set(record.keys()) - known
    if unknown:
        raise DatasetValidationError(
            path, line_no, f"unknown field(s) {sorted(unknown)} for schema {schema.__name__}"
        )
    if "id" not in record or not record["id"]:
        raise DatasetValidationError(path, line_no, "record is missing required non-empty 'id'")
    return record


def load_dataset(path: Path, suite: str, limit: int | None = None) -> list:
    """
    Load and validate a JSONL dataset into typed dataclass instances.
    Raises DatasetValidationError with an exact file:line pointer on the
    first bad record, rather than failing deep inside an evaluator.
    """
    schema = get_schema(suite)
    records = []
    for line_no, raw in enumerate(iter_dataset(path, suite), start=1):
        validate_record(raw, schema, path, line_no)
        records.append(schema(**raw))
        if limit is not None and len(records) >= limit:
            break
    return records


def dataset_size(path: Path) -> int:
    if not path.exists():
        return 0
    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip() and not line.strip().startswith("//"))
