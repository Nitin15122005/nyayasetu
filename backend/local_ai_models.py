# -*- coding: utf-8 -*-
"""
local_ai_models.py — In-process local AI inference for NyayaSetu
NyayaSetu | Team IKS | SPIT CSE 2025-26

Runs MiniLM embeddings, BART summarization, and NLLB translation directly
on this machine's GPU/CPU instead of round-tripping to the Colab notebook
over ngrok. This is the ONLY module in the backend that touches torch /
transformers / sentence-transformers model objects directly — local_models.py
is a thin, drop-in-compatible façade over these functions so every other
caller (document_analyzer.py, legal_translator.py, lex_validator.py,
modules/m2_rag/ingest.py) is unchanged.

Design:
  - Each model is a lazily-loaded, process-wide singleton (double-checked
    locking) — loaded on first use, never reloaded per request.
  - A second, per-model lock serializes the actual forward pass. This isn't
    needed for correctness of a single call, but concurrent calls into the
    same CUDA context from multiple threads (document_analyzer.py's
    ThreadPoolExecutor(max_workers=12) does exactly this) are not something
    PyTorch inference guarantees is safe, so calls are serialized rather
    than risking a subtle race for a modest amount of GPU idle time.
  - Model identifiers match exactly what the notebook used to build the
    existing ChromaDB / serve production so far — see colab_config.py and
    NyayaSetu_Final_Corrected.ipynb, Cells 6/16/18/20.
"""

import os
import re
import threading
import logging
from typing import List

import torch

from gpu_utils import DEVICE

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════════════
# Model identifiers — must match the models that built the existing ChromaDB
# collection and the notebook's own model choices (Cells 6, 16, 18, 20).
# ══════════════════════════════════════════════════════════════════════════════

MINILM_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
BART_MODEL_NAME    = "facebook/bart-large-cnn"
NLLB_MODEL_NAME    = "facebook/nllb-200-distilled-600M"

EMBED_DIM = 384  # verified against the live ChromaDB collection (nyayasetu_legal, 3254 vectors, dim=384)

# NLLB FLORES-200 codes for every language the product claims to support.
# This is the single source of truth for NLLB language support now — there
# is no second, out-of-sync copy of this map living inside a notebook cell
# anymore (that mismatch — the notebook's translate_text() only recognised
# 3 of these 13 codes — is exactly what made hosted NLLB silently wrong for
# 10 of them; going local removes the second copy instead of fixing it).
NLLB_LANG_MAP = {
    "hi": "hin_Deva",   # Hindi
    "mr": "mar_Deva",   # Marathi
    "ta": "tam_Taml",   # Tamil
    "te": "tel_Telu",   # Telugu
    "kn": "kan_Knda",   # Kannada
    "bn": "ben_Beng",   # Bengali
    "gu": "guj_Gujr",   # Gujarati
    "ml": "mal_Mlym",   # Malayalam
    "pa": "pan_Guru",   # Punjabi (Gurmukhi)
    "or": "ory_Orya",   # Odia
    "as": "asm_Beng",   # Assamese
    "ur": "urd_Arab",   # Urdu
    "en": "eng_Latn",   # English
}


# ══════════════════════════════════════════════════════════════════════════════
# MiniLM — sentence embeddings
# ══════════════════════════════════════════════════════════════════════════════

_minilm_model = None
_minilm_load_lock = threading.Lock()
_minilm_infer_lock = threading.Lock()


def _get_minilm():
    global _minilm_model
    if _minilm_model is None:
        with _minilm_load_lock:
            if _minilm_model is None:
                from sentence_transformers import SentenceTransformer
                logger.info("[LOCAL_AI] Loading MiniLM (%s) on %s ...", MINILM_MODEL_NAME, DEVICE)
                model = SentenceTransformer(MINILM_MODEL_NAME, device=str(DEVICE))
                dim = model.get_sentence_embedding_dimension()
                if dim != EMBED_DIM:
                    raise RuntimeError(
                        f"[LOCAL_AI] MiniLM loaded with dim={dim}, expected {EMBED_DIM}. "
                        "This would silently corrupt the existing ChromaDB collection — refusing to proceed."
                    )
                logger.info("[LOCAL_AI] MiniLM ready. dim=%d device=%s", dim, DEVICE)
                _minilm_model = model
    return _minilm_model


