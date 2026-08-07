# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/corpus/inventory.py — full, read-only scan of an
external legal-document corpus (see corpus/config.py for how the corpus
location is configured). Produces per-file metadata and a per-category
summary BEFORE any evaluation record is generated — this is deliberately
a separate pass from extraction (build_from_corpus.py), so a corpus can
be inspected without committing to processing all of it.

Per-file checks, each computed directly (no LLM):
  - category:        the top-level folder name under corpus_dir — the
                      corpus's own organization IS the category ground
                      truth (see DATASET_DESIGN.md's provenance notes).
  - page_count:       via PyMuPDF (fitz), None if the file can't be opened.
  - corrupted:        True if fitz.open() / page iteration raises.
  - extracted_chars:  total chars from fitz's text layer across all pages.
  - empty_document:   extracted_chars below EMPTY_CHAR_THRESHOLD.
  - ocr_needed:       page_count > 0 and avg chars/page below
                      OCR_CHARS_PER_PAGE_THRESHOLD — a text layer this
                      thin on a real legal document almost always means
                      the PDF is a scanned image with no embedded text,
                      not that the document is genuinely short.
  - detected_language: Unicode script-range voting over the extracted
                      text — the SAME approach as
                      backend/legal_translator.py's detect_script()
                      (SCRIPT_RANGES copied verbatim from that file, see
                      _SCRIPT_RANGES below, rather than importing it,
                      because importing legal_translator.py eagerly
                      constructs a Groq client via ai_clients.py and
                      requires GROQ_API_KEY to even be set).
  - sha256:           exact-duplicate detection key (file bytes).

    python -m evaluation.datasets.build.corpus.inventory
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF

from evaluation.datasets.build.common import REPO_ROOT
from evaluation.datasets.build.corpus.config import resolve_corpus_dir, list_category_dirs

INVENTORY_DIR = REPO_ROOT / "evaluation" / "datasets" / "corpus_inventory"
INVENTORY_JSONL = INVENTORY_DIR / "inventory.jsonl"
INVENTORY_REPORT = REPO_ROOT / "evaluation" / "datasets" / "CORPUS_INVENTORY.md"

EMPTY_CHAR_THRESHOLD = 20
OCR_CHARS_PER_PAGE_THRESHOLD = 40

# Verbatim copy of backend/legal_translator.py's SCRIPT_RANGES (lines
# 52-65) — see module docstring for why this is a copy, not an import.
_SCRIPT_RANGES = {
    "mr": [(0x0900, 0x097F)], "hi": [(0x0900, 0x097F)], "ta": [(0x0B80, 0x0BFF)],
    "te": [(0x0C00, 0x0C7F)], "kn": [(0x0C80, 0x0CFF)], "bn": [(0x0980, 0x09FF)],
    "gu": [(0x0A80, 0x0AFF)], "ml": [(0x0D00, 0x0D7F)], "pa": [(0x0A00, 0x0A7F)],
    "or": [(0x0B00, 0x0B7F)], "as": [(0x0980, 0x09FF)],
    "ur": [(0x0600, 0x06FF), (0xFB50, 0xFDFF)],
}


def detect_script(text: str) -> str:
    """Identical logic to backend/legal_translator.py::detect_script."""
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for lang, ranges in _SCRIPT_RANGES.items():
            for lo, hi in ranges:
                if lo <= cp <= hi:
                    counts[lang] = counts.get(lang, 0) + 1
                    break
    return max(counts, key=counts.get) if counts else "en"


@dataclass
class FileRecord:
    relative_path: str
    category: str
    size_bytes: int
    sha256: str
    page_count: Optional[int]
    extracted_chars: int
    corrupted: bool
    error: Optional[str]
    empty_document: bool
    ocr_needed: bool
    detected_language: str


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def scan_file(path: Path, category: str, corpus_dir: Path) -> FileRecord:
    rel = str(path.relative_to(corpus_dir))
    size = path.stat().st_size
    sha = _hash_file(path)
    try:
        doc = fitz.open(str(path))
        n_pages = len(doc)
        text_parts = []
        for page in doc:
            text_parts.append(page.get_text("text"))
        doc.close()
        text = "".join(text_parts)
        n_chars = len(text)
        avg_chars_per_page = (n_chars / n_pages) if n_pages else 0
        return FileRecord(
            relative_path=rel, category=category, size_bytes=size, sha256=sha,
            page_count=n_pages, extracted_chars=n_chars, corrupted=False, error=None,
            empty_document=n_chars < EMPTY_CHAR_THRESHOLD,
            ocr_needed=(n_pages > 0 and avg_chars_per_page < OCR_CHARS_PER_PAGE_THRESHOLD),
            detected_language=detect_script(text) if n_chars >= EMPTY_CHAR_THRESHOLD else "unknown",
        )
    except Exception as e:
        return FileRecord(
            relative_path=rel, category=category, size_bytes=size, sha256=sha,
            page_count=None, extracted_chars=0, corrupted=True, error=f"{type(e).__name__}: {e}",
            empty_document=True, ocr_needed=False, detected_language="unknown",
        )


def scan_corpus() -> tuple[list[FileRecord], dict[str, int]]:
    corpus_dir = resolve_corpus_dir()
    category_dirs = list_category_dirs(corpus_dir)

    records: list[FileRecord] = []
    non_pdf_counts: dict[str, int] = defaultdict(int)

    for cat_dir in category_dirs:
        category = cat_dir.name
        for path in cat_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() != ".pdf":
                non_pdf_counts[category] += 1
                continue
            records.append(scan_file(path, category, corpus_dir))

    return records, dict(non_pdf_counts)


def _duplicate_groups(records: list[FileRecord]) -> dict[str, list[str]]:
    by_hash: dict[str, list[str]] = defaultdict(list)
    for r in records:
        by_hash[r.sha256].append(r.relative_path)
    return {h: paths for h, paths in by_hash.items() if len(paths) > 1}


_PAREN_SUFFIX_RE = re.compile(r"\s*\(\d+\)\s*$")


def _filename_pattern_duplicate_groups(records: list[FileRecord]) -> dict[str, list[str]]:
    """Weaker, secondary signal: files whose name is identical after
    stripping a trailing ' (n)' — a common download-duplicate pattern
    observed in this corpus's FIR/ and Court_Notice/ folders. Reported
    separately from exact-hash duplicates, never merged with them."""
    by_stem: dict[str, list[str]] = defaultdict(list)
    for r in records:
        name = Path(r.relative_path).stem
        stripped = _PAREN_SUFFIX_RE.sub("", name)
        key = f"{r.category}::{stripped.lower()}"
        by_stem[key].append(r.relative_path)
    return {k: v for k, v in by_stem.items() if len(v) > 1}


def write_inventory(records: list[FileRecord]) -> None:
    INVENTORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(INVENTORY_JSONL, "w", encoding="utf-8") as f:
        for r in sorted(records, key=lambda r: r.relative_path):
            f.write(json.dumps(asdict(r), ensure_ascii=False) + "\n")


def build_report(records: list[FileRecord], non_pdf_counts: dict[str, int],
                  elapsed_s: float) -> str:
    exact_dupes = _duplicate_groups(records)
    name_dupes = _filename_pattern_duplicate_groups(records)
    corpus_dir = resolve_corpus_dir()

    by_category: dict[str, list[FileRecord]] = defaultdict(list)
    for r in records:
        by_category[r.category].append(r)

    lines = []
    lines.append("# External Legal Corpus — Inventory Report")
    lines.append("")
    lines.append(f"Corpus location (configured, not hardcoded): `{corpus_dir}`")
    lines.append(f"Scanned {len(records)} PDF files across {len(by_category)} category folders "
                  f"in {elapsed_s:.1f}s.")
    lines.append("")
    lines.append(
        "This report is generated BEFORE any extraction — see "
        "`evaluation/datasets/build/corpus/build_from_corpus.py` for the extraction phase, "
        "which reads this inventory to decide what to sample and to skip corrupted/empty/"
        "duplicate files."
    )
    lines.append("")

    lines.append("## Per-category summary")
    lines.append("")
    lines.append("| Category | PDFs | Non-PDF files (skipped) | Avg pages | Corrupted | "
                  "Empty | OCR-needed | Exact-dup files | Language distribution |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for cat in sorted(by_category):
        rs = by_category[cat]
        pages = [r.page_count for r in rs if r.page_count is not None]
        avg_pages = sum(pages) / len(pages) if pages else 0
        corrupted = sum(1 for r in rs if r.corrupted)
        empty = sum(1 for r in rs if r.empty_document)
        ocr = sum(1 for r in rs if r.ocr_needed)
        dup_files_in_cat = sum(len(v) for k, v in exact_dupes.items()
                                if any(p.startswith(cat + "\\") or p.startswith(cat + "/") for p in v))
        lang_dist = Counter(r.detected_language for r in rs if not r.corrupted)
        lang_str = ", ".join(f"{k}:{v}" for k, v in lang_dist.most_common())
        non_pdf = non_pdf_counts.get(cat, 0)
        lines.append(f"| {cat} | {len(rs)} | {non_pdf} | {avg_pages:.1f} | {corrupted} | "
                      f"{empty} | {ocr} | {dup_files_in_cat} | {lang_str} |")
    lines.append("")

    total_lang_dist = Counter(r.detected_language for r in records if not r.corrupted)
    lines.append("## Corpus-wide language distribution")
    lines.append("")
    for lang, n in total_lang_dist.most_common():
        lines.append(f"- {lang}: {n} ({100*n/len(records):.1f}%)")
    lines.append("")

    lines.append("## Duplicate detection")
    lines.append("")
    lines.append(f"- **Exact duplicates (sha256 file-hash match)**: {len(exact_dupes)} group(s), "
                  f"{sum(len(v) for v in exact_dupes.values())} files total.")
    for h, paths in sorted(exact_dupes.items())[:20]:
        lines.append(f"  - `{h[:12]}…`: {paths}")
    if len(exact_dupes) > 20:
        lines.append(f"  - … and {len(exact_dupes) - 20} more group(s) (see inventory.jsonl for the full list)")
    lines.append(f"- **Filename-pattern duplicates** (same name modulo a trailing ` (n)` — a "
                  f"secondary, weaker signal, not merged with exact duplicates): "
                  f"{len(name_dupes)} group(s).")
    lines.append("")

    corrupted_files = [r for r in records if r.corrupted]
    lines.append("## Corrupted / unreadable PDFs")
    lines.append("")
    lines.append(f"{len(corrupted_files)} file(s) could not be opened or read by PyMuPDF:")
    for r in corrupted_files[:30]:
        lines.append(f"  - `{r.relative_path}`: {r.error}")
    if len(corrupted_files) > 30:
        lines.append(f"  - … and {len(corrupted_files) - 30} more (see inventory.jsonl)")
    lines.append("")

    empty_files = [r for r in records if r.empty_document and not r.corrupted]
    lines.append("## Empty documents (no meaningfully extractable text)")
    lines.append("")
    lines.append(f"{len(empty_files)} file(s) opened successfully but yielded under "
                  f"{EMPTY_CHAR_THRESHOLD} characters of extractable text.")
    lines.append("")

    ocr_files = [r for r in records if r.ocr_needed]
    lines.append("## OCR requirements")
    lines.append("")
    lines.append(f"{len(ocr_files)}/{len(records)} ({100*len(ocr_files)/len(records) if records else 0:.1f}%) "
                  f"files have under {OCR_CHARS_PER_PAGE_THRESHOLD} extractable chars/page on average — "
                  f"almost certainly scanned images with no embedded text layer, needing OCR before "
                  f"any text-based extraction (entity/section/citation extraction, language ID, "
                  f"summarization) can run on them. This build's extraction phase "
                  f"(`build_from_corpus.py`) SKIPS these — no OCR engine is wired into this pipeline "
                  f"(pytesseract exists in `backend/lex_validator.py` for image uploads, but is not "
                  f"invoked here) — see the gap list in NSLB_REPORT.md.")
    lines.append("")

    lines.append("## Non-PDF files present (out of scope for this pipeline)")
    lines.append("")
    for cat, n in sorted(non_pdf_counts.items()):
        if n:
            lines.append(f"- {cat}: {n} non-PDF file(s) (e.g. .doc/.docx) — not processed; "
                          f"this pipeline only reads PDFs via PyMuPDF.")
    if not any(non_pdf_counts.values()):
        lines.append("- none")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    print("Scanning external corpus (this may take a minute for a large corpus)...")
    t0 = time.time()
    records, non_pdf_counts = scan_corpus()
    elapsed = time.time() - t0
    print(f"Scanned {len(records)} PDFs in {elapsed:.1f}s")

    write_inventory(records)
    print(f"Wrote per-file inventory -> {INVENTORY_JSONL.relative_to(REPO_ROOT)}")

    report = build_report(records, non_pdf_counts, elapsed)
    INVENTORY_REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote inventory report -> {INVENTORY_REPORT.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
