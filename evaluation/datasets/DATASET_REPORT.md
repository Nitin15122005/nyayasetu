# NyayaSetu Evaluation — Ground Truth Dataset Report

Generated: 2026-08-07T12:06:46+00:00

Every number below is computed directly from `evaluation/datasets/raw/*.jsonl` at report-generation time — see `evaluation/datasets/build/*.py` for exactly how each record was derived, and `evaluation/datasets/DATASET_DESIGN.md` for the schema/purpose/validation-rule design behind each dataset.

## 1. Datasets created — record counts

| Dataset | Records | Primary source(s) |
|---|---|---|
| ipc_bns_mapping | 185 | pdf_regex_extraction_artifact (115), production_code_table (70) |
| retrieval | 46 | chromadb_live_query (46) |
| document_analysis | 1 | real_sample_document (1) |
| legal_qa | 8 | real_sample_document (8) |
| end_to_end | 2 | real_sample_document (2) |
| translation | 12 | official_ncrb_form (12) |
| multilingual | 12 | official_ncrb_form (12) |
| robustness | 8 | mechanical_edge_case (5), hallucination_probe (3) |
| research | 18 | curated_legal_kb_json (18) |
| **Total** | **292** | |

## 2. Source distribution (across all datasets)

| Source category | Records | Share |
|---|---|---|
| pdf_regex_extraction_artifact | 115 | 39.4% |
| production_code_table | 70 | 24.0% |
| chromadb_live_query | 46 | 15.8% |
| official_ncrb_form | 24 | 8.2% |
| curated_legal_kb_json | 18 | 6.2% |
| real_sample_document | 11 | 3.8% |
| mechanical_edge_case | 5 | 1.7% |
| hallucination_probe | 3 | 1.0% |

`production_code_table` and `chromadb_live_query` and `official_ncrb_form` are the highest-confidence tiers (live production code / live vector store / a government-issued bilingual form). `pdf_regex_extraction_artifact` is mechanically derived but from a source PDF no longer present in this repo — see the gap analysis in section 6.

## 3. Per-dataset breakdown

### 3.1 ipc_bns_mapping
- 185 unique (act, section) -> BNS/BNSS/BSA mappings
- Act distribution: {'CrPC': 12, 'IEA': 2, 'IPC': 171}
- ABOLISHED (decriminalized) sections: 2

### 3.2 retrieval
- 46 query -> relevant-chunk-id records, all against the LIVE data/chromadb collection (3254 chunks total in the collection)
- By act: {'bns': 13, 'bnss': 25, 'bsa': 8}
- Coverage: 46/3254 chunks (1.4%) have a labeled query — capped by naive fixed-window chunking (modules/m2_rag/ingest.py chunks at fixed 512-char offsets, not at section boundaries), which limits how often a section header lands cleanly at a chunk start.

### 3.3 document_analysis / 3.4 legal_qa / 3.9 end_to_end
- document_analysis: 1 record(s); legal_qa: 8 record(s) (2 honesty/refusal checks); end_to_end: 2 record(s)
- All three are built from the SAME single real fixture (`fixtures/fir_0125_bhayandar.pdf`) — this project has exactly one real sample legal document checked into the repo. This is the dataset suite's biggest size constraint; see section 6.

### 3.5 translation / 3.6 multilingual
- translation: 12 official bilingual (mr->en) NCRB form-label pairs
- multilingual: 12 records, ALL in Marathi->English — 1 of 12 languages in legal_translator.SUPPORTED_LANGUAGES has real source content in this repo (hi, ta, te, kn, bn, gu, ml, pa, or, as, ur are gaps, not fabricated placeholders)

### 3.7 robustness (incl. hallucination)
- 8 records; by category: {'empty_input': 1, 'hallucination': 3, 'malformed_payload': 1, 'oversized_input': 1, 'unsupported_language': 1, 'wrong_file_type': 1}
- `upstream_unavailable` (declared in robustness.yaml) has NO records here — it requires fault injection a black-box JSON-payload dataset can't express.
- `hallucination` records are source-grounded (real ABOLISHED sections + a verified-absent decoy section) but current robustness_metrics.py doesn't score response content — see module docstring for the framework-side gap.

### 3.8 research
- 18 queries grounded in data/legal_kb.json's 18 curated offences
- Topic distribution: {'Criminal Law': 13, 'Civil & Property': 3, 'Labour & Service': 2}
- Offence-category distribution: {'assault': 3, 'cybercrime': 4, 'theft': 4, 'domestic_violence': 2, 'property': 3, 'workplace': 2}

