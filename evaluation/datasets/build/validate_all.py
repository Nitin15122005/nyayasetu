# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/validate_all.py

Two layers of validation, run over every evaluation/datasets/raw/*.jsonl
this build produced:

1. Schema validation via the framework's OWN loader
   (evaluation.datasets.loader.load_dataset) — the exact code path
   evaluation.cli run uses, so "the loader accepts this file" is not a
   separate claim from "the evaluator can consume this file". Malformed
   entries (bad JSON, unknown fields, missing id) surface here with the
   file:line the loader itself reports.

2. Cross-dataset integrity checks this build adds on top (duplicates,
   contradictions, missing citations, incomplete metadata) — findings are
   printed AND auto-fixed in place where the fix is unambiguous
   (duplicate id -> keep first occurrence, drop the rest; that's the only
   auto-clean this script performs — anything else is reported, not
   silently altered, because guessing the "right" fix for a contradiction
   would itself be a fabrication).

    python -m evaluation.datasets.build.validate_all
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from evaluation.datasets.build.common import RAW_DIR
from evaluation.datasets.loader import DatasetValidationError, load_dataset
from evaluation.datasets.schema import SCHEMA_REGISTRY

SUITES_BUILT_BY_THIS_PHASE = [
    "ipc_bns_mapping", "retrieval", "document_analysis", "legal_qa",
    "end_to_end", "translation", "multilingual", "robustness", "research",
]


def _read_raw_rows(path: Path) -> list[dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("//"):
                rows.append(json.loads(line))
    return rows


def check_schema_loads(suite: str) -> tuple[bool, str]:
    path = RAW_DIR / f"{suite}.jsonl"
    try:
        records = load_dataset(path, suite)
        return True, f"{len(records)} records loaded cleanly via evaluation.datasets.loader"
    except DatasetValidationError as e:
        return False, str(e)
    except FileNotFoundError as e:
        return False, str(e)


def check_duplicate_ids(suite: str) -> list[str]:
    path = RAW_DIR / f"{suite}.jsonl"
    if not path.exists():
        return []
    rows = _read_raw_rows(path)
    counts = Counter(r["id"] for r in rows)
    dupes = [rid for rid, n in counts.items() if n > 1]
    if dupes:
        deduped = []
        seen = set()
        for r in rows:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            deduped.append(r)
        with open(path, "w", encoding="utf-8") as f:
            for r in deduped:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  [AUTO-CLEANED] {suite}: removed {len(rows) - len(deduped)} duplicate-id row(s): {dupes}")
    return dupes


def check_incomplete_metadata(suite: str) -> list[str]:
    """Flags (not fixes) records missing tags or notes — every record
    built by this phase's build_*.py scripts sets both, so a record
    missing either was hand-edited outside the build pipeline or is a
    genuine gap that needs a human to fill in, not an auto-fix."""
    path = RAW_DIR / f"{suite}.jsonl"
    if not path.exists():
        return []
    issues = []
    for r in _read_raw_rows(path):
        if not r.get("tags"):
            issues.append(f"{r['id']}: missing tags")
        if not r.get("notes"):
            issues.append(f"{r['id']}: missing notes (no source-of-truth pointer)")
    return issues


def check_ipc_bns_contradictions() -> list[str]:
    """Same (act, section) mapping to two different expected_bns values
    across the merged sources would be a real contradiction worth
    surfacing (not auto-fixed — build_ipc_bns_mapping.py already
    resolves tier conflicts deterministically at build time; this check
    exists to catch a FUTURE regression if that resolution logic
    changes)."""
    path = RAW_DIR / "ipc_bns_mapping.jsonl"
    if not path.exists():
        return []
    seen: dict[tuple, str] = {}
    contradictions = []
    for r in _read_raw_rows(path):
        key = (r["act"], r["section"])
        if key in seen and seen[key] != r["expected_bns"]:
            contradictions.append(f"{key}: {seen[key]!r} vs {r['expected_bns']!r}")
        seen[key] = r["expected_bns"]
    return contradictions


def check_retrieval_chunk_ids_exist() -> list[str]:
    """Every relevant_chunk_id must be a real id in data/chromadb — a
    typo'd or stale id here would make precision@k silently score
    against a chunk that doesn't exist. Verified directly against the
    live collection, not assumed from the build script's own output."""
    path = RAW_DIR / "retrieval.jsonl"
    if not path.exists():
        return []
    from evaluation.harness.direct_adapter import get_chromadb_collection
    coll = get_chromadb_collection()
    all_ids = set(coll.get(include=[])["ids"])
    missing = []
    for r in _read_raw_rows(path):
        for cid in r["relevant_chunk_ids"]:
            if cid not in all_ids:
                missing.append(f"{r['id']}: chunk id {cid} not found in live ChromaDB collection")
    return missing


def check_fixtures_exist() -> tuple[list[str], list[str]]:
    """Two populations, checked differently:
      - phase-1 records (file_path is a plain relative name) must resolve
        under raw/fixtures/ — a real failure if missing.
      - corpus-expansion records (file_path == '<external-corpus>/...',
        see corpus/build_from_corpus.py's PII-handling note) are NOT
        expected to resolve locally by design — instead, informationally
        check that provenance.source_file still exists on disk (only
        possible if the external corpus is configured on this machine;
        skipped, not failed, otherwise).
    Returns (hard_failures, informational_notes)."""
    fixtures_dir = RAW_DIR / "fixtures"
    failures, info = [], []
    corpus_dir = None
    try:
        from evaluation.datasets.build.corpus.config import resolve_corpus_dir
        corpus_dir = resolve_corpus_dir()
    except Exception:
        pass

    for suite in ("document_analysis", "legal_qa", "end_to_end"):
        path = RAW_DIR / f"{suite}.jsonl"
        if not path.exists():
            continue
        for r in _read_raw_rows(path):
            fp = r.get("file_path")
            if not fp:
                continue
            if fp.startswith("<external-corpus>/"):
                src = (r.get("provenance") or {}).get("source_file")
                if corpus_dir is None:
                    info.append(f"{suite}/{r['id']}: external-corpus reference, corpus not "
                                f"configured on this run — not checked")
                elif not src or not Path(src).exists():
                    info.append(f"{suite}/{r['id']}: provenance.source_file '{src}' not found "
                                f"(corpus may have changed since extraction)")
                continue
            if not (fixtures_dir / fp).exists():
                failures.append(f"{suite}/{r['id']}: file_path '{fp}' not found under raw/fixtures/")
    return failures, info


def check_duplicate_content() -> list[str]:
    """Detects true content duplicates — same (question, reference_answer)
    pair appearing twice in legal_qa — as distinct from the SAME question
    TEXT being intentionally reused as a template across many different
    source documents (expected, not a duplicate; see
    corpus/build_from_corpus.py's docstring on this). Auto-removes exact
    repeats, keeping the first occurrence."""
    path = RAW_DIR / "legal_qa.jsonl"
    if not path.exists():
        return []
    rows = _read_raw_rows(path)
    seen = set()
    deduped, removed = [], []
    for r in rows:
        key = (r["question"], r["reference_answer"])
        if key in seen:
            removed.append(r["id"])
            continue
        seen.add(key)
        deduped.append(r)
    if removed:
        with open(path, "w", encoding="utf-8") as f:
            for r in deduped:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  [AUTO-CLEANED] legal_qa: removed {len(removed)} true content-duplicate "
              f"(question, reference_answer) row(s): {removed}")
    return removed


def main() -> int:
    print("=" * 70)
    print("Dataset validation")
    print("=" * 70)

    all_ok = True

    print("\n[1/6] Schema validation via evaluation.datasets.loader (same code path as `cli run`)")
    for suite in SUITES_BUILT_BY_THIS_PHASE:
        ok, msg = check_schema_loads(suite)
        print(f"  {'PASS' if ok else 'FAIL'}  {suite}: {msg}")
        all_ok &= ok

    print("\n[2/6] Duplicate id detection + auto-clean")
    for suite in SUITES_BUILT_BY_THIS_PHASE:
        dupes = check_duplicate_ids(suite)
        if not dupes:
            print(f"  PASS  {suite}: no duplicate ids")

    print("\n[3/6] IPC->BNS mapping contradiction check")
    contradictions = check_ipc_bns_contradictions()
    if contradictions:
        print(f"  FAIL  {len(contradictions)} contradiction(s):")
        for c in contradictions:
            print(f"    - {c}")
        all_ok = False
    else:
        print("  PASS  no (act, section) maps to two different expected_bns values")

    print("\n[4/6] retrieval.jsonl relevant_chunk_ids exist in the live ChromaDB collection")
    missing_chunks = check_retrieval_chunk_ids_exist()
    if missing_chunks:
        print(f"  FAIL  {len(missing_chunks)} dangling chunk id reference(s):")
        for m in missing_chunks:
            print(f"    - {m}")
        all_ok = False
    else:
        print("  PASS  every relevant_chunk_id resolves to a real chunk")

    print("\n[5/6] Fixture file existence (document_analysis / legal_qa / end_to_end)")
    missing_fixtures, external_info = check_fixtures_exist()
    if missing_fixtures:
        print(f"  FAIL  {len(missing_fixtures)} missing fixture reference(s):")
        for m in missing_fixtures:
            print(f"    - {m}")
        all_ok = False
    else:
        print("  PASS  every locally-referenced file_path resolves to a real fixture")
    if external_info:
        print(f"  INFO  {len(external_info)} external-corpus reference(s) (by design, not "
              f"copied into git — see corpus/build_from_corpus.py's PII-handling note):")
        for m in external_info[:5]:
            print(f"    - {m}")
        if len(external_info) > 5:
            print(f"    - … and {len(external_info) - 5} more")

    print("\n[6/6] Duplicate content check (legal_qa: same question+answer pair, auto-cleaned)")
    removed = check_duplicate_content()
    if removed:
        print(f"  [AUTO-CLEANED] {len(removed)} true content-duplicate record(s) removed")
    else:
        print("  PASS  no (question, reference_answer) pair repeats")

    print("\n[extra] Incomplete metadata (tags/notes) — informational, not auto-fixed")
    total_meta_issues = 0
    for suite in SUITES_BUILT_BY_THIS_PHASE:
        issues = check_incomplete_metadata(suite)
        total_meta_issues += len(issues)
        if issues:
            print(f"  {suite}: {len(issues)} record(s) missing tags/notes")
    if total_meta_issues == 0:
        print("  every record across all 9 datasets has non-empty tags AND a source-of-truth note")

    print("\n" + "=" * 70)
    print("VALIDATION " + ("PASSED" if all_ok else "FAILED"))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
