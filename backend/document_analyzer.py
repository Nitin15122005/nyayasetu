# -*- coding: utf-8 -*-
"""
document_analyzer.py — Core Document Analysis Engine
NyayaSetu | Team IKS | SPIT CSE 2025-26

Changes from previous version:
  - DocumentRAG now uses _LocalEmbedder, which runs MiniLM in-process on
    this machine's GPU/CPU (local_ai_models.py) instead of calling out to
    a Colab notebook over HTTP.
  - summarize_document calls local_models.summarize_with_bart, which now
    runs BART in-process too — no other changes needed there.
  - All other logic (clause scoring, RAG Q&A, IndianKanoon, etc.) unchanged.

PARALLEL PIPELINE (v6):
  - Phase 1: Translation (local NLLB → Gemini → Groq) runs concurrently with
             document-type detection & legal section extraction.
  - Phase 2: ALL Groq analysis tasks fire simultaneously via ThreadPoolExecutor.
  - Phase 3: IndianKanoon targeted case-law fetch.
"""

import os, sys, re, json
import logging
from concurrent.futures import ThreadPoolExecutor, wait as _futures_wait, ALL_COMPLETED
import requests as req
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz          # PyMuPDF
from pydantic import BaseModel
from gpu_utils import DEVICE
from legal_translator import detect_language_with_llm, translate_legal_text
from ai_clients import groq_client, GROQ_MODEL
from urllib.parse import quote
import base64

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=12)

INDIANKANOON_API_KEY = os.getenv("INDIANKANOON_API_KEY", "")


# ─────────────────────────────────────────────────────────────
# _LocalEmbedder — drop-in replacement for SentenceTransformer
# Used by DocumentRAG so the rest of the class is unchanged.
# ─────────────────────────────────────────────────────────────
class _LocalEmbedder:
    """
    Mimics the SentenceTransformer.encode() API but routes all calls
    through local_models.embed_texts(), which now runs MiniLM in-process
    on this machine's GPU/CPU (see local_ai_models.py) instead of over
    HTTP to a Colab notebook.

    DocumentRAG calls: self.embedder.encode(texts, normalize_embeddings=True,
                                            convert_to_numpy=True)
    This class accepts the same kwargs and returns a numpy array.
    """

    def __init__(self):
        # Lazy import — avoids circular dependency at module level
        import numpy as np
        self._np = np
        logger.info("[DocRAG] Using local embedding model (in-process, GPU if available).")

    def encode(
        self,
        texts,
        normalize_embeddings: bool = True,  # accepted, handled inside local_ai_models
        convert_to_numpy: bool = True,
        batch_size: int = 32,
        show_progress_bar: bool = False,
        **kwargs,
    ):
        """
        Encode texts via the local embedding model.
        Always returns a numpy float32 array with shape (N, dim).

        Deliberately does NOT catch exceptions and fall back to zero
        vectors. A zero-vector fallback makes every chunk score equally
        "relevant" during retrieval — that's silent data corruption, not
        graceful degradation, and it used to mask real problems (e.g. an
        unreachable Colab server) behind a working-looking answer. Local
        inference has no network failure mode; if this raises, something
        is genuinely wrong (bad input, OOM, corrupted model state) and the
        caller should see a clear error instead of degraded-looking results.
        """
        from local_models import embed_texts
        if isinstance(texts, str):
            texts = [texts]

        vecs = embed_texts(texts, batch_size=batch_size)
        return self._np.array(vecs, dtype=self._np.float32)


# ─────────────────────────────────────────────────────────────
# Document type definitions
# ─────────────────────────────────────────────────────────────
DOCUMENT_TYPES = {
    "rental_agreement": {
        "label":    "Rental Agreement",
        "keywords": ["tenancy", "rent", "landlord", "tenant", "premises", "lease", "monthly rent"],
        "required_clauses": [
            "Termination clause",
            "Maintenance clause",
            "Security deposit clause",
            "Notice period clause",
            "Rent escalation clause",
            "Subletting / lock-in clause",
        ],
    },
    "employment_contract": {
        "label":    "Employment Contract",
        "keywords": ["employment", "salary", "employer", "employee", "designation", "joining", "probation"],
        "required_clauses": [
            "Probation period clause",
            "Notice period clause",
            "Non-disclosure / confidentiality clause",
            "Termination clause",
            "Salary revision clause",
            "Intellectual property clause",
        ],
    },
    "loan_agreement": {
        "label":    "Loan Agreement",
        "keywords": ["loan", "borrower", "lender", "emi", "repayment", "collateral", "interest rate"],
        "required_clauses": [
            "Repayment schedule clause",
            "Interest rate clause",
            "Default clause",
            "Prepayment clause",
            "Security / collateral clause",
        ],
    },
    "sale_agreement": {
        "label":    "Sale Agreement",
        "keywords": ["sale", "purchase", "buyer", "seller", "payment", "delivery", "goods"],
        "required_clauses": [
            "Payment terms clause",
            "Delivery clause",
            "Warranty clause",
            "Dispute resolution clause",
            "Force majeure clause",
        ],
    },
    "service_agreement": {
        "label":    "Service Agreement",
        "keywords": ["service", "client", "vendor", "deliverable", "milestone", "fee", "scope of work"],
        "required_clauses": [
            "Scope of work clause",
            "Payment terms clause",
            "Confidentiality clause",
            "Termination clause",
            "Liability / indemnity clause",
            "Intellectual property clause",
        ],
    },
    "nda": {
        "label":    "Non-Disclosure Agreement",
        "keywords": ["confidential", "non-disclosure", "proprietary", "disclose", "recipient", "disclosing party"],
        "required_clauses": [
            "Definition of confidential information",
            "Obligations of receiving party",
            "Exclusions clause",
            "Term / duration clause",
            "Return of information clause",
        ],
    },
    "fir": {
        "label":    "FIR / Police Complaint",
        "keywords": ["fir", "first information report", "complainant", "accused", "police station", "offence"],
        "required_clauses": [],
    },
    "legal_notice": {
        "label":    "Legal Notice / Court Document",
        "keywords": ["summon", "notice", "court", "plaintiff", "defendant", "petition", "jurisdiction"],
        "required_clauses": [],
    },
    "unknown": {
        "label":    "General Legal Document",
        "keywords": [],
        "required_clauses": [
            "Termination clause",
            "Dispute resolution clause",
            "Governing law clause",
        ],
    },
}


