"""
document_analyzer.py — Core Document Analysis Engine
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

Handles:
  1. PDF/image text extraction
  2. Clause segmentation
  3. Clause risk scoring (Safe/Caution/High Risk/Illegal)
  4. Plain-language document summary
  5. Confidence scoring on every output
  6. IndianKanoon case law retrieval
  7. RAG Q&A over uploaded document
"""

import os, sys, re, json, time
import requests as req
from typing import Optional
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fitz          # PyMuPDF
import chromadb
import ollama
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
from dotenv import load_dotenv
from gpu_utils import DEVICE

load_dotenv()

OLLAMA_MODEL     = os.getenv("OLLAMA_MODEL", "llama3")
INDIANKANOON_API_KEY = os.getenv("INDIANKANOON_API_KEY", "")
CHROMA_DOC_DIR   = "data/doc_chromadb"   # separate from legal KB chromadb

EMBED_MODEL = r"C:\Users\Nitin Sharma\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\8b3219a92973c328a8e22fadcfa821b5dc75636a"


# ── Pydantic models ────────────────────────────────────────────────────────────
class ClauseAnalysis(BaseModel):
    clause_text:   str
    risk_level:    str        # Safe / Caution / High Risk / Illegal
    risk_score:    float      # 0.0 to 1.0
    explanation:   str        # plain English
    confidence:    float      # 0.0 to 1.0
    suggestion:    str        # what user should do about this clause

class DocumentAnalysis(BaseModel):
    document_name:    str
    document_type:    str     # Rental / Employment / Legal Notice / FIR / Other
    total_clauses:    int
    summary:          str     # plain-language summary
    risk_distribution: dict   # {"Safe": N, "Caution": N, "High Risk": N, "Illegal": N}
    clauses:          list[ClauseAnalysis]
    overall_risk:     str     # Safe / Moderate / High / Critical
    compliance_score: int     # 0-100 IPC→BNS compliance
    case_laws:        list[dict]   # from IndianKanoon
    recommendations:  list[str]

class QAResponse(BaseModel):
    question:   str
    answer:     str
    confidence: float
    sources:    list[str]    # clause texts used as sources
    disclaimer: str


# ── Text extraction ────────────────────────────────────────────────────────────
def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from PDF or image."""
    fname = filename.lower()

    if fname.endswith(".pdf"):
        doc  = fitz.open(stream=file_bytes, filetype="pdf")
        text = "\n".join(page.get_text("text") for page in doc)
        doc.close()
        return text.strip()

    elif any(fname.endswith(ext) for ext in [".jpg",".jpeg",".png",".webp"]):
        try:
            import pytesseract
            from PIL import Image
            import io
            img  = Image.open(io.BytesIO(file_bytes))
            return pytesseract.image_to_string(img).strip()
        except ImportError:
            # Fallback: use PyMuPDF to open as image
            doc  = fitz.open(stream=file_bytes, filetype="pdf")
            text = "\n".join(page.get_text() for page in doc)
            doc.close()
            return text.strip()

    return ""


# ── Clause segmentation ────────────────────────────────────────────────────────
def segment_clauses(text: str) -> list[str]:
    """
    Split document into individual clauses.
    Uses numbered clause patterns + sentence boundaries.
    """
    # Try numbered clauses first (1. / 1) / Clause 1 / Section 1)
    numbered = re.split(
        r'\n(?=(?:\d+[\.\)]\s)|(?:Clause\s+\d+)|(?:Section\s+\d+)|(?:[A-Z]\.\s))',
        text
    )
    if len(numbered) > 3:
        clauses = [c.strip() for c in numbered if len(c.strip()) > 30]
        return clauses

    # Fallback: split by double newline (paragraph boundaries)
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
    if len(paragraphs) > 2:
        return paragraphs

    # Last resort: split into ~300 char chunks
    words  = text.split()
    chunks = []
    chunk  = []
    for word in words:
        chunk.append(word)
        if len(" ".join(chunk)) > 300:
            chunks.append(" ".join(chunk))
            chunk = []
    if chunk:
        chunks.append(" ".join(chunk))
    return chunks


# ── Document type detection ────────────────────────────────────────────────────
def detect_document_type(text: str) -> str:
    text_lower = text.lower()
    if any(w in text_lower for w in ["tenancy","rent","landlord","tenant","premises","lease"]):
        return "Rental Agreement"
    if any(w in text_lower for w in ["employment","salary","employer","employee","designation","joining"]):
        return "Employment Contract"
    if any(w in text_lower for w in ["fir","first information report","complainant","accused","police station"]):
        return "FIR / Police Complaint"
    if any(w in text_lower for w in ["summon","notice","court","plaintiff","defendant","petition"]):
        return "Legal Notice / Court Document"
    if any(w in text_lower for w in ["loan","borrower","lender","emi","repayment","collateral"]):
        return "Loan Agreement"
    if any(w in text_lower for w in ["vendor","supplier","purchase order","delivery","payment terms"]):
        return "Vendor / Business Contract"
    return "Legal Document"


# ── LLM helpers ────────────────────────────────────────────────────────────────
def call_llm(prompt: str, temperature: float = 0.1) -> str:
    response = ollama.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": temperature, "num_ctx": 4096, "num_gpu": 99},
    )
    return response["message"]["content"].strip()


def compute_confidence(text: str, answer: str) -> float:
    """
    Simple confidence scoring:
    - High if answer contains specific numbers, section references, named parties
    - Low if answer is vague or contains uncertainty markers
    """
    uncertainty_markers = [
        "i'm not sure", "i don't know", "unclear", "cannot determine",
        "not specified", "ambiguous", "may or may not", "it depends"
    ]
    certainty_markers = [
        "section", "clause", "shall", "must", "required", "prohibited",
        "rs.", "₹", "days", "months", "percent", "%"
    ]

    answer_lower = answer.lower()
    uncertainty_count = sum(1 for m in uncertainty_markers if m in answer_lower)
    certainty_count   = sum(1 for m in certainty_markers   if m in answer_lower)

    base_score = 0.6
    base_score += certainty_count   * 0.05
    base_score -= uncertainty_count * 0.15

    return round(max(0.1, min(0.95, base_score)), 2)


# ── Clause risk scoring ────────────────────────────────────────────────────────
def analyze_clause(clause: str, doc_type: str) -> ClauseAnalysis:
    """Score a single clause for risk level."""
    prompt = f"""You are an Indian legal expert reviewing a {doc_type}.