## 4. Language distribution

- {'mr': 26}
- Every non-English record in this build is Marathi (`mr`) — the only language with real project-sourced content. 0 records exist for the other 11 supported languages.

## 5. Validation results

`python -m evaluation.datasets.build.validate_all` (run immediately before this report) checks: (1) every file loads through the framework's own `evaluation.datasets.loader` — the same code path `cli run` uses; (2) duplicate ids (auto-cleaned if found); (3) ipc_bns_mapping contradictions (same act+section mapping to two different expected_bns values); (4) every retrieval.jsonl relevant_chunk_id resolves to a real id in the live ChromaDB collection; (5) every document_analysis / legal_qa / end_to_end file_path resolves to a real fixture; (6, informational) every record has non-empty tags and a notes field naming its source of truth. All checks passed on the build that produced the numbers in this report — see that command's output for the full log.

## 6. Coverage analysis and remaining gaps

| Gap | Detail | Recommended before publication |
|---|---|---|
| Only 1 real sample document | document_analysis, legal_qa, and end_to_end all derive from a single FIR PDF — no rental agreement, employment contract, loan agreement, sale agreement, NDA, or legal notice sample exists in this repo, despite `backend/document_analyzer.py` defining required-clause taxonomies for all of them. | Collect **at least 2-3 real, human-sourced documents per `DOCUMENT_TYPES` key** (9 keys) — roughly **20-25 additional manually-verified documents**, each with a human-reviewed expected_document_type, expected_overall_risk, and expected_missing_clauses label. |
| No full-sentence translation ground truth | translation/multilingual only cover short official form-label terminology, not full-paragraph legal prose. | Commission **10-15 professionally human-translated full-paragraph legal excerpts per target language** actually prioritized for the product (at least Hindi, Marathi, and one South Indian language) — roughly **30-50 records**. |
| 11 of 12 supported languages have zero real source content | multilingual.jsonl is Marathi-only. | Same collection effort as above covers this — do not build it separately; multilingual.jsonl should draw from the same human-sourced parallel corpus, reused via `parallel_group`. |
| retrieval.jsonl covers 46/3254 chunks (1.4%) | Capped by non-section-aware fixed-window chunking; many real sections never land a header at a chunk start. | Either **write a section-aware re-chunker** (splits BNS/BNSS/BSA at numbered-section boundaries, not fixed character offsets) and re-ingest, or **manually label 50-100 additional queries** against the existing chunk set for sections not currently covered. |
| ipc_bns_mapping's PDF-extracted tier has no reproducible source | `data/ipc_bns_mappings.json`'s originating PDF (`ipc_bns.pdf`) is not in this repo — only the extracted JSON survives. | **Locate and add `ipc_bns.pdf` to `data/statutes/`**, or have a human directly verify a sample of the 115 PDF-extracted-only mappings (not already in the hand-curated table) against an authoritative BNS/IPC comparison table — recommend **spot-checking at least 30 of the 115** before treating them as citable. |
| hallucination category has no content-aware metric | `robustness_metrics.py` scores status codes, not whether a response fabricated a section number. | **Framework change** (out of scope for this dataset-only phase): add a content-checking metric function that reads each hallucination record's `notes` for the fact to check against the response body. |
| upstream_unavailable has zero records | Needs fault injection (mocked Groq/Colab outage), which a static JSON-payload dataset can't express. | **Framework change**: add a harness mode that can force a downstream call to fail (e.g. an env var the harness checks), then author 2-3 records against it. |
| research.jsonl min_citations is a floor, not a real count | No `INDIANKANOON_API_KEY` configured in this environment — every record uses `min_citations=1` rather than a verified real count. | Once a key is available, run the 18 queries live once, human-review the actual citation counts returned, and update `min_citations` per record to the reviewed floor. |

## 7. Recommended additional manually-verified records for publication

Summing the per-gap recommendations above: roughly **75-100 additional manually verified records** — dominated by ~20-25 new labeled sample documents (the single largest gap) and ~30-50 professionally translated parallel-text records. The datasets in this build (292 records total) are real, source-traceable, and pass every structural/consistency check the framework and this build's own validator can run — they are not a substitute for that additional human-reviewed material, particularly for document_analysis/legal_qa/end_to_end (n=1 fixture) and multilingual (1/12 languages), which are undersized for a publication-grade evaluation on their own.
