"""
document_analyzer.py — Core Document Analysis Engine
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

Handles:
  1.  PDF/image text extraction
  2.  Clause segmentation
  3.  Clause risk scoring (Safe/Caution/High Risk/Illegal)
  4.  Plain-language document summary
  5.  Confidence scoring on every output
  6.  IndianKanoon case law retrieval
  7.  RAG Q&A over uploaded document (multi-turn)
  NEW:
  8.  Document type detection with confidence %
  9.  Party obligation map
  10. Missing clauses detector
  11. Plain-English rewrite for High Risk / Illegal clauses (safer_version)
  12. Key numbers extractor (rupees, dates, %, durations)
  13. Limitation period / deadline alerts
  14. Suggested questions (6 per document)
  15. Signature verdict (Sign / Negotiate / Do Not Sign)
"""

import os, sys, re, json
import requests as req
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz          # PyMuPDF
import ollama
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
from dotenv import load_dotenv
from gpu_utils import DEVICE

load_dotenv()

OLLAMA_MODEL         = os.getenv("OLLAMA_MODEL", "llama3")
INDIANKANOON_API_KEY = os.getenv("INDIANKANOON_API_KEY", "")
EMBED_MODEL = r"C:\Users\Nitin Sharma\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\8b3219a92973c328a8e22fadcfa821b5dc75636a"


# ─────────────────────────────────────────────────────────────
# Document type definitions — required clauses per type
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
    risk_level:    str           # Safe / Caution / High Risk / Illegal
    risk_score:    float         # 0.0–1.0
    explanation:   str
    confidence:    float
    suggestion:    str
    safer_version: Optional[str] = None   # NEW: rewrite for High Risk / Illegal

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
    type:  str    # monetary / date / percentage / duration / other

class Deadline(BaseModel):
    description: str
    deadline:    str
    consequence: Optional[str] = None

class SignatureVerdict(BaseModel):
    verdict: str   # "Safe to Sign" / "Negotiate First" / "Do Not Sign"
    color:   str   # green / orange / red
    reason:  str

class DocumentAnalysis(BaseModel):
    document_name:       str
    document_type:       str
    document_type_key:   str    # NEW: e.g. "rental_agreement"
    type_confidence:     int    # NEW: 0–100
    total_clauses:       int
    summary:             str
    risk_distribution:   dict
    clauses:             list[ClauseAnalysis]
    overall_risk:        str
    compliance_score:    int
    case_laws:           list[dict]
    recommendations:     list[str]
    # NEW fields
    party_obligations:   list[PartyObligation]
    missing_clauses:     list[MissingClause]
    key_numbers:         list[KeyNumber]
    deadlines:           list[Deadline]
    suggested_questions: list[str]
    signature_verdict:   SignatureVerdict

class QAResponse(BaseModel):
    question:   str
    answer:     str
    confidence: float
    sources:    list[str]
    disclaimer: str


# ─────────────────────────────────────────────────────────────
# Text extraction
# ─────────────────────────────────────────────────────────────
def extract_text(file_bytes: bytes, filename: str) -> str:
    fname = filename.lower()
    if fname.endswith(".pdf"):
        doc  = fitz.open(stream=file_bytes, filetype="pdf")
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
        return text.strip()
    elif any(fname.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
        try:
            import pytesseract
            from PIL import Image
            import io
            img = Image.open(io.BytesIO(file_bytes))
            return pytesseract.image_to_string(img).strip()
        except ImportError:
            doc  = fitz.open(stream=file_bytes, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text.strip()
    return ""


# ─────────────────────────────────────────────────────────────
# Clause segmentation
# ─────────────────────────────────────────────────────────────
def segment_clauses(text: str) -> list[str]:
    numbered = re.split(
        r'\n(?=(?:\d+[\.\)]\s)|(?:Clause\s+\d+)|(?:Section\s+\d+)|(?:[A-Z]\.\s))',
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
# Document type detection with confidence  (ENHANCED)
# ─────────────────────────────────────────────────────────────
def detect_document_type(text: str) -> tuple[str, str, int]:
    """Returns (type_key, label, confidence_pct)"""
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


# ─────────────────────────────────────────────────────────────
# LLM helpers
# ─────────────────────────────────────────────────────────────
def call_llm(prompt: str, temperature: float = 0.1) -> str:
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature, "num_ctx": 4096, "num_gpu": 99},
    )
    return response["message"]["content"].strip()


def parse_json_response(raw: str, fallback):
    """Strip markdown fences and extract the first JSON array or object."""
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
# Clause risk scoring  (ENHANCED — adds safer_version)
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
  "safer_version": "if risk_level is High Risk or Illegal, write a fairer rewrite the user can propose to the other party. Otherwise null."
}}

