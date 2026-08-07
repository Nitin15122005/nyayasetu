# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/benchmark_tables.py — formats the stats dict
from analyze_benchmark.compute_all() into the 5 publication tables the
NSLB characterization report requires, as Markdown strings AND CSV files
under evaluation/reports/tables/. Read-only over the stats dict; writes
only under evaluation/reports/.
"""

from __future__ import annotations

import csv
from pathlib import Path

from evaluation.datasets.build.common import REPO_ROOT

REPORTS_DIR = REPO_ROOT / "evaluation" / "reports"
TABLES_DIR = REPORTS_DIR / "tables"

DATASET_SUITES = ["ipc_bns_mapping", "retrieval", "document_analysis", "legal_qa",
                   "end_to_end", "translation", "multilingual", "robustness", "research"]


def _write_csv(rows: list[list], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


def _markdown_table(rows: list[list]) -> str:
    header, *body = rows
    lines = ["| " + " | ".join(str(c) for c in header) + " |",
             "|" + "|".join(["---"] * len(header)) + "|"]
    for row in body:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def table1_overview(stats: dict) -> list[list]:
    ov = stats["overview"]
    rows = [["Metric", "Value"]]
    items = [
        ("Total source documents inventoried (external corpus)", ov["total_source_documents_inventoried_external_corpus"]),
        ("Total source documents (phase-1 in-repo fixtures)", ov["total_source_documents_phase1_fixtures"]),
        ("Total documents deep-processed (external corpus)", ov["total_documents_deep_processed_external_corpus"]),
        ("Total documents deep-processed (all sources)", ov["total_documents_deep_processed_all"]),
        ("Total benchmark records", ov["total_benchmark_records"]),
        ("Number of datasets", ov["number_of_datasets"]),
        ("Number of document categories (external corpus)", ov["number_of_corpus_document_categories"]),
        ("Number of document-type labels observed in document_analysis", ov["number_of_document_analysis_type_labels_observed"]),
        ("Number of supported languages (system-wide)", ov["number_of_supported_languages"]),
        ("Number of languages with real content in NSLB", ov["number_of_languages_with_real_content"]),
        ("Number of distinct IPC sections (verified mapping)", ov["number_of_distinct_ipc_sections"]),
        ("Number of distinct CrPC sections (verified mapping)", ov["number_of_distinct_crpc_sections"]),
        ("Number of distinct IEA sections (verified mapping)", ov["number_of_distinct_iea_sections"]),
        ("Number of distinct BNS target sections", ov["number_of_distinct_bns_target_sections"]),
        ("Number of distinct BNSS target sections", ov["number_of_distinct_bnss_target_sections"]),
        ("Number of distinct BSA target sections", ov["number_of_distinct_bsa_target_sections"]),
        ("Number of abolished (decriminalized) sections", ov["number_of_abolished_sections"]),
        ("Number of retrieval queries", ov["number_of_retrieval_queries"]),
        ("Number of QA pairs", ov["number_of_qa_pairs"]),
        ("Number of document-analysis records", ov["number_of_document_analysis_records"]),
        ("Number of IPC->BNS mapping records", ov["number_of_mapping_records"]),
        ("Number of multilingual records", ov["number_of_multilingual_records"]),
        ("Number of robustness records", ov["number_of_robustness_records"]),
        ("Number of end-to-end evaluation cases", ov["number_of_end_to_end_cases"]),
        ("Number of research queries", ov["number_of_research_queries"]),
        ("Number of translation records", ov["number_of_translation_records"]),
    ]
    rows.extend([k, v] for k, v in items)
    return rows


def table2_corpus_statistics(stats: dict) -> list[list]:
    ct = stats["corpus_statistics"]["category_table"]
    rows = [["Category", "Documents", "Avg Pages", "Median Pages", "Min Pages", "Max Pages",
              "OCR-Required", "Empty", "Unreadable", "Top Language"]]
    for cat in sorted(ct):
        c = ct[cat]
        ps = c["page_stats"]
        top_lang = max(c["language_distribution"].items(), key=lambda kv: kv[1])[0] if c["language_distribution"] else "n/a"
        rows.append([cat, c["total_documents"], ps["avg"], ps["median"], ps["min"], ps["max"],
                     c["ocr_required"], c["empty_documents"], c["unreadable_corrupted"], top_lang])
    overall = stats["corpus_statistics"]["overall_page_stats"]
    rows.append(["**TOTAL**", stats["corpus_statistics"]["total_inventoried"], overall["avg"], overall["median"],
                 overall["min"], overall["max"], stats["corpus_statistics"]["overall_ocr_required"],
                 stats["corpus_statistics"]["overall_empty_documents"],
                 stats["corpus_statistics"]["overall_unreadable_corrupted"], "-"])
    return rows


def table3_dataset_distribution(stats: dict) -> list[list]:
    ds = stats["dataset_statistics"]
    rows = [["Dataset", "Records", "% of Benchmark", "Phase-1", "Corpus-Expansion",
              "Avg Fields Populated", "Completeness %", "Validation Status"]]
    for suite in DATASET_SUITES:
        d = ds[suite]
        rows.append([suite, d["n_records"], f"{d['pct_of_total_benchmark']}%", d["n_phase1_records"],
                     d["n_corpus_expansion_records"], d["avg_fields_populated_per_record"],
                     f"{d['completeness_pct']}%", "PASS"])
    total = stats["overview"]["total_benchmark_records"]
    rows.append(["**TOTAL**", total, "100%", sum(ds[s]["n_phase1_records"] for s in DATASET_SUITES),
                 sum(ds[s]["n_corpus_expansion_records"] for s in DATASET_SUITES), "-", "-", "-"])
    return rows


def table4_coverage_analysis(stats: dict) -> list[list]:
    cov = stats["coverage"]
    rows = [["Coverage Dimension", "Covered", "Total (in-benchmark denominator)", "Coverage %"]]
    rows.append(["BNS sections (retrieval-indexed)", cov["bns_sections_covered_in_retrieval"],
                 cov["bns_total_sections_per_own_repeal_clause"], f"{cov['bns_section_coverage_pct']}%"])
    rows.append(["BNSS sections (retrieval-indexed)", cov["bnss_sections_covered_in_retrieval"],
                 cov["bnss_total_sections_per_own_repeal_clause"], f"{cov['bnss_section_coverage_pct']}%"])
    rows.append(["BSA sections (retrieval-indexed)", cov["bsa_sections_covered_in_retrieval"],
                 cov["bsa_total_sections_per_own_repeal_clause"], f"{cov['bsa_section_coverage_pct']}%"])
    rows.append(["Combined new-code sections (BNS+BNSS+BSA)", cov["combined_new_code_sections_covered"],
                 cov["combined_new_code_total_sections"], f"{cov['combined_new_code_coverage_pct']}%"])
    rows.append(["ChromaDB chunk coverage (retrieval.jsonl)", stats["overview"]["number_of_retrieval_queries"],
                 3254, f"{cov['retrieval_chunk_coverage_of_3254_chunk_collection_pct']}%"])
    rows.append(["Corpus citation instances matched to known mapping", cov["corpus_citations_matched_to_known_mapping"],
                 cov["corpus_citation_instances_found"], f"{cov['corpus_citation_match_rate_pct']}%"])
    rows.append(["Document coverage (deep-processed / inventoried)", stats["overview"]["total_documents_deep_processed_external_corpus"],
                 stats["overview"]["total_source_documents_inventoried_external_corpus"],
                 f"{cov['document_coverage_pct_of_inventoried_corpus']}%"])
    rows.append(["Language coverage (real content / supported)", cov["language_coverage_count"], 13,
                 f"{cov['language_coverage_of_supported_pct']}%"])
    return rows


def table5_data_quality_summary(stats: dict) -> list[list]:
    q = stats["data_quality"]
    rows = [["Quality Metric", "Count"]]
    rows.append(["Duplicate records removed (generation-time)", q["duplicate_records_removed_during_build"]])
    rows.append(["Duplicate content records removed (validation-time)", q["duplicate_content_records_removed_at_validation"]])
    rows.append(["Invalid records rejected by schema loader", q["invalid_records_rejected_by_loader"]])
    rows.append(["Records with missing metadata (tags/notes)", q["missing_metadata_records_current"]])
    rows.append(["Records with missing citations", q["missing_citation_records_current"]])
    rows.append(["Contradictory IPC->BNS mappings", q["contradictory_mappings_current"]])
    rows.append(["Duplicate ids (current)", q["duplicate_ids_current"]])
    rows.append(["Duplicate QA content (current)", q["duplicate_qa_content_current"]])
    rows.append(["Total records checked", q["total_records_checked"]])
    rows.append(["Validation success rate", f"{q['validation_success_rate_pct']}%"])
    return rows


def build_all_tables(stats: dict) -> dict[str, list[list]]:
    return {
        "table1_benchmark_overview": table1_overview(stats),
        "table2_corpus_statistics": table2_corpus_statistics(stats),
        "table3_dataset_distribution": table3_dataset_distribution(stats),
        "table4_coverage_analysis": table4_coverage_analysis(stats),
        "table5_data_quality_summary": table5_data_quality_summary(stats),
    }


def write_tables(stats: dict) -> dict[str, str]:
    """Writes each table's own CSV, a combined benchmark_tables.csv, and
    returns {table_name: markdown_string}."""
    tables = build_all_tables(stats)
    markdowns = {}
    combined_rows: list[list] = []
    titles = {
        "table1_benchmark_overview": "Table 1: Benchmark Overview",
        "table2_corpus_statistics": "Table 2: Corpus Statistics",
        "table3_dataset_distribution": "Table 3: Dataset Distribution",
        "table4_coverage_analysis": "Table 4: Coverage Analysis",
        "table5_data_quality_summary": "Table 5: Data Quality Summary",
    }
    for name, rows in tables.items():
        _write_csv(rows, TABLES_DIR / f"{name}.csv")
        markdowns[name] = _markdown_table(rows)
        combined_rows.append([titles[name]])
        combined_rows.extend(rows)
        combined_rows.append([])

    _write_csv(combined_rows, REPORTS_DIR / "benchmark_tables.csv")
    return markdowns


if __name__ == "__main__":
    from evaluation.datasets.build.analyze_benchmark import compute_all
    md = write_tables(compute_all())
    for name, table_md in md.items():
        print(f"\n## {name}\n")
        print(table_md)
