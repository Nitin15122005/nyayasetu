# -*- coding: utf-8 -*-
"""
evaluation/metrics/generation_metrics.py — text-generation quality metrics

Used by: translation (chrF against reference translations), summarization
(ROUGE-L against reference summaries), legal_qa / research (semantic
similarity between an answer and a reference, using the SAME embedding
model NyayaSetu itself uses — see harness/direct_adapter.embed_query_via_colab
— so "does the answer mean the same thing" is measured in the system's
own embedding space, not a foreign one).

Prefers real, citable libraries (sacrebleu for chrF, rouge-score for
ROUGE-L) when installed — see evaluation/requirements-eval.txt — and
falls back to a documented custom implementation otherwise, so this
package has zero hard dependencies beyond the stdlib + numpy.
"""

from __future__ import annotations

import math
from collections import Counter

from evaluation.metrics.base import MetricResult


# ── chrF ─────────────────────────────────────────────────────────────────────

def _char_ngrams(text: str, n: int) -> Counter:
    text = text.replace(" ", "")
    if len(text) < n:
        return Counter([text]) if text else Counter()
    return Counter(text[i:i + n] for i in range(len(text) - n + 1))


def _chrf_single_custom(pred: str, ref: str, n: int, beta: float) -> float:
    if not pred.strip() and not ref.strip():
        return 1.0
    if not pred.strip() or not ref.strip():
        return 0.0
    p_grams, r_grams = _char_ngrams(pred, n), _char_ngrams(ref, n)
    overlap = sum((p_grams & r_grams).values())
    precision = overlap / max(sum(p_grams.values()), 1)
    recall = overlap / max(sum(r_grams.values()), 1)
    if precision + recall == 0:
        return 0.0
    beta2 = beta ** 2
    return (1 + beta2) * precision * recall / (beta2 * precision + recall)


def chrf(predictions: list[str], references: list[str], n: int = 6, beta: float = 2.0, **_) -> MetricResult:
    """
    chrF (character n-gram F-score), the standard metric for translation
    quality when word-level tokenization is unreliable across scripts —
    exactly the situation here (Marathi/Hindi/Tamil/... -> English).

    Uses `sacrebleu.CHRF` if installed (publication-grade, matches papers
    exactly); otherwise a documented custom character n-gram F-beta score
    that agrees with the standard definition but has not been validated
    against sacrebleu's reference implementation — treat scores from the
    fallback as directionally, not numerically, comparable to published
    chrF numbers.
    """
    try:
        import sacrebleu
        scorer = sacrebleu.CHRF(char_order=n, beta=int(beta))
        per_item = [scorer.sentence_score(p, [r]).score / 100.0 for p, r in zip(predictions, references)]
        source = "sacrebleu"
    except ImportError:
        per_item = [_chrf_single_custom(p, r, n, beta) for p, r in zip(predictions, references)]
        source = "custom_fallback"

    value = sum(per_item) / len(per_item) if per_item else None
    return MetricResult(name="chrf", value=value, n=len(per_item),
                         details={"per_item": per_item, "implementation": source})


# ── ROUGE-L ──────────────────────────────────────────────────────────────────

def _lcs_length(a: list[str], b: list[str]) -> int:
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            dp[i][j] = dp[i - 1][j - 1] + 1 if a[i - 1] == b[j - 1] else max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def _rouge_l_single_custom(pred: str, ref: str) -> float:
    p_toks, r_toks = pred.split(), ref.split()
    if not p_toks or not r_toks:
        return 0.0
    lcs = _lcs_length(p_toks, r_toks)
    precision = lcs / len(p_toks)
    recall = lcs / len(r_toks)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def rouge_l(predictions: list[str], references: list[str], **_) -> MetricResult:
    """
    Uses `rouge_score.RougeScorer` if installed; otherwise a custom
    LCS-based ROUGE-L F1 (the standard definition — token-level longest
    common subsequence), same caveat as chrf() re: numerical comparability
    to the reference implementation.
    """
    try:
        from rouge_score import rouge_scorer
        scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
        per_item = [scorer.score(r, p)["rougeL"].fmeasure for p, r in zip(predictions, references)]
        source = "rouge_score"
    except ImportError:
        per_item = [_rouge_l_single_custom(p, r) for p, r in zip(predictions, references)]
        source = "custom_fallback"

    value = sum(per_item) / len(per_item) if per_item else None
    return MetricResult(name="rouge_l", value=value, n=len(per_item),
                         details={"per_item": per_item, "implementation": source})


# ── Semantic similarity (embedding cosine) ──────────────────────────────────

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_similarity(predictions: list[list[float]], references: list[list[float]], **_) -> MetricResult:
    """
    Cosine similarity between pre-computed embedding vectors (compute
    them via NotebookClient.embed() or harness.direct_adapter before
    calling this — this function does no embedding itself, keeping it a
    pure function like every other metric here).
    """
    if not predictions:
        return MetricResult(name="semantic_similarity", value=None, n=0)
    per_item = [_cosine(p, r) for p, r in zip(predictions, references)]
    return MetricResult(name="semantic_similarity", value=sum(per_item) / len(per_item),
                         n=len(per_item), details={"per_item": per_item})
