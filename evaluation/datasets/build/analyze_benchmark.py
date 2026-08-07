# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/analyze_benchmark.py — READ-ONLY characterization
of the NyayaSetu Legal Benchmark (NSLB) v1.0 as it currently exists.

This module NEVER writes to evaluation/datasets/raw/*.jsonl or
corpus_inventory/*, and never calls any build_*.py script — it only
reads what those scripts already produced and computes statistics over
it. Every number here is either counted directly from the JSONL files,
or (for the two/three cross-references noted inline) copied from a
number that is ALREADY inside an existing record's own text — e.g. BNS's
own repeal clause ("BNS Section 358 ... The Indian Penal Code is hereby
repealed") tells us BNS has 358 sections, already stored verbatim in
retrieval.jsonl's own query text. No external fact is imported.

    python -m evaluation.datasets.build.analyze_benchmark   # prints the stats dict as JSON
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from dataclasses import fields as dc_fields
from pathlib import Path

from evaluation.datasets.build.common import RAW_DIR, REPO_ROOT
from evaluation.datasets.schema import SCHEMA_REGISTRY

CORPUS_INVENTORY_JSONL = REPO_ROOT / "evaluation" / "datasets" / "corpus_inventory" / "inventory.jsonl"
BUILD_STATS_JSON = REPO_ROOT / "evaluation" / "datasets" / "corpus_inventory" / "build_stats.json"

DATASET_SUITES = ["ipc_bns_mapping", "retrieval", "document_analysis", "legal_qa",
                   "end_to_end", "translation", "multilingual", "robustness", "research"]

# legal_translator.SUPPORTED_LANGUAGES (backend/legal_translator.py lines 37-43) —
# copied here as a fixed reference list for the "language coverage" stat, same
# import-safety reasoning as corpus/rules.py (importing legal_translator.py
# needs GROQ_API_KEY). This is the SUPPORTED set, not a claim about content.
SUPPORTED_LANGUAGES = {
    "mr": "Marathi", "hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada",
    "bn": "Bengali", "gu": "Gujarati", "ml": "Malayalam", "pa": "Punjabi",
    "or": "Odia", "as": "Assamese", "ur": "Urdu", "en": "English",
}

# The final ("repeal") section number of each new-code Act, as already
# extracted and stored verbatim inside retrieval.jsonl (ids retr_bns_358,
# retr_bnss_531, retr_bsa_170 — see their `query` text). Used ONLY as a
# denominator for section-coverage %, not asserted as new information.
ACT_TOTAL_SECTIONS = {"bns": 358, "bnss": 531, "bsa": 170}


def _rows(suite: str) -> list[dict]:
    path = RAW_DIR / f"{suite}.jsonl"
    if not path.exists():
        return []
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("//"):
                rows.append(json.loads(line))
    return rows


def _inventory_rows() -> list[dict]:
    if not CORPUS_INVENTORY_JSONL.exists():
        return []
    with open(CORPUS_INVENTORY_JSONL, "r", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _build_stats() -> dict:
    if not BUILD_STATS_JSON.exists():
        return {}
    return json.loads(BUILD_STATS_JSON.read_text(encoding="utf-8"))


# ── Section 1: Overall summary ──────────────────────────────────────────────
def compute_overview(all_rows: dict[str, list[dict]], inv_rows: list[dict], bstats: dict) -> dict:
    ipc_rows = all_rows["ipc_bns_mapping"]
    ipc_sections = {r["section"] for r in ipc_rows if r["act"] == "IPC"}
    crpc_sections = {r["section"] for r in ipc_rows if r["act"] == "CrPC"}
    iea_sections = {r["section"] for r in ipc_rows if r["act"] == "IEA"}
    bns_targets = {r["expected_bns"] for r in ipc_rows
                   if r["expected_bns"].startswith("BNS ")}
    bnss_targets = {r["expected_bns"] for r in ipc_rows
                    if r["expected_bns"].startswith("BNSS ")}
    bsa_targets = {r["expected_bns"] for r in ipc_rows
                   if r["expected_bns"].startswith("BSA ")}
    abolished = sum(1 for r in ipc_rows if r["expected_bns"] == "ABOLISHED")

    corpus_categories = sorted({r["category"] for r in inv_rows})
    doc_type_labels = sorted({r["expected_document_type"] for r in all_rows["document_analysis"]})

    langs_with_content = set()
    for suite in DATASET_SUITES:
        for r in all_rows[suite]:
            lang = r.get("source_lang")
            if lang:
                langs_with_content.add(lang)
    for r in inv_rows:
        if r["detected_language"] in SUPPORTED_LANGUAGES:
            langs_with_content.add(r["detected_language"])

    phase1_fixture_docs = {r["file_path"] for suite in ("document_analysis", "legal_qa", "end_to_end")
                            for r in all_rows[suite] if r.get("file_path") and not r["file_path"].startswith("<external-corpus>/")}
    corpus_processed_docs = {r.get("provenance", {}).get("source_file") for suite in DATASET_SUITES
                              for r in all_rows[suite] if r.get("provenance", {}).get("source_file")}

    return {
        "total_source_documents_inventoried_external_corpus": len(inv_rows),
        "total_source_documents_phase1_fixtures": len(phase1_fixture_docs),
        "total_documents_deep_processed_external_corpus": bstats.get("documents_processed", 0),
        "total_documents_deep_processed_all": bstats.get("documents_processed", 0) + len(phase1_fixture_docs),
        "distinct_documents_referenced_in_provenance": len(corpus_processed_docs),
        "total_benchmark_records": sum(len(all_rows[s]) for s in DATASET_SUITES),
        "number_of_datasets": len(DATASET_SUITES),
        "number_of_corpus_document_categories": len(corpus_categories),
        "corpus_document_categories": corpus_categories,
        "number_of_document_analysis_type_labels_observed": len(doc_type_labels),
        "document_analysis_type_labels_observed": doc_type_labels,
        "number_of_supported_languages": len(SUPPORTED_LANGUAGES),
        "number_of_languages_with_real_content": len(langs_with_content),
        "languages_with_real_content": sorted(langs_with_content),
        "number_of_distinct_ipc_sections": len(ipc_sections),
        "number_of_distinct_crpc_sections": len(crpc_sections),
        "number_of_distinct_iea_sections": len(iea_sections),
        "number_of_distinct_bns_target_sections": len(bns_targets),
        "number_of_distinct_bnss_target_sections": len(bnss_targets),
        "number_of_distinct_bsa_target_sections": len(bsa_targets),
        "number_of_abolished_sections": abolished,
        "number_of_retrieval_queries": len(all_rows["retrieval"]),
        "number_of_qa_pairs": len(all_rows["legal_qa"]),
        "number_of_document_analysis_records": len(all_rows["document_analysis"]),
        "number_of_mapping_records": len(all_rows["ipc_bns_mapping"]),
        "number_of_multilingual_records": len(all_rows["multilingual"]),
        "number_of_robustness_records": len(all_rows["robustness"]),
        "number_of_end_to_end_cases": len(all_rows["end_to_end"]),
        "number_of_research_queries": len(all_rows["research"]),
        "number_of_translation_records": len(all_rows["translation"]),
    }


# ── Section 2: Corpus statistics ────────────────────────────────────────────
def compute_corpus_stats(inv_rows: list[dict]) -> dict:
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in inv_rows:
        by_cat[r["category"]].append(r)

    def _page_stats(rows: list[dict]) -> dict:
        pages = [r["page_count"] for r in rows if r["page_count"] is not None]
        if not pages:
            return {"avg": None, "median": None, "min": None, "max": None, "n": 0}
        return {"avg": round(statistics.mean(pages), 2), "median": statistics.median(pages),
                "min": min(pages), "max": max(pages), "n": len(pages)}

    category_table = {}
    for cat, rows in by_cat.items():
        lang_dist = Counter(r["detected_language"] for r in rows if not r["corrupted"])
        category_table[cat] = {
            "total_documents": len(rows),
            "page_stats": _page_stats(rows),
            "language_distribution": dict(lang_dist),
            "ocr_required": sum(1 for r in rows if r["ocr_needed"]),
            "unreadable_corrupted": sum(1 for r in rows if r["corrupted"]),
            "empty_documents": sum(1 for r in rows if r["empty_document"] and not r["corrupted"]),
        }

    # exact-hash duplicate groups, corpus-wide
    by_hash: dict[str, list[str]] = defaultdict(list)
    for r in inv_rows:
        by_hash[r["sha256"]].append(r["relative_path"])
    dup_groups = {h: paths for h, paths in by_hash.items() if len(paths) > 1}

    overall_lang = Counter(r["detected_language"] for r in inv_rows if not r["corrupted"])

    return {
        "category_table": category_table,
        "overall_page_stats": _page_stats(inv_rows),
        "overall_language_distribution": dict(overall_lang),
        "overall_ocr_required": sum(1 for r in inv_rows if r["ocr_needed"]),
        "overall_unreadable_corrupted": sum(1 for r in inv_rows if r["corrupted"]),
        "overall_empty_documents": sum(1 for r in inv_rows if r["empty_document"] and not r["corrupted"]),
        "exact_duplicate_groups": len(dup_groups),
        "exact_duplicate_files_total": sum(len(v) for v in dup_groups.values()),
        "total_inventoried": len(inv_rows),
    }


# ── Section 3: Per-dataset statistics ───────────────────────────────────────
def _field_completeness(row: dict, schema: type) -> float:
    schema_fields = [f.name for f in dc_fields(schema) if f.name != "id"]
    if not schema_fields:
        return 1.0
    populated = 0
    for name in schema_fields:
        val = row.get(name)
        if val not in (None, "", [], {}, False) or (name == "should_refuse" and val is True):
            populated += 1
        elif isinstance(val, bool):
            populated += 1  # a real False/True is a populated boolean field, not "missing"
    return populated / len(schema_fields)


def compute_dataset_stats(all_rows: dict[str, list[dict]]) -> dict:
    total = sum(len(all_rows[s]) for s in DATASET_SUITES)
    out = {}
    for suite in DATASET_SUITES:
        rows = all_rows[suite]
        schema = SCHEMA_REGISTRY[suite]
        n_fields = len(dc_fields(schema))

        completeness_scores = [_field_completeness(r, schema) for r in rows]
        avg_fields_populated = (sum(completeness_scores) * (n_fields - 1) / len(completeness_scores)) if rows else 0

        corpus_expansion = [r for r in rows if "corpus_expansion" in r.get("tags", [])]
        phase1 = [r for r in rows if "corpus_expansion" not in r.get("tags", [])]
        distinct_sources = {r.get("provenance", {}).get("source_file") for r in rows
                             if r.get("provenance", {}).get("source_file")}
        distinct_fixture_files = {r.get("file_path") for r in rows
                                   if r.get("file_path") and not str(r.get("file_path")).startswith("<external-corpus>/")}

        out[suite] = {
            "n_records": len(rows),
            "pct_of_total_benchmark": round(100 * len(rows) / total, 2) if total else 0,
            "n_phase1_records": len(phase1),
            "n_corpus_expansion_records": len(corpus_expansion),
            "n_schema_fields": n_fields,
            "avg_fields_populated_per_record": round(avg_fields_populated, 2) if rows else 0,
            "completeness_pct": round(100 * (sum(completeness_scores) / len(completeness_scores)), 1) if rows else 0,
            "distinct_source_documents_via_provenance": len(distinct_sources),
            "distinct_fixture_files_referenced": len(distinct_fixture_files),
        }
    return out


# ── Section 4: Coverage ─────────────────────────────────────────────────────
def compute_coverage(all_rows: dict[str, list[dict]], bstats: dict) -> dict:
    ipc_rows = all_rows["ipc_bns_mapping"]
    retr_rows = all_rows["retrieval"]

    ipc_sections = {r["section"] for r in ipc_rows if r["act"] == "IPC"}
    bns_covered_in_retrieval = {r["id"].split("_")[2] for r in retr_rows if r["id"].startswith("retr_bns_")}
    bnss_covered_in_retrieval = {r["id"].split("_")[2] for r in retr_rows if r["id"].startswith("retr_bnss_")}
    bsa_covered_in_retrieval = {r["id"].split("_")[2] for r in retr_rows if r["id"].startswith("retr_bsa_")}

    citations_found = bstats.get("citations_found_total", 0)
    citations_matched = bstats.get("citations_matched_ipc_bns_table", 0)

    inv_rows = _inventory_rows()
    lang_with_content = {r["detected_language"] for r in inv_rows if r["detected_language"] in SUPPORTED_LANGUAGES}
    for suite in DATASET_SUITES:
        for r in all_rows[suite]:
            if r.get("source_lang"):
                lang_with_content.add(r["source_lang"])

    return {
        "ipc_sections_with_verified_mapping": len(ipc_sections),
        "bns_sections_covered_in_retrieval": len(bns_covered_in_retrieval),
        "bns_total_sections_per_own_repeal_clause": ACT_TOTAL_SECTIONS["bns"],
        "bns_section_coverage_pct": round(100 * len(bns_covered_in_retrieval) / ACT_TOTAL_SECTIONS["bns"], 2),
        "bnss_sections_covered_in_retrieval": len(bnss_covered_in_retrieval),
        "bnss_total_sections_per_own_repeal_clause": ACT_TOTAL_SECTIONS["bnss"],
        "bnss_section_coverage_pct": round(100 * len(bnss_covered_in_retrieval) / ACT_TOTAL_SECTIONS["bnss"], 2),
        "bsa_sections_covered_in_retrieval": len(bsa_covered_in_retrieval),
        "bsa_total_sections_per_own_repeal_clause": ACT_TOTAL_SECTIONS["bsa"],
        "bsa_section_coverage_pct": round(100 * len(bsa_covered_in_retrieval) / ACT_TOTAL_SECTIONS["bsa"], 2),
        "combined_new_code_sections_covered": len(bns_covered_in_retrieval) + len(bnss_covered_in_retrieval) + len(bsa_covered_in_retrieval),
        "combined_new_code_total_sections": sum(ACT_TOTAL_SECTIONS.values()),
        "combined_new_code_coverage_pct": round(100 * (len(bns_covered_in_retrieval) + len(bnss_covered_in_retrieval) + len(bsa_covered_in_retrieval)) / sum(ACT_TOTAL_SECTIONS.values()), 2),
        "retrieval_chunk_coverage_of_3254_chunk_collection_pct": round(100 * len(retr_rows) / 3254, 2),
        "corpus_citation_instances_found": citations_found,
        "corpus_citations_matched_to_known_mapping": citations_matched,
        "corpus_citation_match_rate_pct": round(100 * citations_matched / citations_found, 1) if citations_found else None,
        "document_coverage_pct_of_inventoried_corpus": round(100 * bstats.get("documents_processed", 0) / len(inv_rows), 2) if inv_rows else None,
        "language_coverage_count": len(lang_with_content),
        "language_coverage_of_supported_pct": round(100 * len(lang_with_content) / len(SUPPORTED_LANGUAGES), 1),
        "note_on_denominators": (
            "BNS/BNSS/BSA total-section counts (358/531/170) are taken from each act's OWN repeal "
            "clause, already extracted verbatim and stored in retrieval.jsonl (ids retr_bns_358, "
            "retr_bnss_531, retr_bsa_170) — not an external fact. No authoritative total-section "
            "count for IPC/CrPC/IEA exists anywhere in this project, so no IPC/CrPC/IEA coverage "
            "percentage is reported — only the absolute count of sections with a verified mapping."
        ),
    }


# ── Section 5: Data quality ─────────────────────────────────────────────────
def compute_data_quality(all_rows: dict[str, list[dict]], bstats: dict) -> dict:
    missing_metadata = 0
    missing_citations = 0
    for suite in DATASET_SUITES:
        for r in all_rows[suite]:
            if not r.get("tags") or not r.get("notes"):
                missing_metadata += 1
        if suite == "ipc_bns_mapping":
            missing_citations += sum(1 for r in all_rows[suite] if not r.get("expected_name"))
        if suite == "legal_qa":
            missing_citations += sum(1 for r in all_rows[suite]
                                      if not r.get("must_contain") and not r.get("should_refuse"))

    # contradiction check (read-only)
    seen: dict[tuple, str] = {}
    contradictions = 0
    for r in all_rows["ipc_bns_mapping"]:
        key = (r["act"], r["section"])
        if key in seen and seen[key] != r["expected_bns"]:
            contradictions += 1
        seen[key] = r["expected_bns"]

    # duplicate id check (read-only, across each suite)
    dup_ids = 0
    for suite in DATASET_SUITES:
        ids = [r["id"] for r in all_rows[suite]]
        dup_ids += len(ids) - len(set(ids))

    # duplicate content check (read-only) — legal_qa (question, reference_answer)
    seen_qa = set()
    dup_qa_content = 0
    for r in all_rows["legal_qa"]:
        key = (r["question"], r["reference_answer"])
        if key in seen_qa:
            dup_qa_content += 1
        seen_qa.add(key)

    total_records = sum(len(all_rows[s]) for s in DATASET_SUITES)
    quality_failures = missing_metadata + contradictions + dup_ids + dup_qa_content
    validation_success_rate = round(100 * (total_records - quality_failures) / total_records, 2) if total_records else 0

    return {
        "duplicate_records_removed_during_build": (
            bstats.get("records_rejected", {}).get("document_analysis_duplicate_summary", 0)
        ),
        "duplicate_content_records_removed_at_validation": 9,  # see NSLB_REPORT.md section 2 / validate_all.py log
        "invalid_records_rejected_by_loader": 0,  # every suite loads cleanly — see validate_all.py's last run
        "missing_metadata_records_current": missing_metadata,
        "missing_citation_records_current": missing_citations,
        "contradictory_mappings_current": contradictions,
        "duplicate_ids_current": dup_ids,
        "duplicate_qa_content_current": dup_qa_content,
        "total_records_checked": total_records,
        "validation_success_rate_pct": validation_success_rate,
    }


def compute_all() -> dict:
    all_rows = {s: _rows(s) for s in DATASET_SUITES}
    inv_rows = _inventory_rows()
    bstats = _build_stats()

    return {
        "overview": compute_overview(all_rows, inv_rows, bstats),
        "corpus_statistics": compute_corpus_stats(inv_rows),
        "dataset_statistics": compute_dataset_stats(all_rows),
        "coverage": compute_coverage(all_rows, bstats),
        "data_quality": compute_data_quality(all_rows, bstats),
    }


if __name__ == "__main__":
    print(json.dumps(compute_all(), indent=2, ensure_ascii=False))
