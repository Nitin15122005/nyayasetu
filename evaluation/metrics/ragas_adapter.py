# -*- coding: utf-8 -*-
"""
evaluation/metrics/ragas_adapter.py — optional RAGAS integration

RAGAS (https://github.com/explodinggraphs/ragas) is the closest thing the
RAG-evaluation field has to a standard for faithfulness / answer-relevancy
/ context-precision / context-recall — worth using where it fits (mainly
legal_qa.yaml, which is a textbook RAG-QA setup: question + retrieved
context + generated answer). It is NOT forced as a hard dependency:
- it pulls in langchain and an LLM-as-judge call (Groq/Gemini/OpenAI),
  which costs money and adds a second point of nondeterminism on top of
  the system under test;
- this repo's venv is already known to have a fragile dependency chain
  (see the Phase 1 architectural audit), and ragas is a heavy addition.

So: this module is import-safe (never raises at import time), and each
function raises a clear, actionable RuntimeError only when actually
CALLED without ragas installed — never silently returns a fake score.
Evaluators check `ragas_available()` first and fall back to the custom
metrics in generation_metrics.py / calibration_metrics.py when it's False
(see legal_qa.yaml's `use_ragas_if_available` flag).

Install with:  pip install -r evaluation/requirements-eval.txt[ragas]
  (or just:    pip install ragas)
"""

from __future__ import annotations

from typing import Optional


def ragas_available() -> bool:
    try:
        import ragas  # noqa: F401
        return True
    except ImportError:
        return False


def _require_ragas():
    if not ragas_available():
        raise RuntimeError(
            "ragas is not installed. Install it with `pip install ragas` to use "
            "RAGAS-based metrics, or set use_ragas_if_available: false in the "
            "suite's YAML to use the custom fallback metrics instead."
        )


def evaluate_qa_sample(question: str, answer: str, contexts: list[str],
                        ground_truth: Optional[str] = None, llm=None) -> dict:
    """
    Runs RAGAS's faithfulness + answer_relevancy (+ context_precision /
    context_recall if `ground_truth` is given) on one QA sample.

    `llm` should be a RAGAS-compatible LLM wrapper for the judge model —
    deliberately not defaulted to a hardcoded provider here, since which
    model judges faithfulness is itself a methodology choice a paper
    needs to state explicitly, not one this framework should make silently.
    """
    _require_ragas()
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall

    metrics = [faithfulness, answer_relevancy]
    row = {"question": [question], "answer": [answer], "contexts": [contexts]}
    if ground_truth:
        row["ground_truth"] = [ground_truth]
        metrics += [context_precision, context_recall]

    ds = Dataset.from_dict(row)
    result = evaluate(ds, metrics=metrics, llm=llm) if llm else evaluate(ds, metrics=metrics)
    return dict(result)