def embed_texts(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """
    Encode texts locally. Same output contract as the old Colab /embed
    response's "embeddings" field: list of 384-dim float lists, L2-normalized.
    """
    if not texts:
        return []
    model = _get_minilm()
    with _minilm_infer_lock:
        with torch.no_grad():
            vecs = model.encode(
                texts,
                batch_size=batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
    return vecs.tolist()


def embedding_dim() -> int:
    return EMBED_DIM


# ══════════════════════════════════════════════════════════════════════════════
# BART — English summarization
# ══════════════════════════════════════════════════════════════════════════════

_bart_tokenizer = None
_bart_model = None
_bart_load_lock = threading.Lock()
_bart_infer_lock = threading.Lock()


def _get_bart():
    global _bart_tokenizer, _bart_model
    if _bart_model is None:
        with _bart_load_lock:
            if _bart_model is None:
                from transformers import BartTokenizer, BartForConditionalGeneration
                logger.info("[LOCAL_AI] Loading BART (%s) on %s ...", BART_MODEL_NAME, DEVICE)
                tok = BartTokenizer.from_pretrained(BART_MODEL_NAME)
                model = BartForConditionalGeneration.from_pretrained(BART_MODEL_NAME).to(DEVICE).eval()
                logger.info("[LOCAL_AI] BART ready.")
                _bart_tokenizer, _bart_model = tok, model
    return _bart_tokenizer, _bart_model


def summarize_text(
    text: str,
    max_length: int = 200,
    min_length: int = 56,
    num_beams: int = 4,
) -> str:
    """
    Summarize English text locally via BART. Same generation parameters as
    the notebook's summarize_text() (Cell 18) / local_models.py's old
    /summarize request contract (min_length=56, max_length=200 by default).
    """
    tokenizer, model = _get_bart()
    with _bart_infer_lock:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=1024).to(DEVICE)
        with torch.no_grad():
            ids = model.generate(
                **inputs,
                max_length=max_length,
                min_length=min_length,
                num_beams=num_beams,
                length_penalty=2.0,
                early_stopping=True,
            )
        summary = tokenizer.decode(ids[0], skip_special_tokens=True)
    return summary.strip()


# ══════════════════════════════════════════════════════════════════════════════
# NLLB — translation
# ══════════════════════════════════════════════════════════════════════════════

_nllb_tokenizer = None
_nllb_model = None
_nllb_load_lock = threading.Lock()
_nllb_infer_lock = threading.Lock()

_NLLB_MAX_INPUT_TOKENS = 512    # NLLB-200-distilled-600M's trained context window
_NLLB_CHUNK_CHARS       = 800   # conservative char budget per chunk (well under 512 tokens for Indian-language text)


def _get_nllb():
    global _nllb_tokenizer, _nllb_model
    if _nllb_model is None:
        with _nllb_load_lock:
            if _nllb_model is None:
                from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
                logger.info("[LOCAL_AI] Loading NLLB (%s) on %s ...", NLLB_MODEL_NAME, DEVICE)
                tok = AutoTokenizer.from_pretrained(NLLB_MODEL_NAME)
                model = AutoModelForSeq2SeqLM.from_pretrained(NLLB_MODEL_NAME).to(DEVICE).eval()
                # VERIFIED against the installed transformers version (4.44.2): NllbTokenizerFast
                # has NO `lang_code_to_id` attribute (neither class- nor instance-level) — the
                # notebook's own translate_text() (Cell 16) uses
                # `nllb_tokenizer.lang_code_to_id[tgt]`, which would raise AttributeError if run
                # against this transformers version. The correct, verified-working call is
                # `tokenizer.convert_tokens_to_ids(lang_code)` (confirmed to resolve real token
                # ids, e.g. "eng_Latn" -> 256047, not the unk-token id).
                if hasattr(tok, "lang_code_to_id"):
                    logger.info("[LOCAL_AI] NLLB tokenizer exposes lang_code_to_id (older API) — fine, unused.")
                logger.info("[LOCAL_AI] NLLB ready.")
                _nllb_tokenizer, _nllb_model = tok, model
    return _nllb_tokenizer, _nllb_model


def _split_into_chunks(text: str, max_chars: int) -> List[str]:
    """Sentence/line-aware chunking so no single NLLB call exceeds its 512-token window."""
    lines = text.split("\n")
    chunks, current = [], ""
    for line in lines:
        candidate = (current + "\n" + line).strip() if current else line
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(line) > max_chars:
            sentences = re.split(r"(?<=[।.!?])\s+", line)
            current = ""
            for sent in sentences:
                trial = (current + " " + sent).strip() if current else sent
                if len(trial) <= max_chars:
                    current = trial
                else:
                    if current:
                        chunks.append(current)
                    current = sent[:max_chars]
        else:
            current = line
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


def _translate_chunk(text: str, src_code: str, tgt_code: str) -> str:
    tokenizer, model = _get_nllb()
    with _nllb_infer_lock:
        tokenizer.src_lang = src_code
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=_NLLB_MAX_INPUT_TOKENS).to(DEVICE)
        forced_bos_token_id = tokenizer.convert_tokens_to_ids(tgt_code)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                forced_bos_token_id=forced_bos_token_id,
                max_length=_NLLB_MAX_INPUT_TOKENS,
            )
        return tokenizer.batch_decode(out, skip_special_tokens=True)[0]


