# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/corpus/build_from_corpus.py — NyayaSetu Legal
Benchmark (NSLB) corpus-expansion pass.

Reads the sample selected by sampling.py (drawn from the full inventory
inventory.py already produced), extracts real text from each PDF via
PyMuPDF, runs the pure rule-based extractors in rules.py (document-type
detection, section/citation extraction, entity extraction, extractive
summaries — no LLM anywhere in this file), and APPENDS new,
fully-traceable records to the existing phase-1 datasets under
evaluation/datasets/raw/*.jsonl via common.append_jsonl (which refuses to
overwrite — see that function's docstring).

Every new record's id is prefixed `nslb_` (NyayaSetu Legal Benchmark) so
it can never collide with a phase-1 id, and every new record's
`provenance` dict names the exact source file, page evidence, category,
and an ISO8601 extraction timestamp (see schema.py's BaseRecord.provenance).

PII HANDLING (per explicit decision — see NSLB_REPORT.md): source PDFs
are NEVER copied into the git-tracked raw/fixtures/ directory. Records
that need the original file at evaluation run time (document_analysis,
legal_qa, end_to_end) store the real location only in
`provenance.source_file` (an absolute path under the configured
corpus_dir) and set `file_path` to a `<external-corpus>/...` marker that
the CURRENT runners (evaluation/runners/document_analysis.py etc.) do
NOT resolve — they only look under raw/fixtures/. Running these specific
records therefore needs either (a) a small, separately-reviewed runner
change to also check corpus_dir, or (b) a human manually placing a copy
under raw/fixtures/ after their own privacy review. This is a
deliberate, documented gap, not an oversight — see NSLB_REPORT.md.

    python -m evaluation.datasets.build.corpus.build_from_corpus
"""

from __future__ import annotations

import json
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import fitz

from evaluation.datasets.build.common import RAW_DIR, REPO_ROOT, append_jsonl
from evaluation.datasets.build.corpus import rules
from evaluation.datasets.build.corpus.config import resolve_corpus_dir
from evaluation.datasets.build.corpus.inventory import detect_script
from evaluation.datasets.build.corpus.sampling import select_sample
from evaluation.datasets.schema import (
    DocumentAnalysisRecord, EndToEndRecord, LegalQARecord,
    ResearchRecord, RetrievalRecord, RobustnessRecord,
)

STATS_PATH = REPO_ROOT / "evaluation" / "datasets" / "corpus_inventory" / "build_stats.json"

# folder name -> DOCUMENT_TYPES key this corpus category is EXPECTED to
# correspond to, where the taxonomy actually has one. Affidavit,
# Bail_Application, Court_Notice, Property_Deed have no matching key —
# that absence is itself recorded (tag "no_taxonomy_match"), not papered
# over with a guess.
_FOLDER_TO_TYPE_KEY = {"FIR": "fir", "Legal_Notice": "legal_notice"}


@dataclass
class DocExtraction:
    relative_path: str
    category: str
    text: str
    page_count: int
    detected_lang: str
    detected_type_key: str
    detected_type_label: str
    type_confidence: int
    sections: list[str]
    ipc_refs: list[tuple[str, str]]
    entities: dict
    summary: str
    missing_clauses: list[str]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _extract_doc(row: dict, corpus_dir: Path) -> Optional[DocExtraction]:
    path = corpus_dir / row["relative_path"]
    try:
        doc = fitz.open(str(path))
        text = "".join(p.get_text("text") for p in doc)
        n_pages = len(doc)
        doc.close()
    except Exception:
        return None

    type_key, type_label, type_conf = rules.detect_document_type(text)
    return DocExtraction(
        relative_path=row["relative_path"],
        category=row["category"],
        text=text,
        page_count=n_pages,
        detected_lang=detect_script(text),
        detected_type_key=type_key,
        detected_type_label=type_label,
        type_confidence=type_conf,
        sections=rules.extract_legal_sections(text),
        ipc_refs=rules.extract_ipc_style_references(text),
        entities=rules.extract_entities(text),
        summary=rules.extractive_summary(text),
        missing_clauses=rules.detect_missing_clauses_fallback(text, type_key),
    )


def _provenance(d: DocExtraction, corpus_dir: Path, source_citation: str) -> dict:
    return {
        "source_file": str((corpus_dir / d.relative_path).resolve()),
        "category": d.category,
        "page_count": d.page_count,
        "extracted_at": _now_iso(),
        "source_citation": source_citation,
    }


def _short_id(relative_path: str) -> str:
    import hashlib
    return hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:10]


def _load_ipc_bns_lookup() -> dict[tuple[str, str], str]:
    path = RAW_DIR / "ipc_bns_mapping.jsonl"
    lookup = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                lookup[(r["act"], r["section"])] = r["expected_bns"]
    return lookup


def _load_retrieval_lookup() -> dict[tuple[str, str], dict]:
    """(act_short_lower, section) -> {id, relevant_chunk_ids, relevance_grades}
    from the phase-1 retrieval.jsonl, so corpus-derived citations can be
    matched to an ALREADY chromadb-verified chunk id (see
    build_retrieval.py) rather than inventing a new one."""
    path = RAW_DIR / "retrieval.jsonl"
    lookup = {}
    if not path.exists():
        return lookup
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            parts = r["id"].split("_")  # retr_<act>_<section>
            if len(parts) == 3:
                lookup[(parts[1], parts[2])] = r
    return lookup


def build() -> dict:
    corpus_dir = resolve_corpus_dir()
    sample = select_sample()
    ipc_bns_lookup = _load_ipc_bns_lookup()
    retrieval_lookup = _load_retrieval_lookup()

    stats = {
        "documents_seen": 0, "documents_processed": 0, "documents_skipped_unreadable": 0,
        "records_generated": defaultdict(int), "records_rejected": defaultdict(int),
        "category_counts": defaultdict(int),
        "citations_found_total": 0, "citations_matched_ipc_bns_table": 0,
        "distinct_sections_cited": set(), "distinct_sections_matched": set(),
        "language_counts": defaultdict(int), "documents_with_no_citations": 0,
    }

    new_records: dict[str, list] = defaultdict(list)
    seen_summaries: set[str] = set()
    seen_research_queries: set[str] = set()

    for category, rows in sample.items():
        for row in rows:
            stats["documents_seen"] += 1
            d = _extract_doc(row, corpus_dir)
            if d is None:
                stats["documents_skipped_unreadable"] += 1
                continue
            stats["documents_processed"] += 1
            stats["category_counts"][category] += 1
            stats["language_counts"][d.detected_lang] += 1
            if not d.ipc_refs:
                stats["documents_with_no_citations"] += 1
            for act, section in d.ipc_refs:
                stats["citations_found_total"] += 1
                stats["distinct_sections_cited"].add(f"{act} {section}")
                if ipc_bns_lookup.get((act, section)):
                    stats["citations_matched_ipc_bns_table"] += 1
                    stats["distinct_sections_matched"].add(f"{act} {section}")
            sid = _short_id(d.relative_path)
            base_id = f"nslb_{category.lower()}_{sid}"
            citation = f"{d.category}/{Path(d.relative_path).name} (corpus-external, {d.page_count} pages)"
            prov = _provenance(d, corpus_dir, citation)
            fixture_marker = f"<external-corpus>/{d.relative_path}"

            # ---- document_analysis ----------------------------------------
            expected_label = d.detected_type_label
            no_taxonomy = category not in ("FIR", "Legal_Notice") and d.detected_type_key == "unknown"
            summary_dedupe_key = d.summary[:120]
            if d.summary and summary_dedupe_key in seen_summaries:
                stats["records_rejected"]["document_analysis_duplicate_summary"] += 1
            else:
                if d.summary:
                    seen_summaries.add(summary_dedupe_key)
                new_records["document_analysis"].append(DocumentAnalysisRecord(
                    id=f"{base_id}_doc",
                    tags=["corpus_expansion", category.lower(), "rule_based_classification"] +
                         (["no_taxonomy_match_expected_unknown"] if no_taxonomy else []),
                    notes=(f"Source: {citation}. expected_document_type computed by running "
                           f"rules.detect_document_type (copied verbatim from "
                           f"backend/document_analyzer.py) on the document's OWN real extracted "
                           f"text — type_confidence={d.type_confidence}. "
                           f"Extractive summary (first real paragraph, not LLM-generated): "
                           f"\"{d.summary}\""),
                    provenance=prov,
                    file_path=fixture_marker,
                    expected_document_type=expected_label,
                    expected_overall_risk=None,
                    expected_missing_clauses=d.missing_clauses,
                ))
                stats["records_generated"]["document_analysis"] += 1

            # ---- legal_qa (self-referential, regex-grounded) ---------------
            if d.sections or d.ipc_refs:
                # This question's TEXT is a reused template — self-referential
                # QA templates are meant to repeat across documents (only the
                # must_contain/reference_answer differ per source); duplicate
                # detection for legal_qa therefore keys on record id, not
                # question phrasing (see validate_all.py's duplicate checks).
                citations_found = sorted(set(d.sections) | {f"{a} {s}" for a, s in d.ipc_refs})
                q = "Which legal sections, acts, or citations are mentioned in this document?"
                new_records["legal_qa"].append(LegalQARecord(
                    id=f"{base_id}_qa_sections",
                    tags=["corpus_expansion", category.lower(), "self_referential_extraction"],
                    notes=(f"Source: {citation}. must_contain values are the EXACT strings "
                           f"regex-extracted from this document's own text by "
                           f"rules.extract_legal_sections / extract_ipc_style_references — "
                           f"not inferred or generated."),
                    provenance=prov,
                    file_path=fixture_marker,
                    question=q,
                    reference_answer="; ".join(citations_found[:8]),
                    must_contain=[c.split()[-1] for c in citations_found[:5]],
                    should_refuse=False,
                ))
                stats["records_generated"]["legal_qa"] += 1
            if d.entities["dates"]:
                new_records["legal_qa"].append(LegalQARecord(
                    id=f"{base_id}_qa_dates",
                    tags=["corpus_expansion", category.lower(), "self_referential_extraction"],
                    notes=(f"Source: {citation}. must_contain values are dates matched by a "
                           f"DD/MM/YYYY-style regex directly against this document's own text."),
                    provenance=prov,
                    file_path=fixture_marker,
                    question="What date(s) are mentioned in this document?",
                    reference_answer=", ".join(d.entities["dates"][:5]),
                    must_contain=d.entities["dates"][:3],
                    should_refuse=False,
                ))
                stats["records_generated"]["legal_qa"] += 1

            # ---- end_to_end (reuse the sections question where available) --
            if d.sections or d.ipc_refs:
                new_records["end_to_end"].append(EndToEndRecord(
                    id=f"{base_id}_e2e",
                    tags=["corpus_expansion", category.lower()],
                    notes=(f"Source: {citation}. source_lang from Unicode script-range detection "
                           f"(rules module / inventory.detect_script) on this document's real text. "
                           f"expected_stages trimmed to reachable stages — see "
                           f"build_end_to_end.py's docstring for why 'translate' is excluded."),
                    provenance=prov,
                    file_path=fixture_marker,
                    source_lang=d.detected_lang if d.detected_lang != "unknown" else "en",
                    question="Which legal sections, acts, or citations are mentioned in this document?",
                    expected_stages=["analyze", "compliance", "qa"],
                ))
                stats["records_generated"]["end_to_end"] += 1

            # ---- retrieval (new query phrasing for an ALREADY verified chunk) --
            for act, section in d.ipc_refs:
                bns = ipc_bns_lookup.get((act, section))
                if not bns or bns in ("UNKNOWN", "ABOLISHED"):
                    continue
                bns_num = bns.split(" ", 1)[-1] if " " in bns else bns
                bns_short = bns.split(" ", 1)[0].lower() if " " in bns else None
                match = retrieval_lookup.get((bns_short, bns_num)) if bns_short else None
                if not match:
                    continue
                rid = f"{base_id}_retr_{act.lower()}{section}"
                new_records["retrieval"].append(RetrievalRecord(
                    id=rid,
                    tags=["corpus_expansion", category.lower(), "query_diversity_reuses_verified_chunk"],
                    notes=(f"Source: {citation}, which cites '{act} {section}'. Cross-referenced "
                           f"against ipc_bns_mapping.jsonl ({act} {section} -> {bns}) and matched to "
                           f"the ALREADY chromadb-verified relevant_chunk_ids of retrieval record "
                           f"'{match['id']}' (see build_retrieval.py) — this record adds a new, "
                           f"real-document-grounded query phrasing for the SAME verified chunk, "
                           f"not a new unverified chunk claim."),
                    provenance=prov,
                    query=f"What is the current BNS equivalent of {act} Section {section}, as cited "
                          f"in a real {category.replace('_', ' ').lower()}?",
                    relevant_chunk_ids=match["relevant_chunk_ids"],
                    relevance_grades=match["relevance_grades"],
                ))
                stats["records_generated"]["retrieval"] += 1

            # ---- research ---------------------------------------------------
            if category == "Court_Notice":
                case_name = Path(d.relative_path).stem.replace("_", " ").replace(" on ", " — ")
                q = f"Case law: {case_name}"
            elif d.ipc_refs:
                act, section = d.ipc_refs[0]
                bns = ipc_bns_lookup.get((act, section))
                q = f"Case law relevant to {act} Section {section}" + (f" ({bns})" if bns else "")
            else:
                q = None
            if q and q not in seen_research_queries:
                seen_research_queries.add(q)
                new_records["research"].append(ResearchRecord(
                    id=f"{base_id}_research",
                    tags=["corpus_expansion", category.lower()],
                    notes=(f"Source: {citation}. " +
                           ("Query built directly from this real court judgment's own filename "
                            "(party names + decision date), which IS the case citation."
                            if category == "Court_Notice" else
                            "Query built from a section citation regex-extracted from this "
                            "document's own text, cross-referenced against ipc_bns_mapping.jsonl.")),
                    provenance=prov,
                    query=q,
                    min_citations=1,
                    expected_topics=["Criminal Law"] if category in ("FIR", "Bail_Application") else [],
                ))
                stats["records_generated"]["research"] += 1

    return dict(new_records), stats


def build_robustness_from_empty_files() -> list[RobustnessRecord]:
    """A small, separate step: reads the ACTUAL (near-empty) extracted
    text of real corpus files the inventory flagged as empty/OCR-needed
    (genuinely scanned/unreadable-as-text documents), and uses that real
    text as the payload for an authentic empty/degraded-input robustness
    probe — real corpus artifacts, not a synthetic empty string."""
    import json as _json
    inv_path = REPO_ROOT / "evaluation" / "datasets" / "corpus_inventory" / "inventory.jsonl"
    corpus_dir = resolve_corpus_dir()
    if not inv_path.exists():
        return []
    with open(inv_path, "r", encoding="utf-8") as f:
        rows = [_json.loads(line) for line in f]
    empty_rows = [r for r in rows if r["empty_document"] and not r["corrupted"]][:3]

    records = []
    for row in empty_rows:
        path = corpus_dir / row["relative_path"]
        try:
            doc = fitz.open(str(path))
            text = "".join(p.get_text("text") for p in doc)
            doc.close()
        except Exception:
            continue
        sid = _short_id(row["relative_path"])
        records.append(RobustnessRecord(
            id=f"nslb_robust_realworld_scanned_{sid}",
            tags=["corpus_expansion", "empty_input", "real_scanned_document"],
            notes=(f"Source: {row['category']}/{Path(row['relative_path']).name} — a real corpus "
                   f"PDF the inventory pass measured at {row['extracted_chars']} extractable chars "
                   f"across {row['page_count']} page(s) (scanned image, no text layer). Payload is "
                   f"the ACTUAL text PyMuPDF extracts from it (near-empty/garbage), not a synthetic "
                   f"empty string — a real, not simulated, degraded-input case."),
            provenance={
                "source_file": str(path.resolve()), "category": row["category"],
                "page_count": row["page_count"], "extracted_at": _now_iso(),
                "source_citation": f"{row['category']}/{Path(row['relative_path']).name}",
            },
            category="empty_input",
            endpoint="/api/compliance",
            payload={"text": text},
            expected_behavior="graceful_fallback",
        ))
    return records


def main() -> None:
    print("Building NSLB corpus-expansion records...")
    t0 = time.time()
    new_records, stats = build()
    robustness_extra = build_robustness_from_empty_files()
    if robustness_extra:
        new_records.setdefault("robustness", []).extend(robustness_extra)
        stats["records_generated"]["robustness"] += len(robustness_extra)

    for suite, records in new_records.items():
        if records:
            append_jsonl(records, f"{suite}.jsonl")

    stats["records_generated"] = dict(stats["records_generated"])
    stats["records_rejected"] = dict(stats["records_rejected"])
    stats["category_counts"] = dict(stats["category_counts"])
    stats["language_counts"] = dict(stats["language_counts"])
    stats["distinct_sections_cited"] = sorted(stats["distinct_sections_cited"])
    stats["distinct_sections_matched"] = sorted(stats["distinct_sections_matched"])
    stats["elapsed_s"] = round(time.time() - t0, 1)
    stats["corpus_dir"] = str(resolve_corpus_dir())

    STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATS_PATH.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"\nWrote build stats -> {STATS_PATH.relative_to(REPO_ROOT)}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
