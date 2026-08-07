# -*- coding: utf-8 -*-
"""
evaluation/datasets/schema.py — one record schema per capability

Every evaluation dataset is a JSONL file (one JSON object per line) under
evaluation/datasets/raw/<suite>.jsonl. Each line must match the dataclass
registered here for that suite. Keeping these as plain dataclasses (not
pydantic) keeps the dataset layer dependency-free — validation is a
field-presence + type check in loader.py, which is all this needs.

Every record carries an `id` (stable across dataset revisions, so results
can be diffed run-over-run) and an optional `tags` list (for slicing
results by category later, e.g. "short-text" vs "long-text").
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Optional


@dataclass
class BaseRecord:
    id: str
    tags: list[str] = field(default_factory=list)
    notes: str = ""
    # Structured traceability back to a source document, for records
    # derived from a corpus-ingestion pipeline (see
    # evaluation/datasets/build/corpus/). Empty dict for phase-1 records
    # built directly from in-repo sources (already fully traceable via
    # `notes`) — this field is additive and optional, never required.
    # Keys used by the corpus pipeline: source_file, page, category,
    # extracted_at (ISO8601), source_citation.
    provenance: dict = field(default_factory=dict)


@dataclass
class TranslationRecord(BaseRecord):
    source_text: str = ""
    source_lang: str = ""          # ISO-ish code matching legal_translator.SUPPORTED_LANGUAGES
    target_lang: str = "en"
    reference_translation: str = ""
    expected_engine: Optional[str] = None   # "nllb-colab" | "gemini-2.5-flash" | "groq-<model>" | None (don't care)


@dataclass
class EmbeddingRecord(BaseRecord):
    text: str = ""
    # Optional: id of another record whose embedding should be close/far,
    # for neighbor-sanity checks (e.g. two paraphrases of the same clause).
    expect_close_to: Optional[str] = None
    expect_far_from: Optional[str] = None


@dataclass
class ChunkingRecord(BaseRecord):
    source_pdf: str = ""            # path relative to data/statutes/ or a test fixture dir
    expected_min_chunks: Optional[int] = None
    expected_max_chunks: Optional[int] = None


@dataclass
class RetrievalRecord(BaseRecord):
    query: str = ""
    relevant_chunk_ids: list[str] = field(default_factory=list)   # ChromaDB ids considered relevant
    relevance_grades: dict[str, int] = field(default_factory=dict)  # id -> graded relevance (for nDCG)


@dataclass
class IPCBNSMappingRecord(BaseRecord):
    act: str = ""                   # "IPC" | "CrPC" | "IEA"
    section: str = ""
    expected_bns: str = ""          # e.g. "BNS 101" or "ABOLISHED"
    expected_name: str = ""
    text_context: str = ""          # surrounding sentence, as sent to /api/compliance


@dataclass
class ComplianceRecord(BaseRecord):
    text: str = ""
    expected_score_min: int = 0
    expected_score_max: int = 100
    expected_grade: Optional[str] = None    # "A".."F"


@dataclass
class DocumentAnalysisRecord(BaseRecord):
    file_path: str = ""             # relative to evaluation/datasets/raw/fixtures/
    expected_document_type: str = ""
    expected_overall_risk: Optional[str] = None   # "Safe" | "Caution" | "High Risk" | "Illegal"
    expected_missing_clauses: list[str] = field(default_factory=list)


@dataclass
class LegalQARecord(BaseRecord):
    file_path: str = ""
    question: str = ""
    reference_answer: str = ""
    must_contain: list[str] = field(default_factory=list)     # substrings/facts the answer must cite
    should_refuse: bool = False      # True if the doc doesn't contain the answer (tests honesty)


@dataclass
class ResearchRecord(BaseRecord):
    query: str = ""
    min_citations: int = 1
    expected_topics: list[str] = field(default_factory=list)


@dataclass
class SummarizationRecord(BaseRecord):
    source_text: str = ""
    reference_summary: str = ""
    max_length: int = 200


@dataclass
class EndToEndRecord(BaseRecord):
    file_path: str = ""
    source_lang: str = ""
    question: str = ""
    expected_stages: list[str] = field(default_factory=lambda: ["translate", "analyze", "compliance", "qa"])


@dataclass
class MultilingualRecord(BaseRecord):
    """
    Cross-language consistency, not single-pair quality (that's
    TranslationRecord's job even though the shape is identical here).
    Every record in multilingual.jsonl holds the SAME source content
    translated into several of legal_translator.SUPPORTED_LANGUAGES, so a
    report can ask "does quality hold across all 12 languages" rather than
    "is this one language pair good". No runner is wired for this suite
    yet — same documented status as classify/retrieve in the README —
    reuses translation's HTTP surface (POST /api/translate) when one is.
    """
    source_text: str = ""
    source_lang: str = ""
    target_lang: str = "en"
    reference_translation: str = ""
    expected_engine: Optional[str] = None
    parallel_group: str = ""        # groups records sharing the same underlying content across languages


@dataclass
class RobustnessRecord(BaseRecord):
    category: str = ""              # matches robustness.yaml's params.categories
    endpoint: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    expected_behavior: str = ""     # e.g. "clean_4xx" | "graceful_fallback" | "clear_error_message"


@dataclass
class PerformanceWorkloadRecord(BaseRecord):
    endpoint: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0             # relative frequency in the replayed workload mix


SCHEMA_REGISTRY: dict[str, type] = {
    "translation": TranslationRecord,
    "multilingual": MultilingualRecord,
    "embeddings": EmbeddingRecord,
    "chunking": ChunkingRecord,
    "retrieval": RetrievalRecord,
    "ipc_bns_mapping": IPCBNSMappingRecord,
    "compliance": ComplianceRecord,
    "document_analysis": DocumentAnalysisRecord,
    "legal_qa": LegalQARecord,
    "research": ResearchRecord,
    "summarization": SummarizationRecord,
    "end_to_end": EndToEndRecord,
    "robustness": RobustnessRecord,
    "performance_workload": PerformanceWorkloadRecord,
    # "confidence" has no dataset — it reads other suites' results.
    # "infra_health" has no dataset — it's a fixed checklist.
}


def get_schema(suite: str) -> type:
    if suite not in SCHEMA_REGISTRY:
        raise KeyError(
            f"No dataset schema registered for suite '{suite}'. "
            f"Registered: {sorted(SCHEMA_REGISTRY)}"
        )
    return SCHEMA_REGISTRY[suite]


def required_field_names(schema: type) -> list[str]:
    return [f.name for f in fields(schema)]
