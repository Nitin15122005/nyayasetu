# NyayaSetu Legal Benchmark (NSLB) — Version 1.0

Generated: 2026-08-07T13:50:55+00:00

NSLB v1.0 = the phase-1 benchmark (built from NyayaSetu's own in-repo corpus: ChromaDB, `lex_validator.py`'s mapping tables, `legal_kb.json`, one real sample document) **expanded, not replaced**, with records derived from an external legal-document corpus. See `CORPUS_INVENTORY.md` for the full-corpus inspection and `DATASET_DESIGN.md` for the per-dataset schema/source-of-truth reference (both existing docs, updated for this expansion).

## 1. Benchmark size: previous vs new

| Dataset | Phase-1 (previous) | NSLB v1.0 (current) | Change |
|---|---|---|---|
| ipc_bns_mapping | 185 | 185 | 0 |
| retrieval | 46 | 46 | 0 |
| document_analysis | 1 | 90 | +89 |
| legal_qa | 8 | 67 | +59 |
| end_to_end | 2 | 11 | +9 |
| translation | 12 | 12 | 0 |
| multilingual | 12 | 12 | 0 |
| robustness | 8 | 11 | +3 |
| research | 18 | 43 | +25 |
| **Total** | **292** | **477** | **+185** |

## 2. Corpus processing summary