Risk guide:
- Safe: standard, fair language
- Caution: unusual or one-sided but not illegal
- High Risk: significantly unfair, likely challengeable in court
- Illegal: violates Indian law (Consumer Protection Act, Contract Act, BNS 2023, labour laws)"""

    raw  = call_llm(prompt)
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
# Document summary
# ─────────────────────────────────────────────────────────────
def summarize_document(text: str, doc_type: str) -> str:
    prompt = f"""You are an Indian legal assistant. Summarize this {doc_type} in plain English for a common person.
Under 120 words. Cover: what it is, who the parties are, key obligations, and any major risks.
No headings or bullet points.

DOCUMENT (first 2000 chars):
{text[:2000]}"""
    return call_llm(prompt, temperature=0.2)


# ─────────────────────────────────────────────────────────────
# Party obligation map  (NEW)
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
# Missing clauses detector  (NEW)
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
  {{"clause": "Termination clause",   "present": true,  "why_important": "Defines how either party can exit the agreement."}},
  {{"clause": "Notice period clause", "present": false, "why_important": "Protects you from sudden eviction without warning."}}
]

Return ONLY valid JSON array.

DOCUMENT:
{text[:3000]}"""

    raw  = call_llm(prompt, temperature=0.1)
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

    # Fallback: keyword-based detection if LLM returned nothing
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
# Key numbers extractor  (NEW)
# ─────────────────────────────────────────────────────────────
def extract_key_numbers(text: str) -> list[KeyNumber]:
    prompt = f"""Extract every monetary amount, date, percentage, and duration from this legal document.

Return a JSON array:
[
  {{"label": "Security Deposit", "value": "₹50,000",     "type": "monetary"}},
  {{"label": "Monthly Rent",     "value": "₹15,000",     "type": "monetary"}},
  {{"label": "Notice Period",    "value": "30 days",      "type": "duration"}},
  {{"label": "Start Date",       "value": "1 Jan 2025",   "type": "date"}},
  {{"label": "Late Fee",         "value": "2% per month", "type": "percentage"}}
]

Types: monetary / date / percentage / duration / other
Extract EVERY number — miss nothing.
Return ONLY valid JSON array.

DOCUMENT:
{text[:4000]}"""

    raw  = call_llm(prompt, temperature=0.0)
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
    return results


