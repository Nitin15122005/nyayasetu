# -*- coding: utf-8 -*-
"""
local_models.py — Local-first AI facade for NyayaSetu
NyayaSetu | Team IKS | SPIT CSE 2025-26

Production inference (embeddings, summarization, translation) now runs
IN-PROCESS via local_ai_models.py (local GPU/CPU) instead of over HTTP to
the Colab notebook. This file keeps the EXACT same public function
signatures the rest of the backend already imports, so
legal_translator.py, document_analyzer.py, lex_validator.py, and
modules/m2_rag/ingest.py needed NO changes.

Architecture (current):
  local_ai_models.py (MiniLM + BART + NLLB, loaded once, in-process)
      ↑ direct Python calls — no network hop, no ngrok
  This file (thin facade — same function names as before)
      ↑ Python imports
  legal_translator.py / document_analyzer.py / lex_validator.py

classify_document() / retrieve_similar() / check_colab_health() are kept
below as OPTIONAL legacy HTTP clients for the notebook's /classify,
/retrieve and /health endpoints. They are NOT on the production critical
path — nothing in api.py, document_analyzer.py, or lex_validator.py calls
them (verified: MuRIL classification and the notebook's own hybrid
retrieval were never wired into production; see colab_config.py for why
they're kept). Colab/ngrok is therefore no longer required to run the
production backend at all.
"""

import logging
import requests as _req

from colab_config import endpoint, COLAB_TIMEOUT
import local_ai_models as _local

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# Re-exported so `from local_models import NLLB_LANG_MAP` (legal_translator.py)
# keeps working unchanged. Single source of truth now lives in local_ai_models.py.
NLLB_LANG_MAP = _local.NLLB_LANG_MAP


# ══════════════════════════════════════════════════════════════════════════════
# NLLB Translation — now local (see local_ai_models.translate_text)
# ══════════════════════════════════════════════════════════════════════════════

def translate_with_nllb(
    text: str,
    src_lang: str = "auto",
    tgt_lang: str = "en",
    max_new_tokens: int = 512,   # kept for signature compatibility — local NLLB chunks internally instead
) -> str:
    """
    Translate text using the locally-loaded NLLB model.
    Same signature as before — drop-in replacement.

    Raises:
        ValueError  — unknown/unsupported language code
        RuntimeError — local NLLB inference failed → caller should fall back to Gemini/Groq
    """
    if src_lang == "auto" or src_lang not in NLLB_LANG_MAP:
        raise ValueError(
            f"[NLLB] Unknown src_lang '{src_lang}'. "
            "Resolve language before calling translate_with_nllb()."
        )
    if tgt_lang not in NLLB_LANG_MAP:
        raise ValueError(f"[NLLB] Unknown tgt_lang '{tgt_lang}'.")

    logger.info("[LOCAL_MODELS] Local NLLB translate (%s -> %s, %d chars)", src_lang, tgt_lang, len(text))
    try:
        translated = _local.translate_text(text, src_lang, tgt_lang).strip()
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(f"[LOCAL_AI] NLLB translation failed: {e}")

    if not translated:
        raise RuntimeError("[LOCAL_AI] NLLB returned empty translation.")
    return translated


def translate_chunks_nllb(
    text: str,
    src_lang: str = "hi",
    tgt_lang: str = "en",
    chunk_chars: int = 800,   # kept for signature compatibility — local_ai_models has its own internal chunk size
) -> str:
    """
    Translate a large document using the locally-loaded NLLB model.
    Chunking happens inside local_ai_models.translate_text().

    Returns empty string on failure or unsupported language (same semantics
    as before) so legal_translator.py falls through to Gemini/Groq correctly.
    Does NOT silently mistranslate unsupported languages as Hindi — that was
    the old notebook's bug (its NLLB_LANGS dict only recognized 3 of the 13
    language codes this backend declares support for; anything else quietly
    resolved to Hindi). Local inference uses one single language map
    (local_ai_models.NLLB_LANG_MAP) covering all 13, so "supported" now
    means what it says.
    """
    if src_lang not in NLLB_LANG_MAP or tgt_lang not in NLLB_LANG_MAP:
        logger.warning("[LOCAL_MODELS] translate_chunks_nllb: unsupported lang pair %s->%s", src_lang, tgt_lang)
        return ""

    logger.info("[LOCAL_MODELS] Local NLLB translate (%s -> %s, %d chars, chunked internally)", src_lang, tgt_lang, len(text))
    try:
        translated = _local.translate_text(text, src_lang, tgt_lang).strip()
        if not translated:
            logger.warning("[LOCAL_MODELS] Local NLLB returned empty — signalling fallback.")
            return ""
        logger.info("[LOCAL_MODELS] Local NLLB OK — %d chars", len(translated))
        return translated
    except Exception as e:
        logger.warning("[LOCAL_MODELS] Local NLLB failed: %s. Signalling fallback.", e)
        return ""