# ─────────────────────────────────────────────────────────────
# Pydantic models
# ─────────────────────────────────────────────────────────────
class ClauseAnalysis(BaseModel):
    clause_text:   str
    risk_level:    str
    risk_score:    float
    explanation:   str
    confidence:    float
    suggestion:    str
    safer_version: Optional[str] = None

class PartyObligation(BaseModel):
    party_name:  str
    obligations: list[str]

class MissingClause(BaseModel):
    clause:        str
    present:       bool
    why_important: str

class KeyNumber(BaseModel):
    label: str
    value: str
    type:  str

class Deadline(BaseModel):
    description: str
    deadline:    str
    consequence: Optional[str] = None

class SignatureVerdict(BaseModel):
    verdict: str
    color:   str
    reason:  str

class SectionExplanation(BaseModel):
    section:      str
    title:        str
    explanation:  str
    punishment:   str = ""
    key_elements: list[str] = []

class DocumentAnalysis(BaseModel):
    document_name:       str
    document_type:       str
    document_type_key:   str
    type_confidence:     int
    total_clauses:       int
    summary:             str
    risk_distribution:   dict
    clauses:             list[ClauseAnalysis]
    overall_risk:        str
    compliance_score:    int
    case_laws:           list[dict]
    recommendations:     list[str]
    party_obligations:   list[PartyObligation]
    missing_clauses:     list[MissingClause]
    key_numbers:         list[KeyNumber]
    deadlines:           list[Deadline]
    suggested_questions: list[str]
    signature_verdict:   SignatureVerdict
    original_text:          Optional[str]   = None
    source_language:        Optional[str]   = None
    full_translation:       Optional[str]   = None
    translation_engine:     Optional[str]   = None
    translation_confidence: Optional[float] = None
    mentioned_sections:     list[str]       = []
    section_explanations:   list[dict]      = []

class QAResponse(BaseModel):
    question:   str
    answer:     str
    confidence: float
    sources:    list[str]
    disclaimer: str


# ─────────────────────────────────────────────────────────────
# Text extraction & Vision OCR
# ─────────────────────────────────────────────────────────────
def extract_text_with_vision(image_bytes: bytes) -> str:
    try:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        completion = groq_client.chat.completions.create(
            model="llama-3.2-90b-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extract all text from this image exactly as it appears. "
                            "Do not add any commentary. If the text is in an Indian language "
                            "(like Marathi or Hindi), transcribe it perfectly in its native script."
                        )
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                    }
                ]
            }],
            temperature=0.0,
            max_tokens=2048
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("[VISION] Failed to extract text: %s", e)
        return ""