# ─────────────────────────────────────────────────────────────
# Deadline / limitation period alerts  (NEW)
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

    raw  = call_llm(prompt, temperature=0.0)
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
# Suggested questions  (NEW)
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
# Signature verdict  (NEW)
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
            reason=f"Contains {illegal_count} illegal clause(s) that violate Indian law. Seek legal counsel before proceeding.",
        )
    if high_risk_count >= 3 or (high_risk_count >= 1 and missing_count >= 2):
        return SignatureVerdict(
            verdict="Negotiate First",
            color="orange",
            reason=f"{high_risk_count} high-risk clause(s) and {missing_count} missing standard protection(s) need to be resolved first.",
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
    if illegal > 0:              return "Critical"
    if high >= 2:                return "High"
    if high == 1 or caution >= 3: return "Moderate"
    return "Safe"


# ─────────────────────────────────────────────────────────────
# IndianKanoon
# ─────────────────────────────────────────────────────────────
def fetch_case_laws(query: str, doc_type: str) -> list[dict]:
    if not INDIANKANOON_API_KEY:
        return [{
            "title":   "IndianKanoon API key not configured",
            "summary": "Add INDIANKANOON_API_KEY to your .env file.",
            "url":     "https://indiankanoon.org",
            "court":   "",
            "year":    "",
        }]
    try:
        response = req.post(
            "https://api.indiankanoon.org/search/",
            data={"formInput": f"{query} {doc_type} India", "pagenum": 0},
            headers={
                "Authorization": f"Token {INDIANKANOON_API_KEY}",
                "Content-Type":  "application/x-www-form-urlencoded",
            },
            timeout=15,
        )
        response.raise_for_status()
        data    = response.json()
        results = []
        for doc in data.get("docs", [])[:3]:
            summary = call_llm(
                f"Summarize in 2-3 plain English sentences:\n{doc.get('headline','')} {doc.get('doc','')[:500]}\nWrite only the summary.",
                temperature=0.1,
            )
            results.append({
                "title":   doc.get("title", "Untitled"),
                "summary": summary,
                "url":     f"https://indiankanoon.org/doc/{doc.get('tid', '')}",
                "court":   doc.get("docsource", ""),
                "year":    doc.get("publishdate", "")[:4] if doc.get("publishdate") else "",
            })
        return results
    except Exception as e:
        print(f"[KANOON] API error: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# Document RAG — multi-turn Q&A  (ENHANCED)
# ─────────────────────────────────────────────────────────────
class DocumentRAG:
    """In-memory vector store for a single uploaded document. Supports multi-turn conversation."""

    def __init__(self):
        self.embedder   = SentenceTransformer(EMBED_MODEL, device=str(DEVICE))
        self.chunks:     list[str]  = []
        self.embeddings             = []
        self.doc_type:   str        = "Legal Document"
        # Multi-turn: store full conversation history
        self.history:    list[dict] = []   # [{"role": "user"/"assistant", "content": "..."}]

    def index(self, clauses: list[str], doc_type: str = "Legal Document"):
        self.chunks     = clauses
        self.doc_type   = doc_type
        self.embeddings = self.embedder.encode(
            clauses, normalize_embeddings=True, convert_to_numpy=True
        )
        print(f"[DocRAG] Indexed {len(clauses)} chunks for {doc_type}")

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        if not self.chunks:
            return []
        import numpy as np
        q_emb   = self.embedder.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        scores  = (self.embeddings @ q_emb.T).flatten()
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [self.chunks[i] for i in top_idx]

    def answer(self, question: str) -> QAResponse:
        """Answer using RAG + multi-turn conversation history."""
        print(f"[DocRAG.answer] Question: {question[:100]}...")
        print(f"[DocRAG.answer] Chunks available: {len(self.chunks)}")
        
        if not self.chunks:
            print(f"[DocRAG.answer] No chunks indexed!")
            return QAResponse(
                question=question,
                answer="No document content available to answer this question.",
                confidence=0.0,
                sources=[],
                disclaimer="Please upload a document first."
            )
        
        # Retrieve relevant chunks
        relevant = self.retrieve(question)
        print(f"[DocRAG.answer] Retrieved {len(relevant)} chunks")
        
        if not relevant:
            print(f"[DocRAG.answer] No relevant chunks found")
            return QAResponse(
                question=question,
                answer="I couldn't find relevant information in the document to answer this question.",
                confidence=0.2,
                sources=[],
                disclaimer="Try rephrasing your question."
            )
        
        context = "\n\n---\n\n".join(relevant)
        
        # Build conversation history
        history_text = ""
        if self.history:
            history_text = "\n\nPREVIOUS CONVERSATION:\n"
            for turn in self.history[-6:]:
                role = "User" if turn["role"] == "user" else "Assistant"
                history_text += f"{role}: {turn['content']}\n"
            print(f"[DocRAG.answer] Using {len(self.history)} history turns")
        
        prompt = f"""You are an Indian legal assistant. Answer the question based on the document excerpts below.
    If the answer is not in the document, say "This is not specified in the document."
    Use previous conversation context if relevant to this question.

    DOCUMENT TYPE: {self.doc_type}
    DOCUMENT EXCERPTS:
    {context}
    {history_text}
    CURRENT QUESTION: {question}

    Give a clear, plain English answer in 2-4 sentences. No legal jargon."""
        
        try:
            answer = call_llm(prompt)
            print(f"[DocRAG.answer] Generated answer: {answer[:100]}...")
            
            confidence = compute_confidence(context, answer)
            
            # Store in history
            self.history.append({"role": "user", "content": question})
            self.history.append({"role": "assistant", "content": answer})
            
            disclaimer = ""
            if confidence < 0.4:
                disclaimer = "⚠️ Low confidence — consult a lawyer for certainty."
            elif confidence < 0.7:
                disclaimer = "ℹ️ Moderate confidence — verify with the original document."
            
            return QAResponse(
                question=question,
                answer=answer,
                confidence=confidence,
                sources=[c[:100] for c in relevant],
                disclaimer=disclaimer,
            )
        except Exception as e:
            print(f"[DocRAG.answer] LLM call failed: {e}")
            return QAResponse(
                question=question,
                answer=f"Error generating answer: {str(e)}",
                confidence=0.0,
                sources=[],
                disclaimer="Technical error occurred. Please try again."
            )

# ─────────────────────────────────────────────────────────────
# Main analysis pipeline
# ─────────────────────────────────────────────────────────────
def analyze_document(
    file_bytes:    bytes,
    filename:      str,
    max_clauses:   int = 15,
    type_override: Optional[str] = None,   # NEW: user can correct detected type
) -> tuple[DocumentAnalysis, DocumentRAG]:

    print(f"\n[ANALYZER] Processing: {filename}")

    # 1. Extract text
    text = extract_text(file_bytes, filename)
    if not text:
        raise ValueError("Could not extract text from document.")
    print(f"[ANALYZER] Extracted {len(text)} chars")

    # 2. Document type (with confidence)
    if type_override and type_override in DOCUMENT_TYPES:
        type_key   = type_override
        doc_type   = DOCUMENT_TYPES[type_key]["label"]
        type_conf  = 100
    else:
        type_key, doc_type, type_conf = detect_document_type(text)
    print(f"[ANALYZER] Type: {doc_type} ({type_conf}%)")

    # 3. Segment clauses
    all_clauses = segment_clauses(text)
    clauses     = all_clauses[:max_clauses]
    print(f"[ANALYZER] {len(all_clauses)} clauses found, analyzing {len(clauses)}")

    # 4. Risk score each clause (now includes safer_version)
    analyzed: list[ClauseAnalysis] = []
    for i, clause in enumerate(clauses):
        print(f"[ANALYZER] Clause {i+1}/{len(clauses)}...")
        analyzed.append(analyze_clause(clause, doc_type))

    # 5. Summary
    summary = summarize_document(text, doc_type)

    # 6. Risk distribution
    dist = {"Safe": 0, "Caution": 0, "High Risk": 0, "Illegal": 0}
    for c in analyzed:
        dist[c.risk_level] = dist.get(c.risk_level, 0) + 1

    # 7. Overall risk
    overall = compute_overall_risk(analyzed)

    # 8. IPC→BNS compliance
    try:
        from lex_validator import compute_compliance_score
        comp_score = compute_compliance_score(text)["score"]
    except Exception:
        comp_score = 75

    # 9. Case laws
    risky   = [c for c in analyzed if c.risk_level in ["High Risk", "Illegal"]]
    kw_src  = risky or [c for c in analyzed if c.risk_level == "Caution"]
    kws     = [c.explanation[:80] for c in kw_src[:2] if c.explanation and len(c.explanation) > 20]
    kanoon_q = (f"{doc_type} {' '.join(kws)}")[:200] if kws else doc_type
    case_laws = fetch_case_laws(kanoon_q, doc_type)

    # NEW 10. Party obligations
    party_obligations = extract_party_obligations(text, doc_type)

    # NEW 11. Missing clauses
    missing_clauses = detect_missing_clauses(text, type_key)

    # NEW 12. Key numbers
    key_numbers = extract_key_numbers(text)

    # NEW 13. Deadlines
    deadlines = extract_deadlines(text)

    # NEW 14. Suggested questions
    suggested_questions = generate_suggested_questions(text, doc_type)

    # NEW 15. Signature verdict
    signature_verdict = get_signature_verdict(analyzed, missing_clauses)

    # Recommendations
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

    # Index for multi-turn Q&A
    doc_rag = DocumentRAG()
    doc_rag.index(all_clauses, doc_type)

    result = DocumentAnalysis(
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
    )

    print(f"[ANALYZER] Done. Verdict: {signature_verdict.verdict}")
    return result, doc_rag