"""
evaluation/runners/ — one evaluator per capability.

Importing this package registers every evaluator (see registry.py) —
each module below calls @register("<suite>") on its evaluator class at
import time. Adding a new capability means adding one new file here and
one line to this list; nothing else needs to know about it.
"""

from evaluation.runners import (  # noqa: F401  (imported for registration side-effect)
    infra_health,
    translation,
    embeddings,
    chunking,
    retrieval,
    ipc_bns_mapping,
    compliance,
    document_analysis,
    legal_qa,
    research,
    summarization,
    confidence,
    end_to_end,
    performance,
    robustness,
)