def extract_text(file_bytes: bytes, filename: str) -> str:
    fname = filename.lower()
    if fname.endswith(".pdf"):
        doc  = fitz.open(stream=file_bytes, filetype="pdf")
        text = "\n".join(page.get_text("text") for page in doc).strip()
        if len(text) < 50:
            logger.info("[ANALYZER] PDF seems scanned. Falling back to Vision OCR...")
            vision_text = []
            for page_num in range(min(3, len(doc))):
                page     = doc.load_page(page_num)
                pix      = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("jpeg")
                extracted = extract_text_with_vision(img_bytes)
                if extracted:
                    vision_text.append(extracted)
            doc.close()
            return "\n\n".join(vision_text).strip()
        doc.close()
        return text
    elif any(fname.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
        logger.info("[ANALYZER] Image detected. Using Vision OCR...")
        return extract_text_with_vision(file_bytes)
    return ""


# ─────────────────────────────────────────────────────────────
# Clause segmentation
# ─────────────────────────────────────────────────────────────
def segment_clauses(text: str) -> list[str]:
    numbered = re.split(
        r'\n(?=(?:\d+[\.]\s)|(?:Clause\s+\d+)|(?:Section\s+\d+)|(?:[A-Z]\.\s))',
        text,
    )
    if len(numbered) > 3:
        return [c.strip() for c in numbered if len(c.strip()) > 30]
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
    if len(paragraphs) > 2:
        return paragraphs
    words, chunks, chunk = text.split(), [], []
    for word in words:
        chunk.append(word)
        if len(" ".join(chunk)) > 300:
            chunks.append(" ".join(chunk))
            chunk = []
    if chunk:
        chunks.append(" ".join(chunk))
    return chunks


# ─────────────────────────────────────────────────────────────
# Document type detection
# ─────────────────────────────────────────────────────────────
def detect_document_type(text: str) -> tuple[str, str, int]:
    lower  = text.lower()
    scores = {}
    for key, cfg in DOCUMENT_TYPES.items():
        if key == "unknown" or not cfg["keywords"]:
            continue
        hits = sum(1 for kw in cfg["keywords"] if kw in lower)
        if hits:
            scores[key] = hits / len(cfg["keywords"])

    if not scores:
        return "unknown", DOCUMENT_TYPES["unknown"]["label"], 40

    best_key   = max(scores, key=scores.get)
    confidence = min(int(scores[best_key] * 100), 97)
    if confidence < 20:
        return "unknown", DOCUMENT_TYPES["unknown"]["label"], 40
    return best_key, DOCUMENT_TYPES[best_key]["label"], confidence


GROQ_FAST_MODEL = os.getenv("GROQ_FAST_MODEL", "llama-3.1-8b-instant")

import time as _time

def _groq_call(model: str, prompt: str, temperature: float, max_tokens: int) -> str:
    for attempt in range(4):
        try:
            resp = groq_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate_limit" in msg.lower():
                wait = 3 * (attempt + 1)
                logger.warning("[LLM] Rate limit hit. Waiting %ds (attempt %d/4)...", wait, attempt + 1)
                _time.sleep(wait)
            else:
                raise
    raise RuntimeError("Groq rate limit: exceeded max retries")


def call_llm(prompt: str, temperature: float = 0.1) -> str:
    return _groq_call(GROQ_MODEL, prompt, temperature, max_tokens=3000)


def call_llm_fast(prompt: str, temperature: float = 0.1) -> str:
    return _groq_call(GROQ_FAST_MODEL, prompt, temperature, max_tokens=1500)


def parse_json_response(raw: str, fallback):
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*",     "", raw).strip()
    for pattern in (r'\[.*\]', r'\{.*\}'):
        m = re.search(pattern, raw, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return fallback


def compute_confidence(context: str, answer: str) -> float:
    uncertainty = ["i'm not sure", "unclear", "cannot determine", "not specified", "ambiguous"]
    certainty   = ["section", "clause", "shall", "must", "rs.", "₹", "days", "months", "%"]
    al    = answer.lower()
    score = 0.6 + sum(0.05 for m in certainty if m in al) - sum(0.15 for m in uncertainty if m in al)
    return round(max(0.1, min(0.95, score)), 2)


# ─────────────────────────────────────────────────────────────
# Clause risk scoring
# ─────────────────────────────────────────────────────────────
def analyze_clause(clause: str, doc_type: str) -> ClauseAnalysis:
    prompt = f"""You are an Indian legal expert reviewing a {doc_type}.
Analyze this clause and respond ONLY with a valid JSON object — no other text.

CLAUSE:
{clause[:500]}

JSON format:
{{
  "risk_level": "Safe" or "Caution" or "High Risk" or "Illegal",
  "risk_score": 0.0 to 1.0,
  "explanation": "one plain-English sentence explaining why",
  "confidence": 0.0 to 1.0,
  "suggestion": "one sentence on what the user should do",
  "safer_version": "if risk_level is High Risk or Illegal, write a fairer rewrite. Otherwise null."
}}

Risk guide:
- Safe: standard, fair language
- Caution: unusual or one-sided but not illegal
- High Risk: significantly unfair, likely challengeable in court
- Illegal: violates Indian law (Consumer Protection Act, Contract Act, BNS 2023, labour laws)"""

    raw  = call_llm_fast(prompt)
    data = parse_json_response(raw, {})
    return ClauseAnalysis(
        clause_text=clause[:300],
        risk_level=data.get("risk_level", "Caution"),
        risk_score=float(data.get("risk_score", 0.5)),
        explanation=data.get("explanation", "Could not parse this clause automatically."),
        confidence=float(data.get("confidence", 0.5)),
        suggestion=data.get("suggestion", "Review with a lawyer."),
        safer_version=data.get("safer_version") or None,
    )


# ─────────────────────────────────────────────────────────────
# Document summary  (Colab BART → Groq fallback)
# ─────────────────────────────────────────────────────────────
def summarize_document(text: str, doc_type: str) -> str:
    # ── 1. Try Colab BART (fast, no API cost) ──────────────────────────────────
    try:
        from local_models import summarize_with_bart
        bart_summary = summarize_with_bart(text[:3000])
        if bart_summary and len(bart_summary) > 40:
            logger.info("[ANALYZER] Colab BART summary OK.")
            return bart_summary
    except Exception as bart_err:
        logger.warning("[ANALYZER] Colab BART failed (%s), falling back to Groq...", bart_err)

    # ── 2. Groq LLM fallback ────────────────────────────────────────────────────
    prompt = f"""You are an Indian legal assistant. Summarize this {doc_type} in plain English for a common person.
Under 120 words. Cover: what it is, who the parties are, key obligations, and any major risks.
No headings or bullet points.

DOCUMENT (first 2000 chars):
{text[:2000]}"""
    return call_llm(prompt, temperature=0.2)


# ─────────────────────────────────────────────────────────────
# Party obligation map
# ─────────────────────────────────────────────────────────────
def extract_party_obligations(text: str, doc_type: str) -> list[PartyObligation]:
    prompt = f"""You are an Indian legal expert. From this {doc_type}, extract the obligations of each party.

Return a JSON array:
[
  {{"party_name": "Landlord", "obligations": ["Must maintain the property", "Cannot enter without 24h notice"]}},
  {{"party_name": "Tenant",   "obligations": ["Must pay rent by 5th of each month", "Cannot sublet without permission"]}}
]

Only include obligations clearly stated in the document. Return ONLY valid JSON array.

DOCUMENT:
{text[:3000]}"""

    raw  = call_llm(prompt, temperature=0.1)
    data = parse_json_response(raw, [])
    results = []
    for item in (data if isinstance(data, list) else []):
        try:
            results.append(PartyObligation(
                party_name=str(item.get("party_name", "Party")),
                obligations=[str(o) for o in item.get("obligations", [])],
            ))
        except Exception:
            pass
    return results


# ─────────────────────────────────────────────────────────────
# Missing clauses detector
# ─────────────────────────────────────────────────────────────
def detect_missing_clauses(text: str, type_key: str) -> list[MissingClause]:
    required = DOCUMENT_TYPES.get(type_key, DOCUMENT_TYPES["unknown"])["required_clauses"]
    if not required:
        return []

    label  = DOCUMENT_TYPES.get(type_key, DOCUMENT_TYPES["unknown"])["label"]
    prompt = f"""You are an Indian legal expert reviewing a {label}.
Check if each of these standard clauses is present in the document.

Clauses to check:
{json.dumps(required)}

Return a JSON array, one item per clause:
[
  {{"clause": "Termination clause",   "present": true,  "why_important": "Defines how either party can exit."}},
  {{"clause": "Notice period clause", "present": false, "why_important": "Protects you from sudden eviction."}}
]

Return ONLY valid JSON array.

DOCUMENT:
{text[:3000]}"""

    raw  = call_llm_fast(prompt, temperature=0.1)
    data = parse_json_response(raw, [])
    results = []
    for item in (data if isinstance(data, list) else []):
        try:
            results.append(MissingClause(
                clause=str(item.get("clause", "")),
                present=bool(item.get("present", False)),
                why_important=str(item.get("why_important", "")),
            ))
        except Exception:
            pass

    if not results:
        lower = text.lower()
        for clause in required:
            kws     = [w for w in clause.lower().replace(" clause", "").split() if len(w) > 3]
            present = any(kw in lower for kw in kws)
            results.append(MissingClause(
                clause=clause,
                present=present,
                why_important=f"Standard protection in a {label}.",
            ))
    return results


# ─────────────────────────────────────────────────────────────
# Key numbers extractor
# ─────────────────────────────────────────────────────────────
def extract_key_numbers(text: str) -> list[KeyNumber]:
    prompt = f"""Extract every monetary amount, date, percentage, and duration from this legal document.

Return a JSON array:
[
  {{"label": "Security Deposit", "value": "₹50,000",     "type": "monetary"}},
  {{"label": "Monthly Rent",     "value": "₹15,000",     "type": "monetary"}},
  {{"label": "Notice Period",    "value": "30 days",      "type": "duration"}},
  {{"label": "Start Date",       "value": "1 Jan 2025",   "type": "date"}}
]

Types: monetary / date / percentage / duration / other
Return ONLY valid JSON array.

DOCUMENT:
{text[:4000]}"""

    raw  = call_llm_fast(prompt, temperature=0.0)
    data = parse_json_response(raw, [])
    results = []
    for item in (data if isinstance(data, list) else []):
        try:
            results.append(KeyNumber(
                label=str(item.get("label", "")),
                value=str(item.get("value", "")),
                type=str(item.get("type",  "other")),
            ))
        except Exception:
            pass
    seen, unique = set(), []
    for n in results:
        key = (re.sub(r'\s+', '', n.value.strip().lower()), n.type)
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return unique


# ─────────────────────────────────────────────────────────────
# Deadline alerts
# ─────────────────────────────────────────────────────────────
def extract_deadlines(text: str) -> list[Deadline]:
    prompt = f"""Extract all deadlines, time limits, and limitation periods from this legal document.

Return a JSON array:
[
  {{"description": "Rent payment",   "deadline": "5th of every month",  "consequence": "2% late fee"}},
  {{"description": "Notice to quit", "deadline": "30 days in advance",  "consequence": "Security deposit forfeited"}}
]

Use null for consequence if not stated.
Return ONLY valid JSON array.

DOCUMENT:
{text[:3000]}"""

    raw  = call_llm_fast(prompt, temperature=0.0)
    data = parse_json_response(raw, [])
    results = []
    for item in (data if isinstance(data, list) else []):
        try:
            results.append(Deadline(
                description=str(item.get("description", "")),
                deadline=str(item.get("deadline", "")),
                consequence=item.get("consequence") or None,
            ))
        except Exception:
            pass
    return results


# ─────────────────────────────────────────────────────────────
# Suggested questions
# ─────────────────────────────────────────────────────────────
def generate_suggested_questions(text: str, doc_type: str) -> list[str]:
    prompt = f"""You are an Indian legal expert. A user just had their {doc_type} analyzed.
Generate exactly 6 questions they are most likely to ask about this specific document.
Make them concrete and based on the document content — not generic.

Return a JSON array of 6 question strings only.
Example: ["Can the landlord enter without notice?", "What happens if I miss a payment?"]

Return ONLY valid JSON array.

DOCUMENT (first 1500 chars):
{text[:1500]}"""

    raw  = call_llm(prompt, temperature=0.3)
    data = parse_json_response(raw, [])
    if isinstance(data, list) and len(data) >= 3:
        return [str(q) for q in data[:6]]
    return [
        "What are my main obligations under this agreement?",
        "Can the other party terminate without prior notice?",
        "What happens if I miss a payment?",
        "Is there a penalty clause I should know about?",
        "Can I negotiate the high-risk clauses?",
        "Which clauses protect me the most?",
    ]


# ─────────────────────────────────────────────────────────────
# Signature verdict
# ─────────────────────────────────────────────────────────────
def get_signature_verdict(
    clauses: list[ClauseAnalysis],
    missing: list[MissingClause],
) -> SignatureVerdict:
    illegal_count   = sum(1 for c in clauses if c.risk_level == "Illegal")
    high_risk_count = sum(1 for c in clauses if c.risk_level == "High Risk")
    missing_count   = sum(1 for m in missing if not m.present)

    if illegal_count > 0:
        return SignatureVerdict(
            verdict="Do Not Sign",
            color="red",
            reason=f"Contains {illegal_count} illegal clause(s) that violate Indian law. Seek legal counsel.",
        )
    if high_risk_count >= 3 or (high_risk_count >= 1 and missing_count >= 2):
        return SignatureVerdict(
            verdict="Negotiate First",
            color="orange",
            reason=f"{high_risk_count} high-risk clause(s) and {missing_count} missing standard protection(s).",
        )
    if high_risk_count >= 1 or missing_count >= 2:
        return SignatureVerdict(
            verdict="Negotiate First",
            color="orange",
            reason=f"Review {high_risk_count} risky clause(s) and consider adding {missing_count} missing standard clause(s).",
        )
    return SignatureVerdict(
        verdict="Safe to Sign",
        color="green",
        reason="No illegal or high-risk clauses detected and standard protections appear to be present.",
    )


# ─────────────────────────────────────────────────────────────
# Overall risk
# ─────────────────────────────────────────────────────────────
def compute_overall_risk(clauses: list[ClauseAnalysis]) -> str:
    if not clauses:
        return "Unknown"
    illegal = sum(1 for c in clauses if c.risk_level == "Illegal")
    high    = sum(1 for c in clauses if c.risk_level == "High Risk")
    caution = sum(1 for c in clauses if c.risk_level == "Caution")
    if illegal > 0:               return "Critical"
    if high >= 2:                 return "High"
    if high == 1 or caution >= 3: return "Moderate"
    return "Safe"


# ─────────────────────────────────────────────────────────────
# Legal section extraction + explanation
# ─────────────────────────────────────────────────────────────
def extract_legal_sections(text: str) -> list[str]:
    patterns = [
        r'(?:BNS|Bharatiya Nyaya Sanhita)\s*(?:Section|Sec\.?|S\.)?\s*\d+(?:\s*\([^)]+\))?',
        r'(?:IPC|Indian Penal Code)\s*(?:Section|Sec\.?)?\s*\d+(?:\s*\([^)]+\))?',
        r'(?:CrPC|BNSS|Bharatiya Nagarik Suraksha Sanhita)\s*(?:Section|Sec\.?)?\s*\d+(?:\s*\([^)]+\))?',
        r'(?:BSA|Bharatiya Sakshya Adhiniyam)\s*(?:Section|Sec\.?)?\s*\d+(?:\s*\([^)]+\))?',
        r'[Ss]ection\s*\d+(?:\s*\([^)]+\))?\s+(?:of\s+(?:the\s+)?)?(?:BNS|IPC|CrPC|BNSS|BSA|Indian Penal Code|Bharatiya Nyaya Sanhita)',
        r'[Uu]/[Ss]\s*\d+(?:\s*\([^)]+\))?',
    ]
    found = set()
    for p in patterns:
        for m in re.finditer(p, text, re.IGNORECASE):
            s = m.group(0).strip()
            if len(s) > 4:
                found.add(s)
    return sorted(found)[:12]


def explain_legal_sections(sections: list[str], doc_type: str) -> list[dict]:
    if not sections:
        return []
    slist = "\n".join(f"- {s}" for s in sections[:8])
    prompt = (
        f"You are an expert in Indian law (IPC, BNS 2023, CrPC, BNSS 2023, BSA 2023).\n"
        f"A {doc_type} mentions these legal provisions. Explain each one for a non-lawyer.\n\n"
        f"SECTIONS:\n{slist}\n\n"
        "Return a JSON array:\n"
        '[{\n'
        '  "section": "BNS Section 304",\n'
        '  "title": "Theft",\n'
        '  "explanation": "Punishes taking someone else\'s property without consent.",\n'
        '  "punishment": "Imprisonment up to 3 years, or fine, or both",\n'
        '  "key_elements": ["Dishonest intention", "Property belongs to another", "Without consent"]\n'
        "}]\n\n"
        "Be accurate about BNS 2023 sections. Return ONLY valid JSON array."
    )
    raw  = call_llm(prompt, temperature=0.0)
    data = parse_json_response(raw, [])
    return data if isinstance(data, list) else []


# ─────────────────────────────────────────────────────────────
# IndianKanoon
# ─────────────────────────────────────────────────────────────
def fetch_case_laws(query: str, doc_type: str, sections: list[str] = None, pagenum: int = 0) -> list[dict]:
    if not INDIANKANOON_API_KEY:
        return [{
            "title":   "IndianKanoon API key not configured",
            "summary": "Add INDIANKANOON_API_KEY to your .env file.",
            "url":     "https://indiankanoon.org",
            "court":   "", "year": "", "related_section": None,
        }]

    queries: list[str] = []
    if sections:
        for s in sections[:5]:
            queries.append(s)
    queries.append(query[:200])

    results, seen_tids = [], set()
    for search_q in queries:
        if len(results) >= 25:
            break
        try:
            r = req.post(
                "https://api.indiankanoon.org/search/",
                data={"formInput": search_q, "pagenum": pagenum},
                headers={"Authorization": f"Token {INDIANKANOON_API_KEY}",
                         "Content-Type": "application/x-www-form-urlencoded"},
                timeout=15,
            )
            r.raise_for_status()
            docs = r.json().get("docs", [])
            for doc in docs:
                tid = doc.get("tid", "")
                if tid in seen_tids:
                    continue
                seen_tids.add(tid)
                raw_summary  = doc.get("headline", "") + " " + doc.get("doc", "")[:500]
                clean_summary = re.sub(r'<[^>]+>', '', raw_summary).strip()
                results.append({
                    "title":           re.sub(r'<[^>]+>', '', doc.get("title", "Untitled")),
                    "summary":         clean_summary + "...",
                    "url":             f"https://indiankanoon.org/doc/{tid}",
                    "court":           doc.get("docsource", ""),
                    "year":            doc.get("publishdate", "")[:4] if doc.get("publishdate") else "",
                    "related_section": search_q if (sections and search_q in sections) else None,
                })
                if len(results) >= 25:
                    break
        except Exception as e:
            logger.warning("[KANOON] Error for '%s': %s", search_q[:60], e)
    return results


def fetch_acts(
    query: str,
    act_type: str = "central",
    state_name: str = "",
    pagenum: int = 0
) -> list[dict]:
    if not INDIANKANOON_API_KEY:
        return [{
            "title":        "IndianKanoon API key not configured",
            "summary":      "Add INDIANKANOON_API_KEY to your .env file.",
            "url":          "https://indiankanoon.org",
            "jurisdiction": "", "year": "", "act_type": act_type,
        }]

    results, seen_tids = [], set()
    try:
        search_query = (
            f"{query} central act"         if act_type.lower() == "central" else
            f"{query} {state_name} state act" if act_type.lower() == "state" else
            query
        )
        r = req.post(
            "https://api.indiankanoon.org/search/",
            data={"formInput": search_query, "pagenum": pagenum},
            headers={"Authorization": f"Token {INDIANKANOON_API_KEY}",
                     "Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        r.raise_for_status()
        for doc in r.json().get("docs", []):
            tid = doc.get("tid", "")
            if not tid or tid in seen_tids:
                continue
            seen_tids.add(tid)
            title        = re.sub(r"<[^>]+>", "", str(doc.get("title", "Untitled"))).strip()
            raw_summary  = str(doc.get("headline", "")) + " " + str(doc.get("doc", ""))[:500]
            clean_summary = re.sub(r"<[^>]+>", "", raw_summary).strip()
            publish_date = str(doc.get("publishdate", ""))
            results.append({
                "title":        title,
                "summary":      clean_summary + "...",
                "url":          f"https://indiankanoon.org/doc/{tid}/",
                "jurisdiction": doc.get("docsource", ""),
                "year":         publish_date[:4] if publish_date else "",
                "act_type":     act_type,
                "doc_id":       tid,
            })
    except Exception as e:
        logger.error("[ACTS ERROR] %s", e)
    return results


# ─────────────────────────────────────────────────────────────
# Document RAG — multi-turn Q&A
# ─────────────────────────────────────────────────────────────
class DocumentRAG:
    """
    In-memory vector store for a single uploaded document.
    Uses _LocalEmbedder — all embedding inference runs in-process on this
    machine's GPU/CPU (no network dependency, no ngrok/Colab required).
    """

    def __init__(self):
        self.embedder    = _LocalEmbedder()
        self.chunks:     list[str]  = []
        self.embeddings             = []
        self.doc_type:   str        = "Legal Document"
        self.history:    list[dict] = []

    def index(self, clauses: list[str], doc_type: str = "Legal Document"):
        self.chunks     = clauses
        self.doc_type   = doc_type
        self.embeddings = self.embedder.encode(
            clauses, normalize_embeddings=True, convert_to_numpy=True
        )
        logger.info("[DocRAG] Indexed %d chunks for %s", len(clauses), doc_type)

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        if not self.chunks:
            return []
        import numpy as np
        q_emb   = self.embedder.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        scores  = (self.embeddings @ q_emb.T).flatten()
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [self.chunks[i] for i in top_idx]

    def answer(self, question: str) -> QAResponse:
        logger.info("[DocRAG.answer] Q: %s", question[:100])
        if not self.chunks:
            return QAResponse(
                question=question,
                answer="No document indexed. Please upload a document first.",
                confidence=0.0, sources=[], disclaimer="Upload a document to begin."
            )

        relevant = self.retrieve(question, top_k=6)
        if self.chunks and self.chunks[0] not in relevant:
            relevant = [self.chunks[0]] + relevant[:5]
        context = "\n\n---\n\n".join(relevant)

        system_prompt = (
            f"You are NyayaBot, an elite Indian legal analyst with deep expertise in:\n"
            f"- Bharatiya Nyaya Sanhita (BNS) 2023 & Indian Penal Code (IPC) 1860\n"
            f"- BNSS 2023 & CrPC | Bharatiya Sakshya Adhiniyam (BSA) 2023\n"
            f"- FIR procedure, bail, arrest, trial, constitutional rights (Articles 20-22)\n\n"
            f"You are analysing a {self.doc_type}. Answer ONLY from the document below.\n\n"
            f"DOCUMENT CONTENT:\n{context}\n\n"
            "RULES (strictly follow):\n"
            "1. Base every answer strictly on the document. If not mentioned, say so explicitly.\n"
            "2. For follow-up / cross-questions, use conversation history for continuity.\n"
            "3. Cite specific sections, names, dates, or clause text from the document.\n"
            "4. Define any legal term in plain language immediately after using it.\n"
            "5. Never speculate or hallucinate facts not present in the document."
        )

        messages = [{"role": "system", "content": system_prompt}]
        for turn in self.history[-10:]:
            messages.append(turn)
        messages.append({"role": "user", "content": question})

        try:
            resp = groq_client.chat.completions.create(
                model=GROQ_MODEL, messages=messages, temperature=0.1, max_tokens=2000,
            )
            answer_text = resp.choices[0].message.content.strip()
            self.history.append({"role": "user",      "content": question})
            self.history.append({"role": "assistant", "content": answer_text})
            confidence = compute_confidence(context, answer_text)
            disclaimer = ""
            if confidence < 0.4:
                disclaimer = "⚠ Low confidence — verify with the document or consult a lawyer."
            elif confidence < 0.65:
                disclaimer = "ℹ Moderate confidence — cross-check with the original document."
            return QAResponse(
                question=question, answer=answer_text, confidence=confidence,
                sources=[c[:120] for c in relevant[:3]], disclaimer=disclaimer
            )
        except Exception as e:
            logger.error("[DocRAG.answer] Error: %s", e)
            return QAResponse(
                question=question, answer=f"Error: {str(e)}",
                confidence=0.0, sources=[], disclaimer="Technical error. Please try again."
            )


# ─────────────────────────────────────────────────────────────
# Main analysis pipeline  (PARALLEL v6 — concurrent.futures)
# ─────────────────────────────────────────────────────────────
def analyze_document(
    file_bytes:    bytes,
    filename:      str,
    max_clauses:   int = 15,
    type_override: Optional[str] = None,
) -> tuple["DocumentAnalysis", "DocumentRAG"]:
    import time as _t
    t0 = _t.perf_counter()
    logger.info("[ANALYZER] >> Processing: %s", filename)

    # ── Step 0: Extract text ─────────────────────────────────────────────────
    text = extract_text(file_bytes, filename)
    if not text:
        raise ValueError("Could not extract text from document.")
    logger.info("[ANALYZER] Extracted %d chars", len(text))

    # ── Phase 1: Translation + type detect + section extract — PARALLEL ────────
    def _do_translation():
        lang_info = detect_language_with_llm(text)
        code = lang_info.get("language_code", "en")
        name = lang_info.get("language_name", "English")
        if code == "en":
            return None, None, None, None, name, code
        logger.info("[ANALYZER|P1] Detected %s. Translating (Colab NLLB → Gemini → Groq)...", name)
        tr = translate_legal_text(text, source_lang=code, target_lang="en")
        translated = tr.get("translated_text", "")
        if translated and translated.strip():
            return (
                text,
                translated,
                tr.get("engine", "unknown"),
                tr.get("confidence"),
                name,
                code,
            )
        logger.warning("[ANALYZER|P1] Translation returned empty — using original text.")
        return None, None, None, None, name, code

    def _do_type_detect(wtext: str):
        if type_override and type_override in DOCUMENT_TYPES:
            return type_override, DOCUMENT_TYPES[type_override]["label"], 100
        return detect_document_type(wtext)

    def _do_sections(wtext: str, orig):
        combined = wtext + (" " + orig if orig else "")
        return extract_legal_sections(combined)

    f_trans = _EXECUTOR.submit(_do_translation)
    (
        original_text, full_translation,
        translation_engine, translation_confidence,
        source_lang_name, source_lang_code,
    ) = f_trans.result()

    working_text = full_translation if full_translation else text

    f_type     = _EXECUTOR.submit(_do_type_detect, working_text)
    f_sections = _EXECUTOR.submit(_do_sections, working_text, original_text)
    type_key, doc_type, type_conf = f_type.result()
    mentioned_sections             = f_sections.result()
    # Emoji removed deliberately (see the [DocRAG] Colab-embed-failure note
    # above) — this line runs unconditionally mid-pipeline, so a
    # UnicodeEncodeError here would fail an otherwise-successful analysis.
    logger.info("[ANALYZER|P1] Type: %s (%s%%) | Sections: %s", doc_type, type_conf, mentioned_sections)

    # ── Phase 2: All analysis tasks submitted simultaneously ──────────────────
    all_clauses = segment_clauses(working_text)
    clauses     = all_clauses[:max_clauses]
    logger.info("[ANALYZER|P2] Submitting %d clause tasks + 6 doc-level tasks...", len(clauses))

    clause_futs  = [_EXECUTOR.submit(analyze_clause, c, doc_type) for c in clauses]
    f_summary    = _EXECUTOR.submit(summarize_document, working_text, doc_type)
    f_party      = _EXECUTOR.submit(extract_party_obligations, working_text, doc_type)
    f_missing    = _EXECUTOR.submit(detect_missing_clauses, working_text, type_key)
    f_numbers    = _EXECUTOR.submit(extract_key_numbers, working_text)
    f_deadlines  = _EXECUTOR.submit(extract_deadlines, working_text)
    f_questions  = _EXECUTOR.submit(generate_suggested_questions, working_text, doc_type)
    f_secexp     = (
        _EXECUTOR.submit(explain_legal_sections, mentioned_sections, doc_type)
        if mentioned_sections else None
    )
    f_compliance = _EXECUTOR.submit(
        lambda: __import__("lex_validator", fromlist=["compute_compliance_score"])
                    .compute_compliance_score(working_text)["score"]
    )

    _futures_wait(clause_futs, return_when=ALL_COMPLETED)
    analyzed: list[ClauseAnalysis] = []
    for f in clause_futs:
        try:
            analyzed.append(f.result())
        except Exception as e:
            logger.warning("[ANALYZER|P2] Clause task failed: %s", e)

    risky    = [c for c in analyzed if c.risk_level in ["High Risk", "Illegal"]]
    kw_src   = risky or [c for c in analyzed if c.risk_level == "Caution"]
    kws      = [c.explanation[:80] for c in kw_src[:2] if c.explanation and len(c.explanation) > 20]
    kanoon_q = (f"{doc_type} {' '.join(kws)}")[:200] if kws else doc_type
    f_kanoon = _EXECUTOR.submit(fetch_case_laws, kanoon_q, doc_type, mentioned_sections)

    def _safe(fut, default):
        if fut is None:
            return default
        try:
            return fut.result()
        except Exception as e:
            logger.warning("[ANALYZER] Task failed (%s): %s", type(e).__name__, e)
            return default

    summary              = _safe(f_summary,    "Summary generation failed.")
    party_obligations    = _safe(f_party,      [])
    missing_clauses      = _safe(f_missing,    [])
    key_numbers          = _safe(f_numbers,    [])
    deadlines            = _safe(f_deadlines,  [])
    suggested_questions  = _safe(f_questions,  [])
    section_explanations = _safe(f_secexp,     [])
    comp_score_raw       = _safe(f_compliance, 75)
    case_laws            = _safe(f_kanoon,     [])

    comp_score = int(comp_score_raw) if comp_score_raw else 75

    dist = {"Safe": 0, "Caution": 0, "High Risk": 0, "Illegal": 0}
    for c in analyzed:
        dist[c.risk_level] = dist.get(c.risk_level, 0) + 1
    overall           = compute_overall_risk(analyzed)
    signature_verdict = get_signature_verdict(analyzed, missing_clauses)

    recommendations = []
    if dist["Illegal"] > 0:
        recommendations.append(f"⚠️ {dist['Illegal']} clause(s) may violate Indian law. Do not sign without legal review.")
    if dist["High Risk"] > 0:
        recommendations.append(f"🔴 {dist['High Risk']} high-risk clause(s) found. Negotiate before signing.")
    if dist["Caution"] > 0:
        recommendations.append(f"🟡 {dist['Caution']} clause(s) need attention. Read carefully.")
    if comp_score < 70:
        recommendations.append(f"📋 Document uses obsolete IPC/CrPC references (Score: {comp_score}/100). Request updated version.")
    if not recommendations:
        recommendations.append("✅ Document appears fair. Standard review recommended before signing.")

    doc_rag = DocumentRAG()
    doc_rag.index(all_clauses, doc_type)

    elapsed = _t.perf_counter() - t0
    # Emoji removed deliberately — same rationale as above; this is the
    # final line of a successful analysis, so a crash here would turn a
    # completed analysis into a failed request.
    logger.info("[ANALYZER] Done in %.1fs | Verdict: %s", elapsed, signature_verdict.verdict)

    return DocumentAnalysis(
        document_name=filename,
        document_type=doc_type,
        document_type_key=type_key,
        type_confidence=type_conf,
        total_clauses=len(analyzed),
        summary=summary,
        risk_distribution=dist,
        clauses=analyzed,
        overall_risk=overall,
        compliance_score=comp_score,
        case_laws=case_laws,
        recommendations=recommendations,
        party_obligations=party_obligations,
        missing_clauses=missing_clauses,
        key_numbers=key_numbers,
        deadlines=deadlines,
        suggested_questions=suggested_questions,
        signature_verdict=signature_verdict,
        original_text=original_text,
        source_language=source_lang_name if original_text else None,
        full_translation=full_translation,
        translation_engine=translation_engine,
        translation_confidence=translation_confidence,
        mentioned_sections=mentioned_sections,
        section_explanations=section_explanations,
    ), doc_rag