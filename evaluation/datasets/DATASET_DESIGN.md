# NyayaSetu Evaluation — Ground Truth Dataset Design

This is the design reference for the datasets under `evaluation/datasets/raw/`.
For the actual current record counts, distributions, and gap analysis, see the
generated `DATASET_REPORT.md` (regenerate it with
`python -m evaluation.datasets.build.report` after any dataset change — every
number there is computed from the files, never hand-typed).

Build scripts live in `evaluation/datasets/build/`, one per dataset (plus
`common.py` for shared helpers, `validate_all.py`, `report.py`, and
`run_all.py` to run everything in order). Every build script's module
docstring states its exact source of truth — this document is the index;
the build script is the citation.

**Ground rule for this entire layer**: no LLM writes a label. An LLM may be
used only to *phrase* a query string from source material that already
determines the fact (e.g. turning a statute's own section title into a
natural-language question) — never to invent the answer, the section
number, the mapping, or the risk level. Every record's `notes` field says
which real, already-existing project source it was derived from.

---

## 1. Legal Question Answering — `legal_qa.jsonl`

- **Purpose**: evaluate `DocumentRAG.answer()` — per-document follow-up Q&A
  (`POST /api/analyze` then `POST /api/qa`) — for both answer correctness
  and honesty (does it refuse when the document doesn't contain the answer,
  rather than inventing one).
- **Schema**: `LegalQARecord` (`evaluation/datasets/schema.py`) — `id`,
  `tags`, `notes`, `file_path`, `question`, `reference_answer`,
  `must_contain: list[str]`, `should_refuse: bool`.
- **Fields**: `file_path` is relative to `raw/fixtures/`. `must_contain` is a
  substring-match heuristic (see `runners/legal_qa.py`'s `groundedness`
  metric) — favour digits, section numbers, and citations over transliterated
  proper nouns, since the pipeline machine-translates non-English documents
  before answering (see `document_analyzer.py`'s Phase 1) and numbers survive
  translation more reliably than names.
- **Validation rules**: `file_path` must resolve under `raw/fixtures/`
  (checked by `validate_all.py`); at least one of `reference_answer` /
  `must_contain` must be non-empty unless `should_refuse=True`.
- **Metadata**: `notes` must cite the exact page/item of the source document
  the fact was copied from.
- **Source of truth**: the one real sample document in this repo,
  `sample_pdf/0125 Publish FIR.pdf` (staged as `fixtures/fir_0125_bhayandar.pdf`).
- **Expected size**: 5-10 questions per real fixture document. Currently 8,
  over 1 fixture — see `DATASET_REPORT.md` section 6 for the fixture-count gap.
- **Used by**: `evaluation/runners/legal_qa.py` → `answer_correctness`
  (embedding cosine similarity), `groundedness`, `refusal_appropriateness`,
  `confidence_calibration`.

## 2. Retrieval Evaluation — `retrieval.jsonl`

- **Purpose**: evaluate the ChromaDB RAG tier in isolation — given a query
  embedding, does vector search return the chunks a human would consider
  relevant, in the right order — independent of the downstream Groq
  extraction step (that's `ipc_bns_mapping.jsonl`'s job).
- **Schema**: `RetrievalRecord` — `id`, `tags`, `notes`, `query`,
  `relevant_chunk_ids: list[str]`, `relevance_grades: dict[id, int]`.
- **Fields**: `relevant_chunk_ids` must be real ChromaDB document ids from
  `data/chromadb`'s `nyayasetu_legal` collection. `relevance_grades` scores
  1-3 (3 = the chunk containing the section's own header text, 2 = the
  immediately adjacent chunk on the same page, by real chunk-index metadata).
- **Validation rules**: every id in `relevant_chunk_ids` must exist in the
  live collection (checked by `validate_all.py` against the collection
  directly, not assumed).
- **Metadata**: `notes` cites the exact chunk id, act, source PDF, and page
  the query was derived from.
- **Source of truth**: `data/chromadb` (`nyayasetu_legal`, 3254 chunks,
  built from `BNS.pdf`/`BNSS.pdf`/`BSA.pdf` by `modules/m2_rag/ingest.py`)
  — read directly and read-only.
- **Expected size**: ideally one query per real statute section (BNS+BNSS+BSA
  have several hundred sections combined). Currently 46, capped by
  non-section-aware fixed-window chunking — see `DATASET_REPORT.md` section 6.
- **Used by**: `evaluation/runners/retrieval.py` → precision@k, recall@k, MRR,
  nDCG@k.

## 3. IPC → BNS Mapping — `ipc_bns_mapping.jsonl`

- **Purpose**: evaluate `LexValidator.get_mapping()`'s full 3-tier cascade
  (RAG → hardcoded table → Groq zero-shot) end to end via
  `POST /api/compliance`, and separately report which tier answered each
  record (a tier-mix shift is itself a finding, not just an accuracy number).
- **Schema**: `IPCBNSMappingRecord` — `id`, `tags`, `notes`, `act`, `section`,
  `expected_bns`, `expected_name`, `text_context`.
- **Fields**: `text_context` is phrased to match
  `backend/lex_validator.py`'s `SectionExtractor` regexes (e.g.
  `"Charged under Section 302 IPC."`) so the reference is actually
  extractable from the text sent to the endpoint.
