# -*- coding: utf-8 -*-
"""
evaluation/harness/client.py — black-box HTTP client for the NyayaSetu backend

Deliberately does NOT import backend/*.py. Evaluators call the same HTTP
surface a real user (or the frontend) would, so:
  - results reflect what's actually deployed, not internal function
    behavior that might differ from what's exposed;
  - the evaluation framework keeps working across backend refactors, as
    long as the API contract doesn't change;
  - auth, serialization, and error-handling bugs at the API boundary are
    caught, not bypassed.

Every call returns an APIResponse with wall-clock latency captured here
(not trusted from the server), status code, parsed JSON (if any), and the
raw text (for non-JSON/error bodies) — evaluators build metrics from this
uniformly instead of each hand-rolling requests.post().
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import requests


@dataclass
class APIResponse:
    status_code: int
    latency_ms: float
    json_body: Optional[dict] = None
    text_body: str = ""
    error: Optional[str] = None       # set on connection/timeout errors (status_code will be -1)

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 300


class NyayaSetuAPIClient:
    """
    Thin wrapper over the backend's HTTP API. Base URL resolution order:
    explicit `base_url` arg > NYAYASETU_EVAL_BASE_URL env var > GlobalConfig default.
    """

    def __init__(self, base_url: Optional[str] = None, timeout_s: float = 30.0, auth_token: Optional[str] = None):
        self.base_url = (
            base_url
            or os.getenv("NYAYASETU_EVAL_BASE_URL")
            or "http://localhost:8001"
        ).rstrip("/")
        self.timeout_s = timeout_s
        self.auth_token = auth_token or os.getenv("NYAYASETU_EVAL_AUTH_TOKEN")

    def _headers(self) -> dict:
        h = {}
        if self.auth_token:
            h["Authorization"] = f"Bearer {self.auth_token}"
        return h

    def _request(self, method: str, path: str, **kwargs) -> APIResponse:
        url = f"{self.base_url}{path}"
        start = time.perf_counter()
        try:
            resp = requests.request(
                method, url, timeout=self.timeout_s, headers=self._headers(), **kwargs
            )
            latency_ms = (time.perf_counter() - start) * 1000
            try:
                body = resp.json()
            except ValueError:
                body = None
            return APIResponse(
                status_code=resp.status_code,
                latency_ms=latency_ms,
                json_body=body,
                text_body=resp.text if body is None else "",
            )
        except requests.exceptions.RequestException as e:
            latency_ms = (time.perf_counter() - start) * 1000
            return APIResponse(status_code=-1, latency_ms=latency_ms, error=str(e))

    # ── Infra ────────────────────────────────────────────────────────────────
    def health(self) -> APIResponse:
        return self._request("GET", "/api/health")

    # ── Translation ──────────────────────────────────────────────────────────
    def translate(self, text: str, source_lang: Optional[str], target_lang: str = "en",
                   document_type: str = "FIR / Police Complaint") -> APIResponse:
        return self._request("POST", "/api/translate", json={
            "text": text, "source_lang": source_lang or "auto",
            "target_lang": target_lang, "document_type": document_type,
        })

    # ── Compliance / IPC-BNS mapping ────────────────────────────────────────
    def compliance(self, text: str) -> APIResponse:
        return self._request("POST", "/api/compliance", json={"text": text})

    # ── Document analysis ───────────────────────────────────────────────────
    def analyze(self, file_path: Path) -> APIResponse:
        with open(file_path, "rb") as f:
            return self._request("POST", "/api/analyze", files={"file": (file_path.name, f)})

    def qa(self, session_id: str, question: str) -> APIResponse:
        return self._request("POST", "/api/qa", json={"session_id": session_id, "question": question})

    # ── Research ─────────────────────────────────────────────────────────────
    def research_ask(self, query: str) -> APIResponse:
        return self._request("POST", "/api/research/ask", json={"query": query})

    def caselaws(self, query: str, doc_type: str = "Legal Question") -> APIResponse:
        return self._request("POST", "/api/caselaws", json={"query": query, "doc_type": doc_type})

    # ── Editor copilot ───────────────────────────────────────────────────────
    def editor_copilot(self, prompt: str, document_context: str = "") -> APIResponse:
        return self._request("POST", "/api/editor/copilot", json={
            "prompt": prompt, "document_context": document_context,
        })

    # ── Generic escape hatch for robustness-suite edge cases ───────────────
    def raw(self, method: str, path: str, **kwargs) -> APIResponse:
        return self._request(method, path, **kwargs)
