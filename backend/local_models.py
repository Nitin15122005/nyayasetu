# -*- coding: utf-8 -*-
"""
local_models.py — HTTP client wrapper for Colab inference server
NyayaSetu | Team IKS | SPIT CSE 2025-26

ALL heavy model inference (NLLB, BART, MuRIL embeddings) now runs on the
Colab GPU.  This file keeps the EXACT same public function signatures as the
old local-model version, so every other file (legal_translator.py,
document_analyzer.py, etc.) continues to work without any import changes.

Architecture:
  Colab GPU (NLLB + BART + SentenceTransformer)
      ↑ HTTP (ngrok public URL)
  This file (thin HTTP client)
      ↑ Python imports
  legal_translator.py / document_analyzer.py
"""

import re
import time as _time
import logging
import requests as _req
from colab_config import endpoint, COLAB_TIMEOUT

# basicConfig is a no-op if a handler is already installed (e.g. by
# ai_clients.py, imported earlier in the app's import chain), so this is
# safe to call here too — it just guarantees this module's own log calls
# are visible even when it's run standalone (`python local_models.py`).
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── NLLB language map (still exported — legal_translator.py imports it) ───────
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


# ── Internal HTTP helper ───────────────────────────────────────────────────────
def _post(path: str, payload: dict, timeout: int = COLAB_TIMEOUT) -> dict:
    """
    POST JSON to the Colab inference server.
    Raises RuntimeError with a clear message on any failure so callers
    can fall back gracefully (Gemini / Groq) just like the old local model.
    """
    url = endpoint(path)
    try:
        resp = _req.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except _req.exceptions.ConnectionError:
        raise RuntimeError(
            f"[COLAB] Cannot reach inference server at {url}. "
            "Is Colab running and is COLAB_BASE_URL in colab_config.py up to date?"
        )
    except _req.exceptions.Timeout:
        raise RuntimeError(
            f"[COLAB] Request to {url} timed out after {timeout}s. "
            "The GPU may be cold-starting — try again in a few seconds."
        )
    except _req.exceptions.HTTPError as e:
        raise RuntimeError(f"[COLAB] HTTP error from {url}: {e}")
    except Exception as e:
        raise RuntimeError(f"[COLAB] Unexpected error calling {url}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# NLLB Translation  (matches old local_models.py public API)
# ══════════════════════════════════════════════════════════════════════════════

def translate_with_nllb(
    text: str,
    src_lang: str = "auto",
    tgt_lang: str = "en",
    max_new_tokens: int = 512,   # kept for signature compatibility — server ignores
) -> str:
    """
    Translate text using the Colab-hosted NLLB model.
    Same signature as the old local version — drop-in replacement.

    Raises:
        ValueError  — unknown language code (same as old version)
        RuntimeError — Colab unreachable → caller should fall back to Gemini/Groq
    """
    if src_lang == "auto" or src_lang not in NLLB_LANG_MAP:
        raise ValueError(
            f"[NLLB] Unknown src_lang '{src_lang}'. "
            "Resolve language before calling translate_with_nllb()."
        )
    if tgt_lang not in NLLB_LANG_MAP:
        raise ValueError(f"[NLLB] Unknown tgt_lang '{tgt_lang}'.")

    logger.info("[LOCAL_MODELS] → Colab /translate  (%s → %s, %d chars)", src_lang, tgt_lang, len(text))
    data = _post("/translate", {
        "text":     text,
        "src_lang": src_lang,
        "tgt_lang": tgt_lang,
    })
    translated = data.get("translated_text", "").strip()
    if not translated:
        raise RuntimeError("[COLAB] NLLB returned empty translation.")
    return translated


def translate_chunks_nllb(
    text: str,
    src_lang: str = "hi",
    tgt_lang: str = "en",
    chunk_chars: int = 800,   # kept for signature compatibility — server handles chunking
) -> str:
    """
    Translate a large document using the Colab NLLB model.
    Chunking is handled server-side; this is now a single HTTP call.

    Returns empty string on failure (same semantics as old version)
    so legal_translator.py falls through to Gemini/Groq correctly.
    """
    if src_lang not in NLLB_LANG_MAP or tgt_lang not in NLLB_LANG_MAP:
        logger.warning("[LOCAL_MODELS] translate_chunks_nllb: unsupported lang pair %s→%s", src_lang, tgt_lang)
        return ""

    logger.info("[LOCAL_MODELS] → Colab /translate  (%s → %s, %d chars, chunked server-side)", src_lang, tgt_lang, len(text))
    try:
        data = _post("/translate", {
            "text":     text,
            "src_lang": src_lang,
            "tgt_lang": tgt_lang,
        })
        translated = data.get("translated_text", "").strip()
        if not translated:
            logger.warning("[LOCAL_MODELS] Colab /translate returned empty — signalling fallback.")
            return ""
        logger.info("[LOCAL_MODELS] Colab NLLB OK — %d chars", len(translated))
        return translated
    except RuntimeError as e:
        logger.warning("[LOCAL_MODELS] Colab NLLB failed: %s. Signalling fallback.", e)
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# BART Summarization  (matches old public API)
# ══════════════════════════════════════════════════════════════════════════════

def summarize_with_bart(
    text: str,
    max_input_chars: int = 3000,
    min_length: int = 56,
    max_length: int = 200,
    num_beams: int = 4,           # kept for signature compatibility
) -> str:
    """
    Summarize English legal text via the Colab-hosted BART model.
    Same signature as old local version — drop-in replacement.

    Raises RuntimeError on Colab failure → caller falls back to Groq.
    """
    logger.info("[LOCAL_MODELS] → Colab /summarize  (%d chars)", min(len(text), max_input_chars))
    data = _post("/summarize", {
        "text":       text[:max_input_chars],
        "min_length": min_length,
        "max_length": max_length,
    })
    summary = data.get("summary", "").strip()
    if not summary:
        raise RuntimeError("[COLAB] BART returned empty summary.")
    logger.info("[LOCAL_MODELS] Colab BART OK — %d chars", len(summary))
    return summary


# ══════════════════════════════════════════════════════════════════════════════
# MuRIL Embeddings  (matches old public API)
# ══════════════════════════════════════════════════════════════════════════════

def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """
    Encode texts using the Colab-hosted SentenceTransformer model.
    Same signature as old local version — drop-in replacement.

    Returns list of float vectors.
    Raises RuntimeError on Colab failure.
    """
    if not texts:
        return []
    logger.info("[LOCAL_MODELS] → Colab /embed  (%d texts)", len(texts))
    data = _post("/embed", {"texts": texts})
    embeddings = data.get("embeddings")
    if not embeddings:
        raise RuntimeError("[COLAB] Embed endpoint returned no vectors.")
    # The notebook's /embed response has no top-level "dim" key — derive it
    # from the vectors themselves instead of assuming one (was always
    # printing "None" here before).
    logger.info("[LOCAL_MODELS] Colab embed OK — %d × %d vectors", len(embeddings), len(embeddings[0]))
    return embeddings


# ══════════════════════════════════════════════════════════════════════════════
# Document Classification  (NEW — not in old local_models.py)
# ══════════════════════════════════════════════════════════════════════════════

def classify_document(text: str) -> dict:
    """
    Classify a legal document using the Colab MuRIL classifier.

    Returns:
        {"label": "FIR", "confidence": 0.92, "all_probs": {...}}
    Raises RuntimeError on Colab failure.
    """
    logger.info("[LOCAL_MODELS] → Colab /classify  (%d chars)", len(text))
    data = _post("/classify", {"text": text[:512]})
    if "label" not in data:
        raise RuntimeError("[COLAB] Classify endpoint returned unexpected response.")
    return data


# ══════════════════════════════════════════════════════════════════════════════
# Hybrid Retrieval  (NEW — combines FAISS + BM25 on Colab)
# ══════════════════════════════════════════════════════════════════════════════

def retrieve_similar(query: str, top_k: int = 3, label_filter: str = None) -> list[dict]:
    """
    Hybrid FAISS + BM25 search on Colab, over the notebook's OWN document
    corpus (the classifier training samples — FIR / Bail Application /
    Court Notice / Legal Notice / Affidavit / Property Deed) — NOT the
    BNS/BNSS/BSA statute text used by ingest.py / lex_validator.RAGMapping.
    Not currently called by any live feature; kept as a ready-to-use,
    notebook-compatible capability.

    Args:
        query:        Search query (any language)
        top_k:        Number of results
        label_filter: Optional document type filter e.g. "FIR" — accepted
                       here but NOT implemented by the notebook's /retrieve
                       endpoint today, so it is currently a no-op server-side.

    Returns:
        List of dicts: {text, label, language, source_file, page, score}
        (matches the notebook's hybrid_retrieve() output exactly)
    """
    logger.info("[LOCAL_MODELS] → Colab /retrieve  (query=%r, top_k=%d)", query[:60], top_k)
    payload = {"query": query, "top_k": top_k}
    if label_filter:
        payload["label_filter"] = label_filter
    data = _post("/retrieve", payload)
    results = data.get("results", [])
    logger.info("[LOCAL_MODELS] Colab retrieve OK — %d results", len(results))
    return results


# ══════════════════════════════════════════════════════════════════════════════
# Colab health check
# ══════════════════════════════════════════════════════════════════════════════

def check_colab_health() -> dict:
    """
    Ping the Colab inference server. Returns the /health JSON or raises.
    Not currently called by any live api.py endpoint (no /api/colab/status
    route exists) — available for wiring in a future health-check endpoint.
    """
    try:
        resp = _req.get(endpoint("/health"), timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise RuntimeError(f"[COLAB] Health check failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Stubs retained for backwards-compat (old imports won't break)
# ══════════════════════════════════════════════════════════════════════════════

def get_nllb():
    """Deprecated — model now runs on Colab. Raises immediately."""
    raise RuntimeError("[LOCAL_MODELS] get_nllb() is deprecated. Model is on Colab.")

def get_bart():
    """Deprecated — model now runs on Colab. Raises immediately."""
    raise RuntimeError("[LOCAL_MODELS] get_bart() is deprecated. Model is on Colab.")

def get_embedding_model():
    """Deprecated — model now runs on Colab. Use embed_texts() instead."""
    raise RuntimeError("[LOCAL_MODELS] get_embedding_model() is deprecated. Use embed_texts().")


# ══════════════════════════════════════════════════════════════════════════════
# CLI smoke test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from colab_config import COLAB_BASE_URL
    print("\n" + "="*60)
    print(f"LOCAL MODEL CLIENT HEALTH CHECK")
    print(f"Colab URL: {COLAB_BASE_URL}")
    print("="*60)

    # 1. Health
    print("\n[TEST] Colab /health")
    h = check_colab_health()
    print(f"  Status : {h['status']} | Device: {h['device']}")
    print(f"  Corpus : {h.get('corpus_size', '?')} docs | FAISS vectors: {h.get('faiss_vectors', '?')}")

    # 2. Translation
    sample_hi = "आरोपी ने दिनांक 15/03/2025 को शिकायतकर्ता का मोबाईल चुराया।"
    print(f"\n[TEST] NLLB Translation")
    print(f"  Input (Hindi): {sample_hi}")
    translated = translate_with_nllb(sample_hi, src_lang="hi", tgt_lang="en")
    print(f"  Output: {translated}")

    # 3. Summarization
    sample_en = (
        "This rental agreement is entered into between the Landlord, Mr. Ramesh Sharma, "
        "and the Tenant, Ms. Priya Verma, for the property at Flat 402, Mumbai. "
        "Monthly rent is Rs. 15,000 payable by the 5th. Security deposit Rs. 45,000."
    )
    print(f"\n[TEST] BART Summarization")
    summary = summarize_with_bart(sample_en)
    print(f"  Summary: {summary}")

    # 4. Embeddings
    print(f"\n[TEST] Embeddings")
    texts = ["FIR filed at Andheri police station", "जमानत अर्जी"]
    vecs  = embed_texts(texts)
    print(f"  Embedded {len(vecs)} texts, dim={len(vecs[0])}")

    # 5. Classification
    print(f"\n[TEST] Classification")
    result = classify_document(sample_hi)
    print(f"  Label: {result['label']} ({result['confidence']*100:.1f}%)")

    # 6. Retrieval
    print(f"\n[TEST] Hybrid Retrieval")
    results = retrieve_similar("इस FIR में आरोपी का नाम क्या है?", top_k=2)
    for i, r in enumerate(results, start=1):
        print(f"  [{i}] {r['label']} ({r['score']:.3f}): {r['text'][:80]}...")

    print("\n✅ All Colab client functions working correctly.")