- **Validation rules**: no `(act, section)` pair may map to two different
  `expected_bns` values across the merged sources (checked by
  `validate_all.py`); `expected_bns` is either a `BNS/BNSS/BSA <n>` string
  or the literal `ABOLISHED`.
- **Metadata**: `notes` states which of the two source tiers (see below)
  produced the record, and for PDF-extracted records, that the source PDF
  is not currently in this repo.
- **Source of truth**: merged from (a) `backend/lex_validator.py`'s
  `FALLBACK_MAPPINGS` dict — the live production fallback table, extracted
  by AST-parsing the source (not importing it, which would require
  `GROQ_API_KEY`) — and (b) `data/ipc_bns_mappings.json`, mechanically
  regex-parsed from the official `ipc_bns.pdf` gazette table by
  `backup/unused/m4_mappings/mapping_loader.py`. Where both cover the same
  section, (a) wins (it's what the live system actually uses).
- **Expected size**: bounded by how many sections the two source tables
  cover — currently 185 unique mappings (70 from the production table, 115
  PDF-extracted-only).
- **Used by**: `evaluation/runners/ipc_bns_mapping.py` → exact-match accuracy,
  `tier_distribution`, `confidence_calibration`.

## 4. Translation — `translation.jsonl`

- **Purpose**: evaluate `backend/legal_translator.py`'s Colab NLLB → Gemini →
  Groq cascade via `POST /api/translate`.
- **Schema**: `TranslationRecord` — `id`, `tags`, `notes`, `source_text`,
  `source_lang`, `target_lang`, `reference_translation`, `expected_engine`.
- **Fields**: `expected_engine` left `None` unless a record specifically
  targets cascade-tier behaviour (none currently do — see gap in
  `DATASET_REPORT.md`).
- **Validation rules**: `source_lang` must be a key in
  `legal_translator.SUPPORTED_LANGUAGES`; `reference_translation` must be
  non-empty (no placeholder references).
- **Metadata**: `notes` states the human-authored source (a government form,
  not a model).
- **Source of truth**: the bilingual field labels printed on the standard
  NCRB I.I.F.-I FIR form, as they appear (both languages) in
  `sample_pdf/0125 Publish FIR.pdf` — government-drafted, human-authored
  translation pairs.
- **Expected size**: currently 12 short terminology pairs — explicitly
  **not** a substitute for full-paragraph translation ground truth, which
  this project has none of (see `DATASET_REPORT.md` section 6 for the
  recommended follow-up: professionally translated parallel-text records).
- **Used by**: `evaluation/runners/translation.py` → chrF,
  `engine_distribution`, `exact_match_engine_expected`.

## 5. Document Analysis — `document_analysis.jsonl`

- **Purpose**: evaluate the full `document_analyzer.py` pipeline via
  `POST /api/analyze` — document-type classification, missing-clause
  detection, overall risk verdict — against human-labeled real documents.
- **Schema**: `DocumentAnalysisRecord` — `id`, `tags`, `notes`, `file_path`,
  `expected_document_type`, `expected_overall_risk`,
  `expected_missing_clauses: list[str]`.
- **Fields**: `expected_document_type` must be one of the exact label
  strings in `document_analyzer.DOCUMENT_TYPES[*]["label"]`.
  `expected_overall_risk` is `Optional` — leave unset rather than guess when
  no authoritative basis exists (as for the FIR fixture: the risk-scoring
  pipeline is designed for contracts, not police reports).
- **Validation rules**: `file_path` must resolve under `raw/fixtures/`;
  `expected_missing_clauses` must be a subset of
  `DOCUMENT_TYPES[key]["required_clauses"]` for the matching type.
- **Metadata**: `notes` names the real document and the exact
  `DOCUMENT_TYPES` key/label it was checked against.
- **Source of truth**: the one real sample document in this repo (see
  Legal QA above) plus `backend/document_analyzer.py`'s own
  `DOCUMENT_TYPES` taxonomy.
- **Expected size**: 2-3 documents per `DOCUMENT_TYPES` key (9 keys) for
  meaningful coverage. Currently 1 record total — the largest gap in this
  build; see `DATASET_REPORT.md` section 6.
- **Used by**: `evaluation/runners/document_analysis.py` →
  `doc_type_accuracy`, `risk_level_agreement`, `missing_clause_f1`,
  `verdict_agreement`.

## 6. Multilingual Evaluation — `multilingual.jsonl`

- **Purpose**: cross-language *consistency* — does translation/analysis
  quality hold across all of `legal_translator.SUPPORTED_LANGUAGES`, not
  just one pair — as distinct from `translation.jsonl`'s single-pair
  quality focus.
- **Schema**: `MultilingualRecord` (added to `datasets/schema.py` this
  phase, additively — same shape as `TranslationRecord` plus a
  `parallel_group` field that ties records sharing the same underlying
  content across languages together). Registered in `SCHEMA_REGISTRY` as
  `"multilingual"` so it validates through the same loader as every other
  suite.
- **Fields**: identical to `TranslationRecord` plus `parallel_group: str`.
- **Validation rules**: same as `translation.jsonl`; additionally, records
  sharing a `parallel_group` should have the same underlying source content
  translated into different `target_lang` values (not currently exercised —
  see gap below).
- **Metadata**: same as `translation.jsonl`.
- **Source of truth**: same NCRB bilingual form labels as `translation.jsonl`
  — Marathi only.
- **Expected size**: ideally the same content across all 12 supported
  languages (`hi, mr, ta, te, kn, bn, gu, ml, pa, or, as, ur`). Currently
  1/12 languages (`mr`) has real source content — 11 languages are an
  explicit, documented gap, not filled with fabricated placeholders.
- **No runner is wired for this suite yet** — same documented status as the
  notebook's `/classify` and `/retrieve` endpoints in
  `evaluation/README.md`. It would reuse `POST /api/translate`'s HTTP
  surface; wiring `runners/multilingual.py` + `config/experiments/
  multilingual.yaml` is a small, separate follow-up once more languages
  have real content.

## 7. Hallucination / Robustness — `robustness.jsonl`

- **Purpose**: two related but distinct things under one schema — (a)
  adversarial/edge-case inputs scored against an explicit
  what-should-happen contract (existing `robustness.yaml` categories), and
  (b) whether the system fabricates a plausible-looking legal fact
  (a BNS section number) instead of correctly reporting "abolished" or
  "unknown" (new `hallucination` category, added this phase).
- **Schema**: `RobustnessRecord` (unchanged) — `id`, `tags`, `notes`,
  `category`, `endpoint`, `payload`, `expected_behavior`.
- **Fields**: `expected_behavior` must be one of the three values
  `metrics/robustness_metrics.py` actually recognizes — `clean_4xx`,
  `graceful_fallback`, `clear_error_message` — anything else is silently
  excluded from `graceful_degradation_rate`, not scored as a failure.
- **Validation rules**: mechanical-category `expected_behavior` values must
  be grounded in code actually read (cited in `notes`) or well-established
  framework behaviour (FastAPI/Pydantic validation), never guessed.
  `hallucination` records must cite a specific, verifiable fact (a real
  `ABOLISHED` entry, or a section number checked absent from every mapping
  source in this project) in `notes`.
- **Metadata**: `notes` states exactly which code path or fact the
  expectation is grounded in.
- **Source of truth**: `backend/lex_validator.py` (code read directly,
  `FALLBACK_MAPPINGS` for the hallucination probes), `backend/api.py` /
  `backend/legal_translator.py` (code read directly, for the mechanical
  categories), and well-documented FastAPI/Pydantic behaviour.
- **Expected size**: currently 8 (5 mechanical across 5 of 6 declared
  categories + 3 hallucination probes). `upstream_unavailable` has zero
  records — it needs fault-injection infrastructure this dataset-only
  phase doesn't build; see `DATASET_REPORT.md` section 6.
- **Used by**: `evaluation/runners/robustness.py` →
  `graceful_degradation_rate`, `crash_rate`, `error_message_quality`.
  **Important limitation**: the hallucination records' actual claim
  (did the response fabricate a section number) is not yet scored by any
  metric function — see `DATASET_REPORT.md` section 6's framework-gap entry.

## 8. Research Search — `research.jsonl`

- **Purpose**: evaluate `POST /api/research/ask` — IndianKanoon retrieval +
  Groq synthesis with inline `[N]` citation markers.
- **Schema**: `ResearchRecord` — `id`, `tags`, `notes`, `query`,
  `min_citations`, `expected_topics`.
- **Fields**: `expected_topics` values are restricted to the 6 literal
  category names `backend/api.py`'s `research_topics()` returns
  (`"Constitutional & Administrative"`, `"Criminal Law"`, `"Civil & Property"`,
  `"Corporate & Commercial"`, `"Tax Laws"`, `"Labour & Service"`).
- **Validation rules**: `min_citations` must not assert a specific real
  citation count without a live, reproducible source — kept at a
  conservative floor (1) since this environment has no
  `INDIANKANOON_API_KEY` configured.
- **Metadata**: `notes` cites the `data/legal_kb.json` offence id the query
  was derived from.
- **Source of truth**: `data/legal_kb.json`'s 18 hand-curated offence
  records (each with a real `bns_section`).
- **Expected size**: one query per curated offence — currently 18, i.e. full
  coverage of the existing `legal_kb.json`. Growing this further means
  growing `legal_kb.json` itself first (a product KB decision, not an
  evaluation-dataset one).
- **Used by**: `evaluation/runners/research.py` → `citation_validity`,
  `citation_count`, `answer_relevancy` (unscored placeholder — see that
  runner's own docstring).

## 9. End-to-End Evaluation — `end_to_end.jsonl`

- **Purpose**: full request traces — upload a non-English document →
  analyze → compliance-check → Q&A — verifying every reachable stage
  actually ran, not silently skipped.
- **Schema**: `EndToEndRecord` — `id`, `tags`, `notes`, `file_path`,
  `source_lang`, `question`, `expected_stages`.
- **Fields**: `expected_stages` should list only stages
  `evaluation/runners/end_to_end.py` can actually mark complete
  (`["analyze", "compliance", "qa"]`) — the runner never appends the
  literal string `"translate"` to `stages_completed` (translation happens
  inside the single `/api/analyze` call and isn't separately observable),
  so using the schema's default 4-stage list would structurally cap
  `stage_completion_rate` at 3/4 regardless of real behaviour. This is a
  dataset-authoring choice, not a runner change.
- **Validation rules**: same `file_path` rule as document_analysis/legal_qa.
- **Metadata**: `notes` cross-references the `legal_qa.jsonl` record the
  question was reused from, where applicable.
- **Source of truth**: same single real fixture as document_analysis/legal_qa.
- **Expected size**: 2-3 traces per real fixture document. Currently 2, over
  1 fixture — grows automatically once more fixtures exist (gap #1 above).
- **Used by**: `evaluation/runners/end_to_end.py` → `stage_completion_rate`,
  `stage_latency_breakdown`, `final_output_validity`.

---

## Corpus-expansion provenance (NyayaSetu Legal Benchmark v1.0)

On top of the phase-1 datasets described above, `evaluation/datasets/build/corpus/`
adds records extracted from a configurable EXTERNAL legal-document corpus (path
never hardcoded — see `corpus/config.py`). These records:

- carry `tags` including `corpus_expansion` and the source category (e.g. `fir`,
  `court_notice`);
- populate the `provenance` dict every `BaseRecord` has (`source_file`, `page_count`,
  `category`, `extracted_at`, `source_citation`) — phase-1 records leave this `{}`
  and rely on `notes` instead, since they were built directly from named, permanent
  in-repo sources rather than an external, per-machine-configured corpus;
- for `document_analysis` / `legal_qa` / `end_to_end`: reference their source file
  via `provenance.source_file` only, NOT by copying the PDF into git-tracked
  `raw/fixtures/` — a deliberate choice (see `NSLB_REPORT.md`) because the source
  corpus's FIR and Affidavit documents contain real people's PII. `file_path` is set
  to a `<external-corpus>/...` marker the CURRENT runners do not resolve; running
  these specific records needs a small, separately-reviewed runner change or a
  manual, privacy-reviewed copy — flagged, not silently gapped.

See `CORPUS_INVENTORY.md` for the full external-corpus inspection (every file, not
a sample) and `NSLB_REPORT.md` for benchmark size before/after, coverage analysis,
and the publication-readiness estimate.

## Build / validate / report workflow

```bash
python -m evaluation.datasets.build.run_all       # builds all 9 datasets from source
python -m evaluation.datasets.build.validate_all  # loader-level + cross-dataset checks
python -m evaluation.datasets.build.report        # regenerates DATASET_REPORT.md
```

Each `build_*.py` is independently re-runnable and idempotent — re-running
after a project source changes (e.g. `FALLBACK_MAPPINGS` gains an entry, or
`data/chromadb` is re-ingested) regenerates the affected dataset from the
current state of that source, not from a stale snapshot.
