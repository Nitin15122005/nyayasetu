"""
M2 — RAG Engine: Query + Generation  [GPU-ACCELERATED]
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

GPU usage:
  - Bi-encoder  (MuRIL multilingual) → GPU  ~300 MB VRAM
  - Cross-encoder (ms-marco)         → GPU  ~90 MB VRAM
  - LLM                              → Groq Cloud API (no local GPU needed)

Embedding model loaded from hf_models/embedding_model (MuRIL — handles Hindi/Marathi natively).

ARCHIVED — never imported by any live entry point. Superseded by
backend/lex_validator.py::RAGMapping + modules/m2_rag/ingest.py, which query
the same data/chromadb collection via the Colab-hosted /embed endpoint
(NyayaSetu_Final_Corrected.ipynb — multilingual MiniLM-L12-v2, 384-dim).
This file loads a local MuRIL encoder instead, which is a different vector
space than the one that populated that collection — so even if wired in
as-is, its query embeddings would not be comparable to the stored vectors.
Kept for reference rather than deleted.
"""

import os, sys, json, re
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
# Add backend/ to sys.path so local_models.py is importable
_BACKEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import chromadb
import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
from pydantic import BaseModel, Field
from groq import Groq
from dotenv import load_dotenv
from gpu_utils import DEVICE, print_gpu_status, clear_gpu_cache

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
# Local MuRIL multilingual embedding model — handles Hindi/Marathi natively (no translation)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EMBED_MODEL  = os.path.join(_PROJECT_ROOT, "hf_models", "embedding_model")
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"   # downloaded from HF Hub on first use

CHROMA_DIR      = "data/chromadb"
COLLECTION      = "nyayasetu_legal"
RETRIEVAL_TOP_K = 20
RERANK_TOP_N    = 3
GROQ_MODEL      = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# ── Groq client ────────────────────────────────────────────────────────────────
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── Pydantic output schema ─────────────────────────────────────────────────────
class FIRComplaint(BaseModel):
    complainant_name:       str
    incident_description:   str
    applicable_sections:    list[str]
    section_explanations:   list[str]
    relief_sought:          str
    recommended_next_steps: list[str]
    legal_disclaimer:       str = (
        "This is an AI-generated legal triage. "
        "Consult a qualified advocate before filing."
    )


