# -*- coding: utf-8 -*-
"""
colab_config.py — OPTIONAL Colab notebook configuration
SPIT CSE | Team IKS

NOT required to run the production backend. As of this pass, embeddings
(MiniLM), summarization (BART), and translation (NLLB) all run in-process
locally — see local_ai_models.py — and no longer call this URL at all.

This file is only read by two legacy, research-only functions in
local_models.py (classify_document, retrieve_similar) plus check_colab_health(),
none of which are called by any production route (/api/analyze, /api/qa,
/api/compliance, /api/translate, etc. all work with the notebook stopped).
Keep this pointed at a running notebook only if you want to manually
exercise its MuRIL classifier or its own hybrid FAISS+BM25 retrieval for
research. Otherwise it can sit stale with no effect on the product.

Update COLAB_BASE_URL whenever ngrok gives a new URL, IF you're using the
research endpoints above.
"""

# =========================================================
# OPTIONAL — only used by research-only Colab client functions
# =========================================================

COLAB_BASE_URL = "https://nonfebrile-bracingly-amina.ngrok-free.dev"

COLAB_TIMEOUT = 120


def endpoint(path: str) -> str:
    """
    Build a Colab endpoint URL. Only called by the optional
    classify_document() / retrieve_similar() / check_colab_health()
    functions in local_models.py — not on the production inference path.

    Example:
        endpoint("/classify")
    """
    return COLAB_BASE_URL.rstrip("/") + path
