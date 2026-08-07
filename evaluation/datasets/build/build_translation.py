# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/build_translation.py

Ground truth: official bilingual field labels printed on the standard
NCRB I.I.F.-I First Information Report form (the same form used in
sample_pdf/0125 Publish FIR.pdf) — a nationally standardised Government
of India police form that prints every field label in both Marathi and
English side by side. These are government-drafted, human-authored
translation pairs, not model output — about as authoritative as
legal-domain terminology ground truth gets without commissioning a
professional translator directly.

Scope and an explicit limitation (see DATASET_REPORT.md): this covers
short domain terminology (form field labels), not full free-text
paragraph translation — the project has no human-verified parallel
corpus of full legal-document prose in the repo, and this build script
does not fabricate one via an LLM. The narrative body of the FIR
(page 5-7 of the fixture) is real Marathi legal text but has no
verified English reference translation in the project, so it is NOT
included here — see the report's gap analysis.

multilingual.jsonl reuses the same records (parallel_group="ncrb_fir_form_labels"):
of legal_translator.SUPPORTED_LANGUAGES' 12 non-English languages, only
Marathi has real source content available in this repo. The other 11 are
a documented, explicit gap — not filled with placeholders.
"""

from __future__ import annotations

from evaluation.datasets.build.common import write_jsonl
from evaluation.datasets.schema import MultilingualRecord, TranslationRecord

_SOURCE_NOTE = (
    "Source: NCRB I.I.F.-I First Information Report form (standard Government of India "
    "police form), as printed bilingually in sample_pdf/0125 Publish FIR.pdf. Both the "
    "Marathi and English strings are printed on the official form itself — not a model "
    "translation of one into the other."
)

# (marathi, english) — verbatim from the bilingual form headers.
_PAIRS = [
    ("प्रथम खबर अहवाल", "First Information Report"),
    ("पोलीस ठाणे", "Police Station"),
    ("जिल्हा", "District"),
    ("तक्रारदार / माहिती देणारा", "Complainant / Informant"),
    ("वडिलांचे नाव", "Father's Name"),
    ("राष्ट्रीयत्व", "Nationality"),
    ("घटनास्थळ", "Place of Occurrence"),
    ("अधिनियम", "Acts"),
    ("कलम", "Sections"),
    ("मालमत्तेचे एकूण मूल्य", "Total value of property"),
    ("प्रकरण नोंदविले आणि तपासाचे काम हाती घेतले", "Registered the case and took up the investigation"),
    ("खबर तक्रारदाराला वाचून दाखवली", "F.I.R. read over to the complainant / informant"),
]


def build_translation() -> list[TranslationRecord]:
    return [
        TranslationRecord(
            id=f"trans_ncrb_{i:02d}",
            tags=["official_form_label", "ncrb_fir_form", "terminology"],
            notes=_SOURCE_NOTE,
            source_text=mr,
            source_lang="mr",
            target_lang="en",
            reference_translation=en,
            expected_engine=None,
        )
        for i, (mr, en) in enumerate(_PAIRS, start=1)
    ]


def build_multilingual() -> list[MultilingualRecord]:
    return [
        MultilingualRecord(
            id=f"multi_ncrb_{i:02d}",
            tags=["official_form_label", "ncrb_fir_form", "terminology",
                  "coverage_gap_11_of_12_languages_missing_real_source"],
            notes=_SOURCE_NOTE + (
                " NOTE: only Marathi is populated here. legal_translator.SUPPORTED_LANGUAGES "
                "lists 12 non-English languages; this repo contains no real source content in "
                "the other 11 (hi, ta, te, kn, bn, gu, ml, pa, or, as, ur) — deliberately not "
                "fabricated. See DATASET_REPORT.md for the recommended follow-up."
            ),
            source_text=mr,
            source_lang="mr",
            target_lang="en",
            reference_translation=en,
            expected_engine=None,
            parallel_group="ncrb_fir_form_labels",
        )
        for i, (mr, en) in enumerate(_PAIRS, start=1)
    ]


if __name__ == "__main__":
    t = build_translation()
    m = build_multilingual()
    write_jsonl(t, "translation.jsonl")
    write_jsonl(m, "multilingual.jsonl")
    print(f"[BUILD] translation: {len(t)} official bilingual term pairs (mr->en only)")
    print(f"[BUILD] multilingual: {len(m)} records — 1/12 supported languages covered "
          f"with real source content; 11-language gap documented in the report")