# ── RAG Engine ─────────────────────────────────────────────────────────────────
class NyayaSetuRAG:

    def __init__(self):
        # Bi-encoder on GPU (or CPU fallback)
        print(f"[RAG] Loading bi-encoder on {DEVICE}...")
        try:
            self.embedder = SentenceTransformer(
                EMBED_MODEL, device=str(DEVICE), local_files_only=True
            )
            print_gpu_status("bi-encoder loaded")
        except Exception as _e:
            print(f"[RAG] ⚠️  Local embedding model failed ({_e}). Falling back to all-MiniLM-L6-v2...")
            self.embedder = SentenceTransformer("all-MiniLM-L6-v2", device=str(DEVICE))
            print("[RAG] Fallback bi-encoder loaded.")

        # Cross-encoder on GPU
        print(f"[RAG] Loading cross-encoder on {DEVICE}...")
        import torch
        if DEVICE.type == "cuda":
            torch.cuda.set_device(DEVICE)
        self.reranker = CrossEncoder(RERANK_MODEL, max_length=512, device=str(DEVICE))
        print_gpu_status("cross-encoder loaded")

        # ChromaDB
        print("[RAG] Connecting to ChromaDB...")
        self.client     = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = self.client.get_collection(COLLECTION)
        print(f"[RAG] ChromaDB docs: {self.collection.count()}")

        # BM25
        print("[RAG] Building BM25 index in RAM...")
        self._build_bm25()

        # Groq Cloud LLM
        print(f"[RAG] Groq LLM: {GROQ_MODEL} (cloud API)")
        self._verify_groq()

    def _build_bm25(self):
        result          = self.collection.get(include=["documents", "metadatas"])
        self._all_docs  = result["documents"]
        self._all_ids   = result["ids"]
        self._all_metas = result["metadatas"]
        tokenized       = [d.lower().split() for d in self._all_docs]
        self.bm25       = BM25Okapi(tokenized)
        print(f"[RAG] BM25 index: {len(self._all_docs)} docs")

    def _verify_groq(self):
        try:
            # Quick test to verify API key works
            response = groq_client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": "Say OK"}],
                max_tokens=5,
            )
            print(f"[RAG] ✅ Groq API verified — model '{GROQ_MODEL}' ready.")
        except Exception as e:
            print(f"[RAG] ⚠️  Groq API check failed: {e} — will try anyway.")

    def _hybrid_retrieve(self, query: str) -> list[dict]:
        # Semantic search on GPU
        q_emb = self.embedder.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        ).tolist()

        sem = self.collection.query(
            query_embeddings=q_emb,
            n_results=min(RETRIEVAL_TOP_K, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        sem_docs   = sem["documents"][0]
        sem_ids    = sem["ids"][0]
        sem_metas  = sem["metadatas"][0]
        sem_scores = [1 - d for d in sem["distances"][0]]

        # BM25 keyword search on CPU
        bm25_all  = self.bm25.get_scores(query.lower().split())
        top_idx   = np.argsort(bm25_all)[::-1][:RETRIEVAL_TOP_K]
        bm25_max  = bm25_all[top_idx[0]] if bm25_all[top_idx[0]] > 0 else 1.0
        bm25_hits = {self._all_ids[i]: bm25_all[i] / bm25_max for i in top_idx}

        # Merge scores
        merged = {}
        for i, did in enumerate(sem_ids):
            merged[did] = {
                "text":     sem_docs[i],
                "metadata": sem_metas[i],
                "score":    0.5 * sem_scores[i] + 0.5 * bm25_hits.get(did, 0.0),
            }
        for did, bm_score in bm25_hits.items():
            if did not in merged:
                idx = self._all_ids.index(did)
                merged[did] = {
                    "text":     self._all_docs[idx],
                    "metadata": self._all_metas[idx],
                    "score":    0.5 * bm_score,
                }

        return sorted(merged.values(), key=lambda x: x["score"], reverse=True)[:RETRIEVAL_TOP_K]

    def _rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        pairs  = [(query, c["text"]) for c in candidates]
        scores = self.reranker.predict(pairs, show_progress_bar=False)
        for i, c in enumerate(candidates):
            c["rerank_score"] = float(scores[i])
        return sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)[:RERANK_TOP_N]

    def _build_prompt(self, query: str, chunks: list[dict]) -> str:
        ctx = "\n\n---\n\n".join(
            f"[Source {i+1}: {c['metadata'].get('act','')} | p.{c['metadata'].get('page','')}]\n{c['text']}"
            for i, c in enumerate(chunks)
        )
        return f"""You are Nyaya-Setu, an Indian legal assistant. Answer using ONLY the context below.

STRICT RULES:
1. Use ONLY information from the CONTEXT. Never invent section numbers.
2. Cite exact Act name and section number from context.
3. Write in simple language a non-lawyer understands.
4. Output ONLY a raw JSON object. No explanation, no markdown, no code fences.
5. Start your response with {{ and end with }}. Nothing before or after.

CONTEXT:
{ctx}

QUERY: {query}

Output this exact JSON structure with all fields filled:
{{
  "complainant_name": "Unknown (to be filled by user)",
  "incident_description": "describe the incident from the query in 1-2 sentences",
  "applicable_sections": ["Act Name Section Number"],
  "section_explanations": ["plain English explanation of each section"],
  "relief_sought": "what the complainant wants police to do",
  "recommended_next_steps": ["Step 1: go to nearest police station", "Step 2: bring ID proof and evidence"],
  "legal_disclaimer": "This is an AI-generated legal triage. Consult a qualified advocate before filing."
}}"""

    def _call_llm(self, prompt: str) -> str:
        response = groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=4096,
        )
        return response.choices[0].message.content

    def _parse(self, raw: str, complainant_name: str) -> FIRComplaint:
        # Clean up common LLM formatting issues
        raw = re.sub(r"```json\s*", "", raw)
        raw = re.sub(r"```\s*",     "", raw)
        raw = raw.strip()

        # Extract JSON object if there's extra text around it
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)

        # Fix trailing commas (common LLM mistake)
        raw = re.sub(r',\s*}', '}', raw)
        raw = re.sub(r',\s*]', ']', raw)

        # Fix unescaped quotes inside strings (basic fix)
        try:
            data = json.loads(raw)
            if complainant_name != "Unknown":
                data["complainant_name"] = complainant_name
            return FIRComplaint(**data)
        except Exception as e:
            print(f"[WARN] JSON parse failed: {e}")
            print(f"[WARN] Raw response was:\n{raw[:300]}")
            # Try to extract useful info even from broken JSON
            sections = re.findall(r'"([A-Z][^"]*Section[^"]*)"', raw)
            steps    = re.findall(r'"(Step \d+[^"]*)"', raw)
            return FIRComplaint(
                complainant_name=complainant_name,
                incident_description=query if hasattr(self, '_last_query') else "See raw response",
                applicable_sections=sections if sections else ["Could not parse — please retry"],
                section_explanations=["Response parsing failed — check raw output above"],
                relief_sought="File complaint at nearest police station",
                recommended_next_steps=steps if steps else ["Step 1: Visit nearest police station with your ID"],
            )

    def query(self, user_query: str, complainant_name: str = "Unknown") -> FIRComplaint:
        self._last_query = user_query
        print(f"\n[RAG] Query: {user_query[:80]}")

        candidates = self._hybrid_retrieve(user_query)
        print(f"[RAG] Stage1: {len(candidates)} candidates")

        top_chunks = self._rerank(user_query, candidates)
        print("[RAG] Stage2 top chunks:")
        for i, c in enumerate(top_chunks):
            m = c["metadata"]
            print(f"  [{i+1}] {m.get('act','')} p.{m.get('page','')} rerank={c['rerank_score']:.3f}")

        print_gpu_status("before LLM call")
        prompt = self._build_prompt(user_query, top_chunks)
        raw    = self._call_llm(prompt)
        print(f"[RAG] LLM response: {len(raw)} chars")
        print(f"[RAG] Raw LLM output: {raw}")

        return self._parse(raw, complainant_name)


# ── Singleton ──────────────────────────────────────────────────────────────────
_instance = None
def get_rag_engine() -> NyayaSetuRAG:
    global _instance
    if _instance is None:
        _instance = NyayaSetuRAG()
    return _instance


# ── CLI test ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    rag = get_rag_engine()
    tests = [
        "My phone was snatched by two men on a bike near Andheri station.",
        "Someone is sending me threatening WhatsApp messages and demanding money.",
        "My landlord has locked my flat without notice and kept my belongings.",
    ]
    for q in tests:
        r = rag.query(q)
        print(f"\n{'='*55}")
        print(f"Q: {q}")
        print(f"Sections: {r.applicable_sections}")
        print(f"Steps:    {r.recommended_next_steps[:2]}")
        print(f"Relief:   {r.relief_sought}")