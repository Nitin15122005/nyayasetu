# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/corpus/rules.py — pure, non-LLM extraction
rules copied from production code, for use by the corpus pipeline.

WHY COPIED, NOT IMPORTED: backend/document_analyzer.py and
backend/lex_validator.py both eagerly construct a Groq client at module
import time (`from ai_clients import groq_client, ...` — see
ai_clients.py's docstring: "missing GROQ_API_KEY still fails at import
time"). This build environment has no GROQ_API_KEY set (see the infra
health validation), so importing either module directly is not possible.
Everything copied below is a PURE function/data structure with no
network or LLM call — copying it is safe and its behavior is identical
to production; each block cites its exact source.

If backend/document_analyzer.py or backend/lex_validator.py's copied
sections are edited in production, this file will silently drift — that
tradeoff is accepted here in exchange for being able to run corpus
extraction without live API keys. A future refactor that splits pure
rules out of those two files into an import-safe module would let this
file import them directly instead; noted as a follow-up, not done here
(out of scope — this phase builds datasets, not refactors the backend).
"""

from __future__ import annotations

import re

# ── Copied from backend/document_analyzer.py, lines 102-191 (DOCUMENT_TYPES) ──
DOCUMENT_TYPES = {
    "rental_agreement": {
        "label": "Rental Agreement",
        "keywords": ["tenancy", "rent", "landlord", "tenant", "premises", "lease", "monthly rent"],
        "required_clauses": [
            "Termination clause", "Maintenance clause", "Security deposit clause",
            "Notice period clause", "Rent escalation clause", "Subletting / lock-in clause",
        ],
    },
    "employment_contract": {
        "label": "Employment Contract",
        "keywords": ["employment", "salary", "employer", "employee", "designation", "joining", "probation"],
        "required_clauses": [
            "Probation period clause", "Notice period clause", "Non-disclosure / confidentiality clause",
            "Termination clause", "Salary revision clause", "Intellectual property clause",
        ],
    },
    "loan_agreement": {
        "label": "Loan Agreement",
        "keywords": ["loan", "borrower", "lender", "emi", "repayment", "collateral", "interest rate"],
        "required_clauses": [
            "Repayment schedule clause", "Interest rate clause", "Default clause",
            "Prepayment clause", "Security / collateral clause",
        ],
    },
    "sale_agreement": {
        "label": "Sale Agreement",
        "keywords": ["sale", "purchase", "buyer", "seller", "payment", "delivery", "goods"],
        "required_clauses": [
            "Payment terms clause", "Delivery clause", "Warranty clause",
            "Dispute resolution clause", "Force majeure clause",
        ],
    },
    "service_agreement": {
        "label": "Service Agreement",
        "keywords": ["service", "client", "vendor", "deliverable", "milestone", "fee", "scope of work"],
        "required_clauses": [
            "Scope of work clause", "Payment terms clause", "Confidentiality clause",
            "Termination clause", "Liability / indemnity clause", "Intellectual property clause",
        ],
    },
    "nda": {
        "label": "Non-Disclosure Agreement",
        "keywords": ["confidential", "non-disclosure", "proprietary", "disclose", "recipient", "disclosing party"],
        "required_clauses": [
            "Definition of confidential information", "Obligations of receiving party",
            "Exclusions clause", "Term / duration clause", "Return of information clause",
        ],
    },
    "fir": {
        "label": "FIR / Police Complaint",
        "keywords": ["fir", "first information report", "complainant", "accused", "police station", "offence"],
        "required_clauses": [],
    },
    "legal_notice": {
        "label": "Legal Notice / Court Document",
        "keywords": ["summon", "notice", "court", "plaintiff", "defendant", "petition", "jurisdiction"],
        "required_clauses": [],
    },
    "unknown": {
        "label": "General Legal Document",
        "keywords": [],
        "required_clauses": [
            "Termination clause", "Dispute resolution clause", "Governing law clause",
        ],
    },
}


def detect_document_type(text: str) -> tuple[str, str, int]:
    """Copied verbatim from backend/document_analyzer.py::detect_document_type
    (lines 357-374)."""
    lower = text.lower()
    scores = {}
    for key, cfg in DOCUMENT_TYPES.items():
        if key == "unknown" or not cfg["keywords"]:
            continue
        hits = sum(1 for kw in cfg["keywords"] if kw in lower)
        if hits:
            scores[key] = hits / len(cfg["keywords"])

    if not scores:
        return "unknown", DOCUMENT_TYPES["unknown"]["label"], 40

    best_key = max(scores, key=scores.get)
    confidence = min(int(scores[best_key] * 100), 97)
    if confidence < 20:
        return "unknown", DOCUMENT_TYPES["unknown"]["label"], 40
    return best_key, DOCUMENT_TYPES[best_key]["label"], confidence


def extract_legal_sections(text: str) -> list[str]:
    """Copied verbatim from backend/document_analyzer.py::extract_legal_sections
    (lines 735-750)."""
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


# ── Copied from backend/lex_validator.py's SectionExtractor (lines 66-128) ──
# Extracts (act, section) pairs in the exact shape build_ipc_bns_mapping.py
# and runners/ipc_bns_mapping.py expect (e.g. ("IPC", "302")), so corpus
# citations can be cross-referenced against the SAME merged mapping table.
_SECTION_PATTERNS = [
    (r'Sections?\s+([\d,\s]+?)\s+(?:and|&)?\s*(\d+)?\s+(IPC|CrPC|IEA)', "multi"),
    (r'Section\s+(\d+[A-Z]?(?:\(\d+\))?)\s+(IPC|CrPC|IEA)', "single"),
    (r'(IPC|CrPC|IEA)\s+(\d+[A-Z]?(?:\(\d+\))?)', "short"),
    (r'(IPC|CrPC|IEA):\s+(\d+[A-Z]?(?:\(\d+\))?)', "short"),
    (r'Section\s+(65B)\s+(?:of\s+the\s+)?(?:Indian\s+)?(?:Evidence\s+Act|IEA)', "iea65b"),
    (r'under\s+section\s+(\d+[A-Z]?(?:\(\d+\))?)\s+(IPC|CrPC|IEA)', "single"),
]


def extract_ipc_style_references(text: str) -> list[tuple[str, str]]:
    """Same regex family as backend/lex_validator.py::SectionExtractor.extract,
    reimplemented as a single function (the original is a class with
    per-pattern bound methods; behavior is equivalent)."""
    references: list[tuple[str, str]] = []
    seen = set()
    for pattern, kind in _SECTION_PATTERNS:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            try:
                if kind == "multi":
                    act = m.group(3)
                    numbers = re.findall(r'\b(\d+)\b', m.group(0))
                    pairs = [(act, num) for num in numbers]
                elif kind == "single":
                    pairs = [(m.group(2), m.group(1))]
                elif kind == "short":
                    pairs = [(m.group(1), m.group(2))]
                elif kind == "iea65b":
                    pairs = [("IEA", "65B")]
                else:
                    pairs = []
                for act, section in pairs:
                    key = f"{act} {section}"
                    if key not in seen:
                        seen.add(key)
                        references.append((act, section))
            except Exception:
                continue
    return references


# ── Generic entity heuristics — NOT copied from production (no equivalent
# exists there); simple, clearly-labeled regexes, not an NLP model. ──
_DATE_RE = re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b')
_MOBILE_RE = re.compile(r'\b(?:\+?91[-\s]?)?[6-9]\d{9}\b')
_MONEY_RE = re.compile(r'(?:₹|Rs\.?|INR)\s?[\d,]+(?:\.\d+)?', re.IGNORECASE)


def extract_entities(text: str) -> dict[str, list[str]]:
    """Best-effort regex entity extraction. Deliberately narrow — dates,
    mobile numbers, monetary amounts — categories where a regex has high
    precision. NOT attempting free-form name/address extraction, which
    would need an NER model this pipeline doesn't have access to
    (offline, no LLM); a wrong extracted "entity" would be exactly the
    kind of fabricated ground truth this phase must not produce."""
    return {
        "dates": sorted(set(_DATE_RE.findall(text)))[:10],
        "mobile_numbers": sorted(set(_MOBILE_RE.findall(text)))[:5],
        "monetary_amounts": sorted(set(_MONEY_RE.findall(text)))[:10],
    }


def detect_missing_clauses_fallback(text: str, type_key: str) -> list[str]:
    """Copied from backend/document_analyzer.py::detect_missing_clauses's
    OWN non-LLM fallback branch (lines 564-573 — the code path it takes
    when the Groq JSON parse comes back empty): a clause counts as
    present if any word longer than 3 chars from its name (stripped of
    the word "clause") appears in the document text. Returns the NAMES
    of clauses judged absent, matching the shape
    DocumentAnalysisRecord.expected_missing_clauses expects."""
    required = DOCUMENT_TYPES.get(type_key, DOCUMENT_TYPES["unknown"])["required_clauses"]
    if not required:
        return []
    lower = text.lower()
    missing = []
    for clause in required:
        kws = [w for w in clause.lower().replace(" clause", "").split() if len(w) > 3]
        present = any(kw in lower for kw in kws)
        if not present:
            missing.append(clause)
    return missing


def extractive_summary(text: str, max_chars: int = 400) -> str:
    """Extractive, not abstractive: returns the first meaningful paragraph
    of real document text, verbatim. No LLM is used to phrase or compress
    this — it is a direct quotation, so it can never assert something the
    source document didn't literally say."""
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 60]
    candidate = paragraphs[0] if paragraphs else text.strip()
    candidate = re.sub(r'\s+', ' ', candidate)
    return candidate[:max_chars]