- External corpus location (configured, not hardcoded): `D:\Programs\raw-pdfs`
- **Documents inventoried (full corpus scan)**: 4020
- **Documents deep-processed (sampled for extraction)**: 94 (2.3% of the inventoried corpus — see `corpus/sampling.py` for the documented per-category caps and rationale; the other ~98% is fully inventoried but not deep-extracted in this pass)
- **Records generated (pre-validation)**: 194
- **Records rejected at generation time**: 5 ({'document_analysis_duplicate_summary': 5})
- **Records rejected at validation time** (true content duplicates, auto-cleaned — see `validate_all.py`'s `check_duplicate_content`): 9
- **Duplicate/rejection rate**: 7.0% of all generated-or-attempted records
- **Net new records kept**: 185

## 3. Records generated per dataset (this expansion only)

- document_analysis: 89
- legal_qa: 68
- end_to_end: 9
- research: 25
- robustness: 3
- ipc_bns_mapping: 0 — see section 6 for why
- retrieval: 0 — see section 6 for why
- translation: 0 — see section 6 for why
- multilingual: 0 — see section 6 for why

## 4. Category distribution (documents deep-processed)

- Legal_Notice: 40
- FIR: 25
- Court_Notice: 20
- Affidavit: 8
- Bail_Application: 1

## 5. Language distribution

**Corpus-wide** (all 4020 inventoried files, from `CORPUS_INVENTORY.md`):
  - en: 3794 (94.4%)
  - mr: 194 (4.8%)
  - unknown: 32 (0.8%)

**Deep-processed sample** (94 documents actually extracted):
  - en: 69
  - mr: 25

No language beyond English and Marathi appears anywhere in this external corpus (confirmed by the full inventory scan, not just the sample) — the multilingual gap identified in phase 1 (11 of 12 `legal_translator.SUPPORTED_LANGUAGES` have no real source content) is **not closed by this corpus** and remains open. `multilingual.jsonl` was deliberately left unchanged this pass rather than padded with repeated form-label pairs that add count without adding real coverage.

## 6. Retrieval coverage

**0 new retrieval.jsonl records were generated.** Mechanism: corpus documents' real section citations were cross-referenced against `ipc_bns_mapping.jsonl` to find a BNS equivalent, then checked against phase-1 `retrieval.jsonl`'s already chromadb-verified chunk ids (only 46 sections, out of several hundred real BNS/BNSS/BSA sections, are covered there — see phase-1's `DATASET_REPORT.md` section 6). None of the 3 corpus citations that DID resolve to a known BNS section happened to land on one of those 46 already-covered sections. This is a real null result, not a bug — it quantifies exactly how sparse retrieval.jsonl's section coverage still is relative to real-world citation patterns.

## 7. IPC/BNS citation coverage

- Total section-style citations found across the 94 deep-processed documents: **9**
- Documents with zero extractable section citations: **89/94** — most Affidavit/Bail_Application/Legal_Notice/Court_Notice documents in this corpus don't cite specific numbered penal-code sections in a regex-matchable form (they're procedural/civil documents, not always charge sheets), and this pipeline does not fabricate a citation that isn't literally in the text.
- Distinct sections cited: ['CrPC 417', 'IPC 188', 'IPC 28', 'IPC 3', 'IPC 302', 'IPC 413', 'IPC 448', 'IPC 75', 'IPC 84']
- Of those, matched to a known mapping in `ipc_bns_mapping.jsonl`: ['IPC 28', 'IPC 302', 'IPC 448'] (3/9 citation instances, 33%)
- **Unmatched** (real citations found in real documents, with no entry in either merged mapping source): ['CrPC 417', 'IPC 188', 'IPC 3', 'IPC 413', 'IPC 75', 'IPC 84'] — candidates for a human to manually verify and add to `ipc_bns_mapping.jsonl` in a future pass, NOT auto-added here (adding an unverified mapping would be exactly the kind of fabrication this phase must avoid).

## 8. Document coverage

- 4020/4020 (100%) of the external corpus was inventoried (page counts, language, corruption, OCR-need, duplicates — see `CORPUS_INVENTORY.md`).
- 94/4020 (2.3%) were deep-extracted into evaluation records — a deliberate, documented sample (see `corpus/sampling.py`), not the full corpus.
- Property_Deed category: **0 documents processed** — its only real PDF needs OCR (no OCR engine is wired into this pipeline) and its other 27 files are .doc/.docx, outside this PDF-only pipeline's scope.

## 9. Publication-readiness estimate

**Better than phase-1, still not publication-ready.** The benchmark grew from 292 to 477 records (63% growth), all still real, source-traceable, and passing every structural/consistency check `validate_all.py` runs. The three phase-1 gaps that mattered most are only partially closed:

- **document_analysis fixture count**: 1 -> 90 (90x growth) — the single largest phase-1 gap is now substantially addressed, though still concentrated in FIR/Legal_Notice/Court_Notice/Affidavit; still zero coverage for rental_agreement, employment_contract, loan_agreement, sale_agreement, service_agreement, and nda — none of `DOCUMENT_TYPES`'s contract-style categories appear in this corpus at all.
- **legal_qa fixture diversity**: 8 -> 67 — real growth, but still template-generated self-referential QA ("which sections are cited", "what dates appear"), not human-authored comprehension questions. No new `should_refuse` honesty-check records were added this pass.
- **multilingual coverage**: unchanged, 1/12 supported languages. This corpus cannot close this gap (see section 5) — it needs a genuinely different source.

**Remaining gaps for a publication-grade NSLB v1.1+**:

| Gap | Recommendation |
|---|---|
| Zero contract-type documents (rental/employment/loan/sale/service/NDA) | Source a SEPARATE corpus for these — this external corpus is entirely litigation/procedural documents, structurally incapable of filling this gap. |
| legal_qa is 100% template-generated, 0% human-authored comprehension questions | Commission human review of a sample (recommend 30-40 records) to write real comprehension questions (not just "what's cited/dated") with verified answers. |
| Property_Deed category effectively empty (0 usable PDFs) | Source real, OCR'd, or born-digital property deed PDFs; current single file needs OCR this pipeline doesn't run. |
| 6 real cited sections have no verified BNS mapping | Human-verify and add ['CrPC 417', 'IPC 188', 'IPC 3', 'IPC 413', 'IPC 75', 'IPC 84'] to `ipc_bns_mapping.jsonl`. |
| retrieval.jsonl gained 0 records despite 94 new documents | Grow retrieval.jsonl's own section-header coverage first (phase-1 gap, see prior report) — corpus citations can only test what's already covered. |
| Affidavit/Bail_Application/Court_Notice/Property_Deed have no DOCUMENT_TYPES entry | Product decision, not a dataset gap: either add these as real classifier categories in `backend/document_analyzer.py`, or accept 'General Legal Document' as the correct answer for them (current behavior, which this benchmark now explicitly tests via the `no_taxonomy_match_expected_unknown` tag). |
| 31/39 Affidavits and the Property_Deed PDF need OCR | No OCR engine is wired into this pipeline; `pytesseract` already exists as a dependency for image uploads (`backend/lex_validator.py`) but isn't invoked here — a scoped follow-up, not a redesign. |

Overall: recommend roughly **50-70 additional human-reviewed records** (concentrated in contract-type documents and genuine comprehension QA) plus a **separate multilingual source acquisition effort** before NSLB is publication-grade — smaller than phase-1's 75-100 estimate because document_analysis/legal_qa/end_to_end's fixture-count gap, the biggest single item, is now substantially addressed.