Analyze this clause and respond ONLY with a JSON object — no other text:

CLAUSE:
{clause[:500]}

JSON to fill:
{{
  "risk_level": "Safe" or "Caution" or "High Risk" or "Illegal",
  "risk_score": 0.0 to 1.0 (0=safe, 1=illegal),
  "explanation": "one sentence in plain English explaining the risk or why it's safe",
  "confidence": 0.0 to 1.0,
  "suggestion": "one sentence on what the user should do about this clause"
}}

Risk guide:
- Safe: standard legal language, fair to both parties
- Caution: unusual or one-sided but not illegal — negotiate this
- High Risk: significantly unfair, may be challenged in court
- Illegal: violates Indian law (Consumer Protection Act, Contract Act, labor laws, etc.)"""

    raw = call_llm(prompt)

    # Clean JSON
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*",     "", raw).strip()
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        data = json.loads(raw)
        return ClauseAnalysis(
            clause_text=clause[:300],
            risk_level=data.get("risk_level", "Caution"),
            risk_score=float(data.get("risk_score", 0.5)),
            explanation=data.get("explanation", "Could not analyze this clause."),
            confidence=float(data.get("confidence", 0.5)),
            suggestion=data.get("suggestion", "Review with a lawyer."),
        )
    except Exception:
        return ClauseAnalysis(
            clause_text=clause[:300],
            risk_level="Caution",
            risk_score=0.5,
            explanation="Could not parse this clause automatically.",
            confidence=0.3,
            suggestion="Have this clause reviewed by a legal professional.",
        )


# ── Document summary ───────────────────────────────────────────────────────────
def summarize_document(text: str, doc_type: str) -> str:
    """Generate plain-language summary of full document."""
    prompt = f"""You are an Indian legal assistant. Summarize this {doc_type} in plain English for a common person with no legal background.

Keep it under 150 words. Cover:
1. What this document is about
2. Key obligations of each party
3. Most important risks or red flags (if any)

DOCUMENT (first 2000 chars):
{text[:2000]}

