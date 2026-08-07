# NyayaSetu Evaluation Framework

Status: **infrastructure only — no evaluation has been run yet.** Every dataset under `datasets/raw/` is empty; `datasets/templates/` shows the format. This document describes the framework that will produce results once real datasets are populated, not results themselves.

## Why a separate subsystem

This lives at `evaluation/`, a sibling of `backend/`, `frontend/`, `modules/` — not inside any of them — because it evaluates the *deployed system*, not internal functions. Every evaluator talks to the backend over HTTP (`harness/client.py`) or to the Colab notebook over HTTP (`harness/notebook_client.py`), the same way a real user or the frontend would. Two narrow exceptions import repo code directly (`harness/direct_adapter.py`): chunking and raw-retrieval-in-isolation, because neither has an HTTP endpoint. That's a deliberate, documented exception, not a crack in the design.

This also means the framework survives backend refactors — it only breaks if the *API contract* changes, which is the right level of coupling for something meant to produce comparable numbers across code versions, including for a paper's "before/after" section.

## Capability inventory this framework covers

Built from a full read of `backend/`, `modules/`, and `NyayaSetu_Final_Corrected.ipynb`:

| Capability | Live entry point | Evaluator |
|---|---|---|
| Infra/service health | `GET /api/health`, notebook `/health`, ChromaDB, DB | `runners/infra_health.py` |
| Translation | `POST /api/translate` (NLLB→Gemini→Groq cascade) | `runners/translation.py` |
| Embeddings | notebook `/embed` directly | `runners/embeddings.py` |
| Chunking | `modules/m2_rag/ingest.py::chunk_pages` (no HTTP) | `runners/chunking.py` |
| Retrieval (statute RAG, isolated) | ChromaDB `data/chromadb` directly | `runners/retrieval.py` |
| IPC→BNS mapping (full cascade) | `POST /api/compliance` | `runners/ipc_bns_mapping.py` |
| Compliance scoring | `POST /api/compliance` | `runners/compliance.py` |
| Document analysis | `POST /api/analyze` | `runners/document_analysis.py` |
| Legal Q&A | `POST /api/analyze` → `POST /api/qa` | `runners/legal_qa.py` |
| Research (case law) | `POST /api/research/ask` (IndianKanoon, external) | `runners/research.py` |
| Summarization | `POST /api/analyze`'s summary field (Colab BART→Groq) | `runners/summarization.py` |
| Confidence calibration | reads other suites' results, no live calls | `runners/confidence.py` |
| End-to-end pipeline | translate→analyze→compliance→qa chained | `runners/end_to_end.py` |
| Performance | concurrent replay of any endpoint | `runners/performance.py` |
| Robustness | adversarial payloads against declared contracts | `runners/robustness.py` |

