# -*- coding: utf-8 -*-
"""
colab_config.py — NyayaSetu Colab inference configuration
SPIT CSE | Team IKS

Update COLAB_BASE_URL whenever ngrok gives a new URL.
"""

# =========================================================
# ACTIVE COLAB NGROK URL
# =========================================================

COLAB_BASE_URL = "https://nonfebrile-bracingly-amina.ngrok-free.dev"

# =========================================================
# REQUEST TIMEOUT
# =========================================================

COLAB_TIMEOUT = 120


# =========================================================
# ENDPOINT HELPER
# =========================================================

def endpoint(path: str) -> str:
    """
    Build endpoint URL safely.

    Example:
        endpoint("/translate")
    """
    return COLAB_BASE_URL.rstrip("/") + path


# =========================================================
# CORE ENDPOINTS
# =========================================================

COLAB_HEALTH_URL = endpoint("/health")

COLAB_TRANSLATE_URL = endpoint("/translate")

COLAB_SUMMARIZE_URL = endpoint("/summarize")

COLAB_EMBED_URL = endpoint("/embed")

COLAB_CLASSIFY_URL = endpoint("/classify")

COLAB_RETRIEVE_URL = endpoint("/retrieve")

# NOTE: the notebook (NyayaSetu_Final_Corrected.ipynb) does not currently
# expose /ner or /keywords — it only serves /health /translate /summarize
# /embed /classify /retrieve. These two are not called anywhere; kept as
# placeholders for if/when the notebook adds them, not as live endpoints.
COLAB_NER_URL = endpoint("/ner")

COLAB_KEYWORDS_URL = endpoint("/keywords")