# ══════════════════════════════════════════════════════════════════════════════
# BART Summarization — now local (see local_ai_models.summarize_text)
# ══════════════════════════════════════════════════════════════════════════════

def summarize_with_bart(
    text: str,
    max_input_chars: int = 3000,
    min_length: int = 56,
    max_length: int = 200,
    num_beams: int = 4,
) -> str:
    """
    Summarize English legal text via the locally-loaded BART model.
    Same signature as before — drop-in replacement.

    Raises RuntimeError on local inference failure → caller falls back to Groq.
    """
    logger.info("[LOCAL_MODELS] Local BART summarize (%d chars)", min(len(text), max_input_chars))
    try:
        summary = _local.summarize_text(
            text[:max_input_chars],
            max_length=max_length,
            min_length=min_length,
            num_beams=num_beams,
        ).strip()
    except Exception as e:
        raise RuntimeError(f"[LOCAL_AI] BART summarization failed: {e}")

    if not summary:
        raise RuntimeError("[LOCAL_AI] BART returned empty summary.")
    logger.info("[LOCAL_MODELS] Local BART OK — %d chars", len(summary))
    return summary


# ══════════════════════════════════════════════════════════════════════════════
# MiniLM Embeddings — now local (see local_ai_models.embed_texts)
# ══════════════════════════════════════════════════════════════════════════════

