# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/run_all.py — runs every build_*.py script in
this package in a fixed order, then validate_all.py, then report.py.

    python -m evaluation.datasets.build.run_all
"""

from __future__ import annotations

from evaluation.datasets.build import (
    build_document_analysis,
    build_end_to_end,
    build_ipc_bns_mapping,
    build_legal_qa,
    build_research,
    build_retrieval,
    build_robustness,
    build_translation,
)
from evaluation.datasets.build.common import write_jsonl


def main() -> None:
    print("=" * 70)
    print("NyayaSetu evaluation — ground truth dataset build")
    print("=" * 70)

    write_jsonl(build_ipc_bns_mapping.build(), "ipc_bns_mapping.jsonl")
    write_jsonl(build_retrieval.build(), "retrieval.jsonl")
    write_jsonl(build_document_analysis.build(), "document_analysis.jsonl")
    write_jsonl(build_legal_qa.build(), "legal_qa.jsonl")
    write_jsonl(build_end_to_end.build(), "end_to_end.jsonl")
    write_jsonl(build_translation.build_translation(), "translation.jsonl")
    write_jsonl(build_translation.build_multilingual(), "multilingual.jsonl")
    write_jsonl(build_robustness.build(), "robustness.jsonl")
    write_jsonl(build_research.build(), "research.jsonl")

    print("\n[BUILD] All datasets written. Run validation next:")
    print("  python -m evaluation.datasets.build.validate_all")
    print("  python -m evaluation.datasets.build.report")


if __name__ == "__main__":
    main()
