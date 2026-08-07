# -*- coding: utf-8 -*-
"""
evaluation/harness/notebook_client.py — direct client for the Colab notebook

Deliberately independent of backend/local_models.py, even though the two
overlap heavily. The point is that if this client's understanding of the
notebook's contract ever diverges from local_models.py's, that divergence
IS the finding (a `translate()` call here decodes the `translated` key,
matching NyayaSetu_Final_Corrected.ipynb's actual /translate response —
if the backend's local_models.translate_with_nllb() were fixed to also
read that key, both clients would agree; today, the embeddings.yaml and
retrieval.yaml suites test the notebook directly through THIS client, so
they aren't silently affected by that unrelated backend-side bug).

Base URL resolution: explicit `base_url` arg > COLAB_BASE_URL env var >
backend/colab_config.py's COLAB_BASE_URL (best-effort import — this is the
one place the eval framework reads a backend file, purely for the
convenience default, never for logic).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

import requests


def _default_colab_base_url() -> str:
    env_val = os.getenv("COLAB_BASE_URL")
    if env_val:
        return env_val
    try:
        import sys
        from pathlib import Path
        backend_dir = Path(__file__).resolve().parents[2] / "backend"
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        import colab_config  # backend/colab_config.py
        return colab_config.COLAB_BASE_URL
    except Exception:
        return "http://localhost:8000"   # last-resort default if the notebook is run locally


@dataclass
class NotebookResponse:
    status_code: int
    latency_ms: float
    json_body: Optional[dict] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 300


class NotebookClient:
    """Calls NyayaSetu_Final_Corrected.ipynb's FastAPI server directly."""

    ENDPOINTS = ("/health", "/translate", "/summarize", "/embed", "/classify", "/retrieve")

    def __init__(self, base_url: Optional[str] = None, timeout_s: float = 120.0):
        self.base_url = (base_url or _default_colab_base_url()).rstrip("/")
        self.timeout_s = timeout_s

    def _post(self, path: str, payload: dict, timeout_s: Optional[float] = None) -> NotebookResponse:
        start = time.perf_counter()
        try:
            resp = requests.post(f"{self.base_url}{path}", json=payload,
                                  timeout=timeout_s or self.timeout_s)
            latency_ms = (time.perf_counter() - start) * 1000
            try:
                body = resp.json()
            except ValueError:
                body = None
            return NotebookResponse(status_code=resp.status_code, latency_ms=latency_ms, json_body=body)
        except requests.exceptions.RequestException as e:
            return NotebookResponse(status_code=-1, latency_ms=(time.perf_counter() - start) * 1000, error=str(e))

    def health(self) -> NotebookResponse:
        start = time.perf_counter()
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=10)
            latency_ms = (time.perf_counter() - start) * 1000
            try:
                body = resp.json()
            except ValueError:
                body = None
            return NotebookResponse(status_code=resp.status_code, latency_ms=latency_ms, json_body=body)
        except requests.exceptions.RequestException as e:
            return NotebookResponse(status_code=-1, latency_ms=(time.perf_counter() - start) * 1000, error=str(e))

    def translate(self, text: str, src_lang: str, tgt_lang: str) -> NotebookResponse:
        # Notebook's actual response key is "translated" (see the header note
        # above) — NOT "translated_text". This client reads it correctly.
        return self._post("/translate", {"text": text, "src_lang": src_lang, "tgt_lang": tgt_lang})

    def summarize(self, text: str, min_length: int = 30, max_length: int = 130) -> NotebookResponse:
        return self._post("/summarize", {"text": text, "min_length": min_length, "max_length": max_length})

    def embed(self, texts: list[str]) -> NotebookResponse:
        return self._post("/embed", {"texts": texts})

    def classify(self, text: str) -> NotebookResponse:
        return self._post("/classify", {"text": text[:512]})

    def retrieve(self, query: str, top_k: int = 5, alpha: float = 0.5) -> NotebookResponse:
        return self._post("/retrieve", {"query": query, "top_k": top_k, "alpha": alpha})
