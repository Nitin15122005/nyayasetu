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

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
groq_client = Groq(api_key=GROQ_API_KEY)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.5-flash"


def get_gemini_client():
    """Returns a Gemini client, or None if GEMINI_API_KEY is not set."""
    return genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