Write the summary directly — no headings, no bullet points."""

    return call_llm(prompt, temperature=0.2)


# ── Overall risk assessment ────────────────────────────────────────────────────
def compute_overall_risk(clauses: list[ClauseAnalysis]) -> str:
    if not clauses:
        return "Unknown"
    illegal_count   = sum(1 for c in clauses if c.risk_level == "Illegal")
    high_risk_count = sum(1 for c in clauses if c.risk_level == "High Risk")
    caution_count   = sum(1 for c in clauses if c.risk_level == "Caution")

    if illegal_count > 0:
        return "Critical"
    if high_risk_count >= 2:
        return "High"
    if high_risk_count == 1 or caution_count >= 3:
        return "Moderate"
    return "Safe"


# ── IndianKanoon API ───────────────────────────────────────────────────────────
def fetch_case_laws(query: str, doc_type: str) -> list[dict]:
    """
    Fetch relevant case laws from IndianKanoon API.
    Free API: https://api.indiankanoon.org
    """
    if not INDIANKANOON_API_KEY:
        # Return placeholder if no API key
        return [{
            "title":   "IndianKanoon API key not configured",
            "summary": "Add INDIANKANOON_API_KEY to your .env file. Get a free key at https://api.indiankanoon.org",
            "url":     "https://indiankanoon.org",
            "court":   "",
            "year":    "",
        }]

    try:
        # Build search query based on document type
        search_query = f"{query} {doc_type} India"
        response = req.post(
            "https://api.indiankanoon.org/search/",
            data={
                "formInput":  search_query,
                "pagenum":    0,
            },
            headers={
                "Authorization": f"Token {INDIANKANOON_API_KEY}",
                "Content-Type":  "application/x-www-form-urlencoded",
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for doc in data.get("docs", [])[:3]:   # top 3 results
            # Summarize the judgment
            summary_prompt = f"""Summarize this Indian court judgment in 2-3 plain English sentences for a common person:

{doc.get('headline', '')} {doc.get('doc', '')[:500]}

Write only the summary."""
            summary = call_llm(summary_prompt, temperature=0.1)

            results.append({
                "title":   doc.get("title",    "Untitled"),
                "summary": summary,
                "url":     f"https://indiankanoon.org/doc/{doc.get('tid', '')}",
                "court":   doc.get("docsource", ""),
                "year":    doc.get("publishdate", "")[:4] if doc.get("publishdate") else "",
            })
        return results

    except Exception as e:
        print(f"[KANOON] API error: {e}")
        return []


# ── Document ChromaDB (per-document RAG) ──────────────────────────────────────
class DocumentRAG:
    """
    In-memory vector store for a single uploaded document.
    Created fresh for each document upload.
    """
    def __init__(self):
        self.embedder  = SentenceTransformer(EMBED_MODEL, device=str(DEVICE))
        self.chunks    = []
        self.embeddings= []

    def index(self, clauses: list[str]):
        """Index document clauses for Q&A retrieval."""
        self.chunks     = clauses
        self.embeddings = self.embedder.encode(
            clauses, normalize_embeddings=True, convert_to_numpy=True
        )
        print(f"[DocRAG] Indexed {len(clauses)} chunks")

    def retrieve(self, query: str, top_k: int = 3) -> list[str]:
        """Retrieve top-k relevant clauses for a query."""
        if not self.chunks:
            return []
        import numpy as np
        q_emb   = self.embedder.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        scores  = (self.embeddings @ q_emb.T).flatten()
        top_idx = np.argsort(scores)[::-1][:top_k]
        return [self.chunks[i] for i in top_idx]

    def answer(self, question: str, doc_type: str) -> QAResponse:
        """Answer a question about the uploaded document using RAG."""
        relevant = self.retrieve(question)
        context  = "\n\n---\n\n".join(relevant)

        prompt = f"""You are an Indian legal assistant. Answer the question based ONLY on the document excerpts below.
If the answer is not in the document, say "This is not specified in the document."

DOCUMENT TYPE: {doc_type}
DOCUMENT EXCERPTS:
{context}

QUESTION: {question}

