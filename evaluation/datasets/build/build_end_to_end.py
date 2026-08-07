# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/build_end_to_end.py

Ground truth: reuses build_legal_qa.py's real-fact questions against the
same real fixture (sample_pdf/0125 Publish FIR.pdf, a genuine Marathi-
language FIR — source_lang="mr" is a fact about the document, not a
guess).

expected_stages intentionally omits "translate": reading
evaluation/runners/end_to_end.py shows the runner NEVER appends the
literal string "translate" to stages_completed — translation happens
internally inside the single /api/analyze call and isn't separately
observable, so a record using the schema default
(["translate","analyze","compliance","qa"]) would be structurally capped
at 3/4 stage-completion forever, regardless of real system behaviour.
Using the three stages the runner actually can mark complete
(["analyze","compliance","qa"]) makes stage_completion_rate a real
signal instead of a permanently-deflated one. This is a dataset-authoring
choice, not a change to runner code.
"""

from __future__ import annotations

from evaluation.datasets.build.common import write_jsonl
from evaluation.datasets.schema import EndToEndRecord

FIXTURE = "fir_0125_bhayandar.pdf"
_REACHABLE_STAGES = ["analyze", "compliance", "qa"]


def build() -> list[EndToEndRecord]:
    return [
        EndToEndRecord(
            id="e2e_fir_0125_fir_number",
            tags=["real_document", "fir"],
            notes=(
                "Source: sample_pdf/0125 Publish FIR.pdf (real Marathi-language Maharashtra "
                "Police FIR, source_lang='mr' is a fact about the document). expected_stages "
                "trimmed to ['analyze','compliance','qa'] — see module docstring: "
                "evaluation/runners/end_to_end.py never marks a 'translate' stage complete."
            ),
            file_path=FIXTURE,
            source_lang="mr",
            question="What is the FIR number mentioned in this document?",
            expected_stages=_REACHABLE_STAGES,
        ),
        EndToEndRecord(
            id="e2e_fir_0125_sections",
            tags=["real_document", "fir", "bns"],
            notes=(
                "Source: same fixture. See build_ipc_bns_mapping.py for the BNS section "
                "ground truth this compliance-stage call is exercised against."
            ),
            file_path=FIXTURE,
            source_lang="mr",
            question="Which BNS sections are cited as the acts and sections in this FIR?",
            expected_stages=_REACHABLE_STAGES,
        ),
    ]


if __name__ == "__main__":
    recs = build()
    write_jsonl(recs, "end_to_end.jsonl")
    print(f"[BUILD] end_to_end: {len(recs)} records over 1 real fixture")