def embed_texts(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """
    Encode texts using the locally-loaded SentenceTransformer model
    (paraphrase-multilingual-MiniLM-L12-v2, 384-dim — same model that built
    the existing ChromaDB collection; verified compatible before this
    module switched over).
    Same signature as before — drop-in replacement.

    Returns list of float vectors.
    Raises RuntimeError on local inference failure.
    """
    if not texts:
        return []
    logger.info("[LOCAL_MODELS] Local embed (%d texts)", len(texts))
    try:
        embeddings = _local.embed_texts(texts, batch_size=batch_size)
    except Exception as e:
        raise RuntimeError(f"[LOCAL_AI] Embedding failed: {e}")

    if not embeddings:
        raise RuntimeError("[LOCAL_AI] Embedding returned no vectors.")
    logger.info("[LOCAL_MODELS] Local embed OK — %d x %d vectors", len(embeddings), len(embeddings[0]))
    return embeddings


# ══════════════════════════════════════════════════════════════════════════════
# OPTIONAL legacy Colab HTTP clients — NOT on the production critical path
# ══════════════════════════════════════════════════════════════════════════════
# The three functions below still talk to the notebook over ngrok. They are
# kept only because they were never wired into any production feature in
# the first place (verified: zero callers in api.py / document_analyzer.py /
# lex_validator.py). They are useful if you want to manually exercise the
# notebook's MuRIL classifier or its own hybrid FAISS+BM25 retrieval for
# research, but the production backend does not need Colab running for any
# of /api/analyze, /api/qa, /api/compliance, /api/translate, or /api/*
# upload endpoints to function.

def classify_document(text: str) -> dict:
    """
    OPTIONAL / RESEARCH ONLY. Classify a legal document using the Colab
    MuRIL classifier over ngrok. Not called by any production route —
    document_analyzer.detect_document_type() uses a local keyword heuristic
    instead (MuRIL's fine-tuned label taxonomy — FIR / Bail_Application /
    Court_Notice / Affidavit / Legal_Notice — does not match the product's
    document-type taxonomy; see MuRIL integration notes below).

    Returns:
        {"label": "FIR", "confidence": 0.92, "all_probs": {...}}
    Raises RuntimeError if the notebook/ngrok isn't running.
    """
    logger.info("[LOCAL_MODELS] -> Colab /classify (research only, %d chars)", len(text))
    data = _post("/classify", {"text": text[:512]})
    if "label" not in data:
        raise RuntimeError("[COLAB] Classify endpoint returned unexpected response.")
    return data


def retrieve_similar(query: str, top_k: int = 3, label_filter: str = None) -> list[dict]:
    """
    OPTIONAL / RESEARCH ONLY. Hybrid FAISS + BM25 search on Colab, over the
    notebook's OWN document corpus (the classifier training samples — FIR /
    Bail Application / Court Notice / Legal Notice / Affidavit / Property
    Deed) — NOT the BNS/BNSS/BSA statute text used by ingest.py /
    lex_validator.RAGMapping. Not called by any production route.

    Args:
        query:        Search query (any language)
        top_k:        Number of results
        label_filter: Optional document type filter — accepted here but NOT
                       implemented by the notebook's /retrieve endpoint, so
                       it is a no-op server-side.

    Returns:
        List of dicts: {text, label, language, source_file, page, score}
    Raises RuntimeError if the notebook/ngrok isn't running.
    """
    logger.info("[LOCAL_MODELS] -> Colab /retrieve (research only, query=%r, top_k=%d)", query[:60], top_k)
    payload = {"query": query, "top_k": top_k}
    if label_filter:
        payload["label_filter"] = label_filter
    data = _post("/retrieve", payload)
    results = data.get("results", [])
    logger.info("[LOCAL_MODELS] Colab retrieve OK — %d results", len(results))
    return results


def check_colab_health() -> dict:
    """
    OPTIONAL / RESEARCH ONLY. Ping the Colab inference server, if you're
    running it for MuRIL/hybrid-retrieval research. Returns the /health
    JSON or raises. No production route depends on this.
    """
    try:
        resp = _req.get(endpoint("/health"), timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise RuntimeError(f"[COLAB] Health check failed: {e}")


def _post(path: str, payload: dict, timeout: int = COLAB_TIMEOUT) -> dict:
    """HTTP POST helper used only by the optional legacy Colab clients above."""
    url = endpoint(path)
    try:
        resp = _req.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except _req.exceptions.ConnectionError:
        raise RuntimeError(
            f"[COLAB] Cannot reach inference server at {url}. "
            "This only affects optional research features (classify_document/"
            "retrieve_similar) — production inference does not need Colab. "
            "Is the notebook running and is COLAB_BASE_URL in colab_config.py up to date?"
        )
    except _req.exceptions.Timeout:
        raise RuntimeError(f"[COLAB] Request to {url} timed out after {timeout}s.")
    except _req.exceptions.HTTPError as e:
        raise RuntimeError(f"[COLAB] HTTP error from {url}: {e}")
    except Exception as e:
        raise RuntimeError(f"[COLAB] Unexpected error calling {url}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# CLI smoke test
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LOCAL MODEL FACADE — SMOKE TEST")
    print(f"Local models loaded: {_local.loaded_models()}")
    print("=" * 60)

    sample_hi = "आरोपी ने दिनांक 15/03/2025 को शिकायतकर्ता का मोबाईल चुराया।"
    print("\n[TEST] NLLB Translation (local)")
    print(f"  Input (Hindi): {sample_hi}")
    translated = translate_with_nllb(sample_hi, src_lang="hi", tgt_lang="en")
    print(f"  Output: {translated}")

    sample_en = (
        "This rental agreement is entered into between the Landlord, Mr. Ramesh Sharma, "
        "and the Tenant, Ms. Priya Verma, for the property at Flat 402, Mumbai. "
        "Monthly rent is Rs. 15,000 payable by the 5th. Security deposit Rs. 45,000."
    )
    print("\n[TEST] BART Summarization (local)")
    summary = summarize_with_bart(sample_en)
    print(f"  Summary: {summary}")

    print("\n[TEST] Embeddings (local)")
    texts = ["FIR filed at Andheri police station", "जमानत अर्जी"]
    vecs = embed_texts(texts)
    print(f"  Embedded {len(vecs)} texts, dim={len(vecs[0])}")

    print("\nAll local model functions working correctly.")
