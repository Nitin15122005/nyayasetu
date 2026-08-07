# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/build_legal_qa.py

Ground truth: facts read directly off the same real FIR PDF used by
build_document_analysis.py (sample_pdf/0125 Publish FIR.pdf) — every
reference_answer/must_contain value below was copied from the document's
own printed fields (FIR number, date, section numbers, names, phone
number), not inferred or generated.

must_contain values favour digits and BNS section numbers over Marathi
proper nouns: the live pipeline internally translates the document
(document_analyzer.py Phase 1) before DocumentRAG answers questions, so
a fact needs to survive machine translation to be a fair substring
check — numbers and section citations do, transliterated names don't
reliably.

One should_refuse=True record tests honesty: it asks about a field the
form has printed but left BLANK in this specific FIR (item 10, "Total
value of property (In Rs/-)" — visibly empty in the source), so a
non-hallucinating system must say the document doesn't state it.
"""

from __future__ import annotations

from evaluation.datasets.build.common import write_jsonl
from evaluation.datasets.schema import LegalQARecord

FIXTURE = "fir_0125_bhayandar.pdf"

_SOURCE_NOTE = (
    "Source: sample_pdf/0125 Publish FIR.pdf, page {page} — fact copied verbatim "
    "from the printed form field, not inferred."
)


def build() -> list[LegalQARecord]:
    return [
        LegalQARecord(
            id="legalqa_fir_0125_number",
            tags=["real_document", "fir", "factual"],
            notes=_SOURCE_NOTE.format(page=1) + " Item 1: 'FIR No. (प्रथम खबर क्र.): 0125'.",
            file_path=FIXTURE,
            question="What is the FIR number mentioned in this document?",
            reference_answer="0125",
            must_contain=["0125"],
            should_refuse=False,
        ),
        LegalQARecord(
            id="legalqa_fir_0125_date",
            tags=["real_document", "fir", "factual"],
            notes=_SOURCE_NOTE.format(page=1) + " Item 1: 'Date and Time of FIR ... 30/03/2026 20:11'.",
            file_path=FIXTURE,
            question="On what date was this FIR registered?",
            reference_answer="30/03/2026",
            must_contain=["30/03/2026"],
            should_refuse=False,
        ),
        LegalQARecord(
            id="legalqa_fir_0125_sections",
            tags=["real_document", "fir", "factual", "bns"],
            notes=_SOURCE_NOTE.format(page=1) + " Item 2 lists 6 BNS 2023 sections: 115(2), 3(5), 85, 316(2), 352, 356(1).",
            file_path=FIXTURE,
            question="Which BNS sections are cited as the acts and sections in this FIR?",
            reference_answer="Bharatiya Nyaya Sanhita (BNS) 2023, Sections 115(2), 3(5), 85, 316(2), 352, and 356(1).",
            must_contain=["115", "85", "316", "352", "356"],
            should_refuse=False,
        ),
        LegalQARecord(
            id="legalqa_fir_0125_marriage_date",
            tags=["real_document", "fir", "factual"],
            notes=_SOURCE_NOTE.format(page=5) + " Narrative: 'माझे लग्न दिनांक 07/02/2022 रोजी ... झाले'.",
            file_path=FIXTURE,
            question="According to the complaint narrative, on what date did the complainant get married?",
            reference_answer="07/02/2022",
            must_contain=["07/02/2022", "2022"],
            should_refuse=False,
        ),
        LegalQARecord(
            id="legalqa_fir_0125_io_name",
            tags=["real_document", "fir", "factual"],
            notes=_SOURCE_NOTE.format(page=7) + " Item 13(2): 'Directed (Name of I.O.) ... HITENDRA JAGANNATH CHAVAN'.",
            file_path=FIXTURE,
            question="Who is the investigating officer directed to take up the investigation?",
            reference_answer="Hitendra Jagannath Chavan, Police Sub-Inspector.",
            must_contain=["Hitendra", "Chavan"],
            should_refuse=False,
        ),
        LegalQARecord(
            id="legalqa_fir_0125_mobile",
            tags=["real_document", "fir", "factual"],
            notes=_SOURCE_NOTE.format(page=3) + " Item 6(j): 'Mobile ... 91-8291083441'.",
            file_path=FIXTURE,
            question="What is the complainant's mobile number as recorded in the FIR?",
            reference_answer="91-8291083441",
            must_contain=["8291083441"],
            should_refuse=False,
        ),
        LegalQARecord(
            id="legalqa_fir_0125_property_value_absent",
            tags=["real_document", "fir", "honesty_check"],
            notes=_SOURCE_NOTE.format(page=5) + " Item 10 'Total value of property (In Rs/-)' is printed with no "
                  "value filled in — the field is genuinely blank in the source document.",
            file_path=FIXTURE,
            question="What is the total value of the property mentioned in this FIR?",
            reference_answer="The document does not state a total property value.",
            must_contain=[],
            should_refuse=True,
        ),
        LegalQARecord(
            id="legalqa_fir_0125_passport_absent",
            tags=["real_document", "fir", "honesty_check"],
            notes=_SOURCE_NOTE.format(page=2) + " Item 6(f) 'Passport No.' is printed with no value filled in.",
            file_path=FIXTURE,
            question="What is the complainant's passport number?",
            reference_answer="The document does not record a passport number for the complainant.",
            must_contain=[],
            should_refuse=True,
        ),
    ]


if __name__ == "__main__":
    recs = build()
    write_jsonl(recs, "legal_qa.jsonl")
    print(f"[BUILD] legal_qa: {len(recs)} records over 1 real fixture "
          f"({sum(1 for r in recs if r.should_refuse)} honesty/refusal checks)")