Give a clear, plain English answer in 2-4 sentences. No legal jargon."""

        answer     = call_llm(prompt)
        confidence = compute_confidence(context, answer)

        disclaimer = ""
        if confidence < 0.4:
            disclaimer = "⚠️ Low confidence — this answer may be incomplete. Consult a lawyer."
        elif confidence < 0.7:
            disclaimer = "ℹ️ Moderate confidence — verify this with the original document."

        return QAResponse(
            question=question,
            answer=answer,
            confidence=confidence,
            sources=[c[:100] for c in relevant],
            disclaimer=disclaimer,
        )


# ── Main analysis function ─────────────────────────────────────────────────────
def analyze_document(
    file_bytes:    bytes,
    filename:      str,
    max_clauses:   int = 15,
) -> tuple[DocumentAnalysis, DocumentRAG]:
    """
    Full document analysis pipeline.
    Returns DocumentAnalysis + DocumentRAG for follow-up Q&A.
    """
    print(f"\n[ANALYZER] Processing: {filename}")

    # Step 1: Extract text
    text = extract_text(file_bytes, filename)
    if not text:
        raise ValueError("Could not extract text from document.")
    print(f"[ANALYZER] Extracted {len(text)} chars")

    # Step 2: Detect type
    doc_type = detect_document_type(text)
    print(f"[ANALYZER] Document type: {doc_type}")

    # Step 3: Segment clauses
    all_clauses = segment_clauses(text)
    clauses     = all_clauses[:max_clauses]   # limit for speed
    print(f"[ANALYZER] {len(all_clauses)} clauses found, analyzing {len(clauses)}")

    # Step 4: Analyze each clause
    analyzed = []
    for i, clause in enumerate(clauses):
        print(f"[ANALYZER] Clause {i+1}/{len(clauses)}...")
        analyzed.append(analyze_clause(clause, doc_type))

    # Step 5: Summary
    summary = summarize_document(text, doc_type)

    # Step 6: Risk distribution
    dist = {"Safe": 0, "Caution": 0, "High Risk": 0, "Illegal": 0}
    for c in analyzed:
        dist[c.risk_level] = dist.get(c.risk_level, 0) + 1

    # Step 7: Overall risk
    overall = compute_overall_risk(analyzed)

    # Step 8: IPC→BNS compliance
    from lex_validator import compute_compliance_score
    compliance = compute_compliance_score(text)
    comp_score = compliance["score"]

    # Step 9: Case law retrieval
    # Build query from risky clauses
    risky_clauses = [c for c in analyzed if c.risk_level in ["High Risk", "Illegal"]]
    caution_clauses = [c for c in analyzed if c.risk_level == "Caution"]
 
    # Extract meaningful keywords from risky clause explanations (not raw text)
    keyword_sources = risky_clauses or caution_clauses
    keywords = []
    for c in keyword_sources[:3]:
        # Use explanation — it's cleaner than raw clause text
        if c.explanation and len(c.explanation) > 20:
            # Pull first 80 chars of explanation as keyword context
            keywords.append(c.explanation[:80])
 
    if keywords:
        kanoon_query = f"{doc_type} {' '.join(keywords[:2])}"
    else:
        # Fallback: doc type only — still gives relevant results
        kanoon_query = doc_type
 
    # Trim to 200 chars max (IndianKanoon query limit)
    kanoon_query = kanoon_query[:200]
    print(f"[ANALYZER] IndianKanoon query: {kanoon_query[:80]}...")
 
    case_laws = fetch_case_laws(kanoon_query, doc_type)

    # Step 10: Recommendations
    recommendations = []
    if dist["Illegal"] > 0:
        recommendations.append(f"⚠️ {dist['Illegal']} clause(s) may violate Indian law. Do not sign without legal review.")
    if dist["High Risk"] > 0:
        recommendations.append(f"🔴 {dist['High Risk']} high-risk clause(s) found. Negotiate these before signing.")
    if dist["Caution"] > 0:
        recommendations.append(f"🟡 {dist['Caution']} clause(s) need attention. Read carefully.")
    if comp_score < 70:
        recommendations.append(f"📋 Document uses obsolete IPC/CrPC sections (Score: {comp_score}/100). Request updated version.")
    if not recommendations:
        recommendations.append("✅ Document appears fair. Standard review recommended before signing.")

    # Step 11: Index for Q&A
    doc_rag = DocumentRAG()
    doc_rag.index(all_clauses)

    result = DocumentAnalysis(
        document_name=filename,
        document_type=doc_type,
        total_clauses=len(analyzed),
        summary=summary,
        risk_distribution=dist,
        clauses=analyzed,
        overall_risk=overall,
        compliance_score=comp_score,
        case_laws=case_laws,
        recommendations=recommendations,
    )

    print(f"[ANALYZER] Done. Overall risk: {overall}")
    return result, doc_rag
