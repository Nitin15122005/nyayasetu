# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/build_retrieval.py

Ground truth: the SAME data/chromadb collection (nyayasetu_legal, 3254
chunks) that backend/lex_validator.py's RAGMapping and
modules/m2_rag/ingest.py build and query in production — read directly
and read-only via evaluation/harness/direct_adapter.get_chromadb_collection.
Every chunk carries its real page number and source PDF (BNS.pdf /
BNSS.pdf / BSA.pdf) in metadata, so every relevant_chunk_id in the output
is traceable to an exact page of an official statute.

Method: scan every chunk's stored text for a section-header line in the
standard Indian-statute drafting style ("103. Punishment for murder.—" or
"103. Punishment for murder.--"), which both BNS/BNSS/BSA follow
throughout. For each matched (act, section_number, title), the query is
built from the title itself (e.g. "What does BNS Section 103 punish?"
for a punishment-style title, generic phrasing otherwise) and
relevant_chunk_ids is the header chunk plus, where present, the very next
chunk on the same page (same act+page, chunk index+1) — sections
frequently overflow the ~512-char chunk boundary, and metadata gives us
the exact adjacency, not a guess.

No LLM is used to write the query OR the relevance label — the title
text IS the statute's own words, and relevance is derived from
chunk/page adjacency in real, stored metadata.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from evaluation.datasets.build.common import write_jsonl
from evaluation.datasets.schema import RetrievalRecord

_HEADER_RE = re.compile(
    r'(?:(?<=\n)|(?<=\A))\s*(\d{1,3}[A-Z]?)\.\s*(?:\((\d+)\)\s*)?([A-Z][A-Za-z0-9 ,\'\-/]{4,90}?)\s*[.—\-]{1,2}\s',
)

# Titles that are grammatically a title-case sentence fragment mid-clause
# rather than a real marginal heading — dropped, not counted as sections.
_BAD_TITLE_STARTS = ("For the", "In this", "Nothing in", "Where the", "Where a", "Provided")


def _act_short(meta: dict) -> str:
    return meta.get("short", "")


def _fetch_all_chunks():
    from evaluation.harness.direct_adapter import get_chromadb_collection
    coll = get_chromadb_collection()
    res = coll.get(include=["documents", "metadatas"])
    return list(zip(res["ids"], res["documents"], res["metadatas"]))


def _query_phrase(short: str, section: str, title: str) -> str:
    lower_title = title.lower()
    if "punish" in lower_title:
        return f"What is the punishment under {short} Section {section} for {lower_title.replace('punishment for', '').strip()}?"
    if lower_title.startswith(("definition", "interpretation")):
        return f"What does {short} Section {section} define?"
    return f"What does {short} Section {section} ({title}) say?"


def build(max_records: int = 220) -> list[RetrievalRecord]:
    chunks = _fetch_all_chunks()
    by_id = {cid: (doc, meta) for cid, doc, meta in chunks}

    # index chunks by (act_short, page) -> ordered list of (chunk_idx, id)
    by_page: dict[tuple, list[tuple[int, str]]] = {}
    for cid, doc, meta in chunks:
        key = (meta.get("short"), meta.get("page"))
        try:
            j = int(meta.get("chunk", "0"))
        except ValueError:
            j = 0
        by_page.setdefault(key, []).append((j, cid))
    for key in by_page:
        by_page[key].sort()

    seen_sections: set[tuple] = set()
    records: list[RetrievalRecord] = []

    for cid, doc, meta in chunks:
        short = _act_short(meta)
        if short not in ("BNS", "BNSS", "BSA"):
            continue
        for m in _HEADER_RE.finditer(doc):
            section, title = m.group(1), m.group(3).strip()
            if len(title.split()) < 2 or title.startswith(_BAD_TITLE_STARTS):
                continue
            key = (short, section)
            if key in seen_sections:
                continue
            seen_sections.add(key)

            page_key = (short, meta.get("page"))
            try:
                this_j = int(meta.get("chunk", "0"))
            except ValueError:
                this_j = 0
            siblings = by_page.get(page_key, [])
            relevance_grades = {cid: 3}
            next_chunk = next((sid for j, sid in siblings if j == this_j + 1), None)
            if next_chunk:
                relevance_grades[next_chunk] = 2

            records.append(RetrievalRecord(
                id=f"retr_{short.lower()}_{section}",
                tags=["chromadb_direct", short.lower(), "auto_extracted_header"],
                notes=(
                    f"Source: data/chromadb collection 'nyayasetu_legal', chunk {cid} "
                    f"(act={meta.get('act')}, source_pdf={meta.get('source')}, page={meta.get('page')}). "
                    f"Query built from the statute's own section title text via a header-line regex, "
                    f"not an LLM. relevant_chunk_ids = the header chunk (+ the immediately following "
                    f"chunk on the same page, if present, per real chunk-index adjacency in metadata)."
                ),
                query=_query_phrase(short, section, title),
                relevant_chunk_ids=list(relevance_grades.keys()),
                relevance_grades=relevance_grades,
            ))
            if len(records) >= max_records:
                return sorted(records, key=lambda r: r.id)

    return sorted(records, key=lambda r: r.id)


if __name__ == "__main__":
    recs = build()
    write_jsonl(recs, "retrieval.jsonl")
    from collections import Counter
    dist = Counter(r.id.split("_")[1] for r in recs)
    print(f"[BUILD] retrieval: {len(recs)} section-grounded queries — by act: {dict(dist)}")
