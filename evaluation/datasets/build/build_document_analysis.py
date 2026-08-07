# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/build_document_analysis.py

Ground truth: the ONE real sample legal document in this repo,
sample_pdf/0125 Publish FIR.pdf (staged at
evaluation/datasets/raw/fixtures/fir_0125_bhayandar.pdf) — an authentic
Maharashtra Police FIR (No. 0125, P.S. Bhayandar, dated 30/03/2026),
cross-checked against backend/document_analyzer.py's own
DOCUMENT_TYPES["fir"] taxonomy (label="FIR / Police Complaint",
required_clauses=[] — FIRs have no contract-style clauses, so
expected_missing_clauses is legitimately empty, not an omission).

expected_overall_risk is deliberately left None: document_analyzer's
clause-risk pipeline (Safe/Caution/High Risk/Illegal scoring) is designed
for contracts, not police reports, and there is no authoritative source
in this project defining what "risk" should mean for an FIR — asserting
a value here would be exactly the kind of fabricated ground truth the
brief says not to produce.
"""

from __future__ import annotations

from evaluation.datasets.build.common import write_jsonl
from evaluation.datasets.schema import DocumentAnalysisRecord

FIXTURE = "fir_0125_bhayandar.pdf"


def build() -> list[DocumentAnalysisRecord]:
    return [
        DocumentAnalysisRecord(
            id="docanalysis_fir_0125",
            tags=["real_document", "fir", "maharashtra_police"],
            notes=(
                "Source: sample_pdf/0125 Publish FIR.pdf, a real Maharashtra Police FIR "
                "(No. 0125, P.S. Bhayandar, Mira-Bhayandar Vasai-Virar Police Commissionerate, "
                "dated 30/03/2026), the only real sample legal document present in this repo. "
                "expected_document_type is the exact label backend/document_analyzer.py's "
                "DOCUMENT_TYPES['fir']['label'] returns (verified by reading the source, not "
                "guessed). expected_missing_clauses=[] because DOCUMENT_TYPES['fir']"
                "['required_clauses'] is genuinely empty in the current code — FIRs are not "
                "scored against contract clauses. expected_overall_risk intentionally left "
                "unset: no authoritative definition of 'risk' exists for FIRs in this project."
            ),
            file_path=FIXTURE,
            expected_document_type="FIR / Police Complaint",
            expected_overall_risk=None,
            expected_missing_clauses=[],
        ),
    ]


if __name__ == "__main__":
    recs = build()
    write_jsonl(recs, "document_analysis.jsonl")
    print(f"[BUILD] document_analysis: {len(recs)} record(s) — n=1 because only one real "
          f"fixture document exists in this repo; see DATASET_DESIGN.md for the gap.")
