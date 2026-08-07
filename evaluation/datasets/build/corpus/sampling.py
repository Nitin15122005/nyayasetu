# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/corpus/sampling.py — turns the full corpus
inventory (evaluation/datasets/corpus_inventory/inventory.jsonl, produced
by inventory.py's full scan) into a small, documented, per-category
sample for DEEP extraction (full text pull, entity/section/citation
extraction, record generation).

Why sample instead of processing all 4020 files: the inventory pass
(cheap — page count + text length + hash) already covers 100% of the
corpus for the statistics NSLB_REPORT.md reports. Deep extraction is a
different cost profile, and more importantly, a benchmark does not need
3747 near-duplicate legal-notice QA pairs to be useful — it needs a
diverse, quality-checked sample. Every cap and its rationale is below,
not hidden in a magic number.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from evaluation.datasets.build.corpus.config import resolve_corpus_dir
from evaluation.datasets.build.corpus.inventory import INVENTORY_JSONL

# category -> max files to deep-extract, with rationale:
#   Affidavit:         only 8/39 files have any extractable text at all
#                       (see CORPUS_INVENTORY.md) — take all 8.
#   Bail_Application:   only 1 file exists — take it.
#   Court_Notice:       39 real judgments, all clean — a generous sample
#                       gives real case-law diversity for research.jsonl.
#   FIR:                193 real Marathi FIRs — capped well below the
#                       full set; this is a benchmark, not a corpus dump.
#   Legal_Notice:       3747 files, heavily skewed to 3 High Courts — cap
#                       low relative to volume, stratified across court
#                       codes (TRHC/MLHC/SKHC) for source diversity.
#   Property_Deed:      0 usable PDFs (the one PDF needs OCR) — take 0.
SAMPLE_CAPS = {
    "Affidavit": 8,
    "Bail_Application": 1,
    "Court_Notice": 20,
    "FIR": 25,
    "Legal_Notice": 40,
    "Property_Deed": 0,
}


def _load_inventory() -> list[dict]:
    if not INVENTORY_JSONL.exists():
        raise FileNotFoundError(
            f"{INVENTORY_JSONL} not found — run "
            f"`python -m evaluation.datasets.build.corpus.inventory` first."
        )
    with open(INVENTORY_JSONL, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _dedupe_exact_hash(rows: list[dict]) -> list[dict]:
    seen_hashes = set()
    kept = []
    for r in sorted(rows, key=lambda r: r["relative_path"]):
        if r["sha256"] in seen_hashes:
            continue
        seen_hashes.add(r["sha256"])
        kept.append(r)
    return kept


def _court_code(relative_path: str) -> str:
    name = Path(relative_path).stem
    return "".join(ch for ch in name[:4] if ch.isalpha()).upper() or "UNK"


def select_sample() -> dict[str, list[dict]]:
    """Returns {category: [inventory row dict, ...]} — only rows that are
    not corrupted, not empty, not OCR-needed (this pipeline has no OCR
    engine wired in), deduplicated by exact file hash, capped per
    SAMPLE_CAPS. Legal_Notice is additionally stratified across its 3
    High Court filename prefixes so the sample isn't dominated by
    whichever court happened to be alphabetically first."""
    rows = _load_inventory()
    valid = [r for r in rows if not r["corrupted"] and not r["empty_document"] and not r["ocr_needed"]]

    by_category: dict[str, list[dict]] = defaultdict(list)
    for r in valid:
        by_category[r["category"]].append(r)

    sample: dict[str, list[dict]] = {}
    for category, cap in SAMPLE_CAPS.items():
        candidates = _dedupe_exact_hash(by_category.get(category, []))
        if cap == 0 or not candidates:
            sample[category] = []
            continue
        if category == "Legal_Notice":
            by_court: dict[str, list[dict]] = defaultdict(list)
            for r in candidates:
                by_court[_court_code(r["relative_path"])].append(r)
            picked, courts = [], sorted(by_court)
            i = 0
            while len(picked) < cap and any(by_court[c] for c in courts):
                c = courts[i % len(courts)]
                if by_court[c]:
                    picked.append(by_court[c].pop(0))
                i += 1
            sample[category] = picked
        else:
            sample[category] = candidates[:cap]
    return sample


if __name__ == "__main__":
    corpus_dir = resolve_corpus_dir()
    sample = select_sample()
    total = sum(len(v) for v in sample.values())
    print(f"Corpus: {corpus_dir}")
    print(f"Deep-extraction sample: {total} files")
    for cat, rows in sample.items():
        print(f"  {cat}: {len(rows)}/{SAMPLE_CAPS[cat]} cap")
