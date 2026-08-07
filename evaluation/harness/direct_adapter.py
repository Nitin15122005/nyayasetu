# -*- coding: utf-8 -*-
"""
evaluation/harness/direct_adapter.py — direct-import adapter

Two capabilities have no HTTP surface at all:
  - chunking (modules/m2_rag/ingest.py's chunk_pages() runs offline, once,
    to build the index — there's no endpoint that re-chunks on demand)
  - raw retrieval-in-isolation (ChromaDB vector search on its own, without
    lex_validator.RAGMapping's downstream Groq extraction step, so
    retrieval quality can be scored independently of generation quality)

For these two cases only, this module imports repo code directly rather
than going over HTTP — that's a deliberate, narrow exception to the
harness's black-box philosophy (see client.py's docstring), not a
loophole: everywhere a real HTTP surface exists, use client.py instead.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
DATA_DIR = REPO_ROOT / "data"


def _ensure_import_paths() -> None:
    for p in (str(BACKEND_DIR), str(REPO_ROOT)):
        if p not in sys.path:
            sys.path.insert(0, p)


def chunk_pdf(pdf_path: Path) -> list[dict]:
    """Run the real chunking pipeline (modules/m2_rag/ingest.py) against one
    PDF, returning the exact chunk records ingest.py would embed & store —
    unmodified chunking logic, just called directly for measurement."""
    _ensure_import_paths()
    from modules.m2_rag.ingest import extract_text, chunk_pages
    pages = extract_text(str(pdf_path))
    return chunk_pages(pages, pdf_path.name)


def get_chromadb_collection(collection_name: str = "nyayasetu_legal", chroma_dir: Optional[Path] = None):
    """Open the real statute ChromaDB collection read-only. Used by the
    retrieval suite (raw vector search) and infra_health (existence/count
    checks) — never writes."""
    _ensure_import_paths()
    import chromadb
    chroma_dir = chroma_dir or (DATA_DIR / "chromadb")
    client = chromadb.PersistentClient(path=str(chroma_dir))
    return client.get_collection(collection_name)


def query_chromadb_direct(query_embedding: list[float], top_k: int = 3,
                           where: Optional[dict] = None,
                           collection_name: str = "nyayasetu_legal") -> dict:
    """
    Raw ChromaDB similarity search, given an already-computed query
    embedding (get one via evaluation.harness.notebook_client.NotebookClient
    .embed(), matching exactly what backend/lex_validator.py's RAGMapping
    does at query time). Returns ChromaDB's raw result dict — the
    retrieval evaluator computes precision/recall/MRR/nDCG from it.
    """
    collection = get_chromadb_collection(collection_name)
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
        where=where,
    )


def embed_query_via_colab(query: str) -> Optional[list[float]]:
    """Convenience: embed one query text using the SAME backend function
    lex_validator.RAGMapping uses (local_models.embed_texts), so the
    retrieval suite exercises the identical embedding path as production,
    not a hand-rolled equivalent. Returns None if Colab is unreachable —
    callers should treat that as a skipped record, not a failure of the
    retrieval logic being measured."""
    _ensure_import_paths()
    from local_models import embed_texts
    vecs = embed_texts([query])
    return vecs[0] if vecs else None
