# -*- coding: utf-8 -*-
"""
ai_clients.py — Shared LLM client construction for Nyaya-Setu
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

Single place where the Groq and Gemini SDK clients are constructed.
Previously document_analyzer.py, legal_translator.py, and lex_validator.py
each built their own Groq client from the same GROQ_API_KEY/GROQ_MODEL env
vars, and api.py built a third, separate Gemini client alongside
legal_translator.py's — all with identical construction arguments. This
module is the one place that now does it.

Construction semantics are unchanged from before this module existed:
  - The Groq client is built eagerly and strictly, exactly as it was in
    each of the three files — missing GROQ_API_KEY still fails at import
    time, just from whichever module imports this one first.
  - The Gemini client is built lazily via get_gemini_client(), returning
    None when GEMINI_API_KEY is unset, matching legal_translator.py's
    original guarded pattern (api.py's copilot endpoint already checked
    for the key before constructing its own client, so it degrades the
    same way it always did — see api.py's /api/editor/copilot).
"""

import os
import threading
import logging
from groq import Groq
from google import genai
from dotenv import load_dotenv

load_dotenv()

# Central logging setup for the AI pipeline — this module is imported before
# any of the LLM-calling modules (document_analyzer, legal_translator,
# lex_validator, local_models), so this is where the format is set once.
# basicConfig() is a no-op if a handler already exists, so it's safe for
# other modules (e.g. local_models.py, when run standalone) to also call it.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# GROQ_SDK_MAX_RETRIES: the groq-python SDK already retries 408/409/429/5xx
# internally with exponential backoff + jitter, and honors a `Retry-After`
# response header when the API sends one (see groq._base_client
# ._calculate_retry_timeout). That is a complete, correct implementation of
# requirement G ("respect 429 Retry-After/backoff, cap retries") — the old
# code in document_analyzer.py additionally hand-rolled its OWN fixed-delay
# retry loop (3s/6s/9s/12s, no jitter) on top of this, so a single rate-limit
# hit under concurrency could trigger the SDK's own retries *and* the outer
# loop's retries stacking together. That double-retrying, multiplied across
# every concurrently-firing task, is what turned isolated 429s into a retry
# storm. Fixing this means deleting the duplicate loop, not adding a second
# one here — this client is the ONLY place `max_retries` is configured now.
GROQ_SDK_MAX_RETRIES = int(os.getenv("GROQ_SDK_MAX_RETRIES", "4"))
groq_client = Groq(api_key=GROQ_API_KEY, max_retries=GROQ_SDK_MAX_RETRIES)

# GROQ_MAX_CONCURRENCY: hard cap on simultaneous in-flight Groq requests from
# this process. document_analyzer.analyze_document() fires many analysis
# tasks into a 12-worker ThreadPoolExecutor at once; without this cap, all of
# them could call the Groq API in the same instant, which is what actually
# causes 429s (and, under contention, Groq's own 409 ConflictError) in the
# first place — no amount of retrying fixes a rate limit that concurrency
# keeps re-triggering. Every Groq call in the backend should route through
# groq_chat() below so this cap applies everywhere, not just in one module.
GROQ_MAX_CONCURRENCY = int(os.getenv("GROQ_MAX_CONCURRENCY", "3"))
_groq_semaphore = threading.Semaphore(GROQ_MAX_CONCURRENCY)

# MAX_PROMPT_TOKENS: safety ceiling for a single prompt, kept comfortably
# under the smallest observed model TPM budget (8,000 tokens/min for
# qwen/qwen3.6-27b). This is a backstop, not the primary fix — callers
# should already be sending small, targeted prompts (see lex_validator's
# RAG mapping, which now sends a section id + a small local text window
# instead of the whole document). If a prompt still exceeds this, it is
# truncated rather than sent whole, so no single call can blow the TPM
# budget by itself and trigger a 413.
MAX_PROMPT_TOKENS = int(os.getenv("GROQ_MAX_PROMPT_TOKENS", "6000"))
_CHARS_PER_TOKEN_ESTIMATE = 4  # rough heuristic for English/legal text, not a real tokenizer


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars/token). A safety heuristic, not a tokenizer."""
    return max(1, len(text) // _CHARS_PER_TOKEN_ESTIMATE)


def _budget_prompt(prompt: str) -> str:
    est = estimate_tokens(prompt)
    if est <= MAX_PROMPT_TOKENS:
        return prompt
    max_chars = MAX_PROMPT_TOKENS * _CHARS_PER_TOKEN_ESTIMATE
    logger.warning(
        "[GROQ] Prompt ~%d tokens exceeds the %d-token safety budget — truncating to ~%d chars.",
        est, MAX_PROMPT_TOKENS, max_chars,
    )
    return prompt[:max_chars]


def groq_chat(model: str, prompt: str, temperature: float = 0.1, max_tokens: int = 1024) -> str:
    """
    Shared entry point for every Groq chat-completion call in the backend.
    Bounds concurrency (GROQ_MAX_CONCURRENCY) and caps prompt size
    (MAX_PROMPT_TOKENS) before handing off to the SDK, which already retries
    408/409/429/5xx with Retry-After-aware backoff (GROQ_SDK_MAX_RETRIES).
    """
    prompt = _budget_prompt(prompt)
    with _groq_semaphore:
        resp = groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
    return resp.choices[0].message.content.strip()


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"


def get_gemini_client():
    """Returns a Gemini client, or None if GEMINI_API_KEY is not set."""
    return genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