Two capabilities exist in the codebase but have **no live entry point** and so are *not* independently evaluable yet: `classify_document()` (notebook `/classify`, MuRIL document-type classifier) and `retrieve_similar()` (notebook `/retrieve`, hybrid search over the classifier's own training corpus — not the statute corpus). Both are notebook-compatible and ready to wire up; a suite for either is a small addition once a feature calls them.

## Directory structure

```
evaluation/
├── config/
│   ├── schema.py              GlobalConfig + ExperimentConfig dataclasses, YAML loader
│   ├── defaults.yaml           environment-level defaults (backend URL, timeouts, seed)
│   └── experiments/*.yaml      one file per suite — dataset, metrics, suite-specific params
├── datasets/
│   ├── schema.py                one dataclass per suite's record shape
│   ├── loader.py                 JSONL loader + validator (exact file:line errors)
│   ├── templates/*.jsonl.template   format examples — NOT real data, every field is a placeholder
│   └── raw/*.jsonl               real datasets go here (empty in this commit)
├── harness/
│   ├── client.py                 black-box HTTP client for the backend API
│   ├── notebook_client.py         independent HTTP client for the notebook's 6 endpoints
│   ├── direct_adapter.py          the two justified direct-import exceptions (chunking, raw retrieval)
│   └── seeding.py                 reproducibility: RNG seeding + environment/git capture
├── metrics/
│   ├── base.py                    Metric protocol + MetricResult
│   ├── retrieval_metrics.py       precision@k, recall@k, MRR, nDCG@k
│   ├── classification_metrics.py  exact match, accuracy, macro-F1, confusion matrix
│   ├── generation_metrics.py      chrF, ROUGE-L, embedding cosine similarity
│   ├── calibration_metrics.py     ECE, Brier score, reliability bins
│   ├── latency_metrics.py         percentiles, throughput, error rate
│   ├── robustness_metrics.py      graceful-degradation rate, crash rate, error-message quality
│   └── ragas_adapter.py           optional RAGAS wrapper (see below)
├── runners/
│   ├── base.py                    BaseEvaluator — load_dataset / run_single / compute_metrics
│   ├── registry.py                suite name -> evaluator class
│   └── <15 files>                 one evaluator per capability above
├── results/
│   ├── schema.py                  RunManifest, RecordResult, SuiteResult
│   ├── store.py                    JSONL persistence, "latest" resolution
│   └── runs/<suite>/<run_id>/     manifest.json, records.jsonl, aggregate.json
├── reporting/
│   ├── plots.py                    matplotlib figure functions (headless/Agg)
│   ├── report_builder.py            SuiteResult(s) -> report.md + figures/
│   ├── compare.py                   before/after ablation comparison
│   └── templates/report.md.j2       Jinja2 report template
├── cli.py                          `python -m evaluation.cli {list-suites,run,report,compare}`
└── requirements-eval.txt
```

## Adding a new capability

1. Add a dataclass to `datasets/schema.py` and register it in `SCHEMA_REGISTRY`.
2. Add `datasets/templates/<suite>.jsonl.template` showing the shape.
3. Add `config/experiments/<suite>.yaml`.
4. Add `runners/<suite>.py`: subclass `BaseEvaluator`, implement `load_dataset`/`run_single`/`compute_metrics`, decorate with `@register("<suite>")`.
5. Add the import line to `runners/__init__.py`.
6. `python -m evaluation.cli list-suites` should now show it registered.

No other file needs to change — `cli.py`, `report_builder.py`, and `compare.py` are all suite-agnostic.

## Experiment configuration format

Each `config/experiments/<suite>.yaml`:

```yaml
suite: translation
description: "what this suite measures and why"
dataset_file: translation.jsonl      # relative to datasets/raw/, or null if dataset-free
sample_limit: null                    # cap for a quick smoke run; overridable via --limit
metrics: [chrf, engine_distribution, latency_ms]   # documentation of intent; the evaluator decides what it actually computes
repeat: 1                             # repetitions per record, for latency/robustness stats
params: {...}                         # suite-specific knobs (endpoint, top_k, concurrency levels, ...)
```

Merged at load time over `config/defaults.yaml` (backend URL, timeouts, seed, output dirs). `ExperimentConfig.config_hash()` hashes the resolved config and is stamped into every run's manifest — two runs with the same hash used the exact same settings.

## Dataset format

JSONL, one labeled record per line, schema-validated against `datasets/schema.py` at load time. Every record has `id` (stable across revisions — results are diffable run-over-run by id) and `tags` (for slicing results later). See `datasets/README.md` for the raw/ vs templates/ split and how to populate a real dataset. **No real dataset has been created in this phase** — populating one is a deliberate, reviewed step, not something to generate automatically, since it's the ground truth an evaluation's credibility rests on.

## Evaluation runner architecture

`runners/base.py::BaseEvaluator.run()` is the one place the control flow lives:

```
load_dataset() → for each record: run_single() [caught, never aborts the suite]
               → stream RecordResult to records.jsonl as it happens
               → compute_metrics(all records, all outcomes)  [batch, not per-record]
               → write aggregate.json, finalize manifest.json
```

Metrics are computed in a batch over the whole run, not averaged per-record, because most of them (precision@k, latency percentiles, ECE) are only meaningful across many records — see `metrics/base.py`'s docstring.

A crash mid-run still leaves a `manifest.json` with `status: "failed"` and whatever records were already written — a partial, honest result, not silence.

## Metrics engine

Every metric is a pure function `(predictions, references, **kwargs) -> MetricResult` (`metrics/base.py`). Pure means: no network, no file I/O, independently unit-testable, freely reusable across suites (`latency_ms` is computed identically everywhere it appears).

**Library choices**, and why each one is optional rather than forced:
- **chrF / ROUGE-L** (`generation_metrics.py`): prefers `sacrebleu` / `rouge-score` if installed (publication-grade, matches what papers cite), falls back to a documented custom implementation otherwise, so the framework has zero hard dependencies for basic use. The fallback is explicitly labeled `"implementation": "custom_fallback"` in every result so nobody mistakes it for the canonical number.
- **RAGAS** (`ragas_adapter.py`): recommended for `legal_qa`'s faithfulness/answer-relevancy — it's the closest thing RAG evaluation has to a standard. Not forced: it requires an LLM-as-judge call (cost + a second source of nondeterminism) and pulls in langchain on top of an already fragile venv (see the Phase 1 architectural audit). The adapter never silently returns a fake score if ragas isn't installed — it raises a clear, actionable error only when actually called.
- **DeepEval** was considered and not adopted: its metric set overlaps RAGAS's for this use case, and standardizing on one LLM-judge framework rather than two keeps the dependency surface and the "which judge scored this" question simpler for a paper to describe.
- Retrieval, classification, calibration, latency, and robustness metrics are custom (`retrieval_metrics.py`, `classification_metrics.py`, `calibration_metrics.py`, `latency_metrics.py`, `robustness_metrics.py`) — these are standard, well-defined formulas (precision@k, ECE, percentiles) with no meaningful "canonical library" gap to fill, so a dependency would add risk without adding rigor.

## Result storage format

`results/runs/<suite>/<run_id>/`: `manifest.json` (reproducibility anchor: config hash, git commit + dirty flag, package versions, timestamps, status), `records.jsonl` (one `RecordResult` per input, streamed as the run happens), `aggregate.json` (the final `MetricResult`s). `run_id` is timestamp-prefixed, so directory listing order is chronological and `"latest"` resolution (used everywhere — `confidence.py`'s cross-suite reads, `report --run latest`, `compare`) is just "last in sorted order."

## Graph generation pipeline

`reporting/plots.py`, matplotlib with the headless `Agg` backend: metric bar charts, latency histograms, calibration reliability diagrams, categorical distribution charts (tier/engine mix), a radar chart for a cross-capability summary, and grouped bar charts for run-over-run comparison. Every function takes plain data and a `Path`, returns that `Path` — composable from `report_builder.py`, from `compare.py`, or ad hoc from a notebook while drafting a paper figure.

## Report generation pipeline

`reporting/report_builder.py::build_report()` takes one or more `SuiteResult`s, auto-generates the figures that apply to each (distribution charts where a `*_distribution` metric exists, a calibration curve where reliability bins exist, a latency histogram if latency data exists, a headline bar chart of scalar metrics), and renders `reporting/templates/report.md.j2` into `report.md` + `figures/`. `reporting/compare.py` does the same for a before/after ablation across multiple runs of one suite — purpose-built for validating the RAGMapping initialization fix from the Phase 3 handoff once real data exists.

## Running it

```bash
pip install -r evaluation/requirements-eval.txt

python -m evaluation.cli list-suites
python -m evaluation.cli run --suite infra_health          # no dataset needed — good first check
python -m evaluation.cli run --suite translation --limit 5  # once translation.jsonl is populated
python -m evaluation.cli report --suite translation
python -m evaluation.cli report --all-latest
python -m evaluation.cli compare --suite ipc_bns_mapping --runs before=<run_id> after=latest
```

`NYAYASETU_EVAL_BASE_URL` / `NYAYASETU_EVAL_AUTH_TOKEN` / `COLAB_BASE_URL` env vars override the defaults in `config/defaults.yaml` without editing committed files.

## What this phase deliberately did not do

No dataset was populated, no suite was run against real data, and no result exists anywhere under `results/runs/`. The only executions during this phase were infrastructure self-tests using clearly-synthetic toy numbers (see `evaluation/SELF_TEST.md`), never NyayaSetu's actual outputs. Populating `datasets/raw/` with reviewed, labeled records — and then running the suites — is the next, separate phase.