def translate_text(text: str, src_lang: str, tgt_lang: str) -> str:
    """
    Translate `text` (any length) from src_lang to tgt_lang using local NLLB.
    src_lang / tgt_lang are the same 2-letter ISO codes used throughout the
    backend (see NLLB_LANG_MAP). Long text is chunked so no single NLLB call
    exceeds the model's 512-token window; chunks are translated and rejoined.

    Raises ValueError if either language code is not in NLLB_LANG_MAP —
    callers must NOT silently claim support for a language this map doesn't
    cover (this was the notebook's bug: it accepted any src_lang string and
    silently defaulted unrecognized codes to Hindi instead of failing).
    """
    if src_lang not in NLLB_LANG_MAP:
        raise ValueError(f"[LOCAL_AI] NLLB has no mapping for src_lang='{src_lang}'.")
    if tgt_lang not in NLLB_LANG_MAP:
        raise ValueError(f"[LOCAL_AI] NLLB has no mapping for tgt_lang='{tgt_lang}'.")

    src_code = NLLB_LANG_MAP[src_lang]
    tgt_code = NLLB_LANG_MAP[tgt_lang]

    if not text or not text.strip():
        return ""

    if len(text) <= _NLLB_CHUNK_CHARS:
        return _translate_chunk(text, src_code, tgt_code).strip()

    chunks = _split_into_chunks(text, _NLLB_CHUNK_CHARS)
    logger.info("[LOCAL_AI] NLLB translating %d chars in %d chunks (%s -> %s)", len(text), len(chunks), src_code, tgt_code)
    parts = [_translate_chunk(c, src_code, tgt_code) for c in chunks]
    return "\n\n".join(p.strip() for p in parts if p.strip())


# ══════════════════════════════════════════════════════════════════════════════
# Status / diagnostics
# ══════════════════════════════════════════════════════════════════════════════

def loaded_models() -> dict:
    """Which local models are currently resident in memory (for diagnostics/health checks)."""
    return {
        "minilm_loaded": _minilm_model is not None,
        "bart_loaded":   _bart_model is not None,
        "nllb_loaded":   _nllb_model is not None,
        "device":        str(DEVICE),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CLI smoke test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("LOCAL AI MODELS — smoke test")
    print(f"Device: {DEVICE}")
    print("=" * 60)

    print("\n[TEST] Embeddings")
    vecs = embed_texts(["FIR filed at Andheri police station", "जमानत अर्जी"])
    print(f"  {len(vecs)} vectors, dim={len(vecs[0])}")

    print("\n[TEST] BART summarization")
    sample_en = (
        "This rental agreement is entered into between the Landlord, Mr. Ramesh Sharma, "
        "and the Tenant, Ms. Priya Verma, for the property at Flat 402, Mumbai. "
        "Monthly rent is Rs. 15,000 payable by the 5th. Security deposit Rs. 45,000."
    )
    print(f"  Summary: {summarize_text(sample_en)}")

    print("\n[TEST] NLLB translation (Hindi -> English)")
    sample_hi = "आरोपी ने दिनांक 15/03/2025 को शिकायतकर्ता का मोबाईल चुराया।"
    print(f"  Output: {translate_text(sample_hi, 'hi', 'en')}")

    print("\nAll local AI model functions working correctly.")
