"""
M2 — RAG Engine: Ingestion Pipeline
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

Reads statute PDFs from data/statutes/, chunks them, embeds via Colab /embed
endpoint (ngrok), and stores in ChromaDB.

Run once from project root:
    python modules/m2_rag/ingest.py
"""

import os, sys, json, hashlib

# ── Path setup (works from any CWD) ────────────────────────────────────────────
_THIS_DIR    = os.path.dirname(os.path.abspath(__file__))   # modules/m2_rag/
_ROOT        = os.path.dirname(os.path.dirname(_THIS_DIR))  # project root
_BACKEND_DIR = os.path.join(_ROOT, "backend")
for _p in (_BACKEND_DIR, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fitz       # PyMuPDF
import chromadb
from tqdm import tqdm

# Import local_models eagerly so we fail fast with a clear message
try:
    from local_models import embed_texts as _colab_embed
except ModuleNotFoundError:
    raise SystemExit(
        f"[INGEST] ERROR: Cannot import local_models.\n"
        f"  backend dir: {_BACKEND_DIR}\n"
        f"  Make sure local_models.py exists in backend/ and colab_config.py is set."
    )

# ── Config ─────────────────────────────────────────────────────────────────────
PDF_DIR       = os.path.join(_ROOT, "data", "statutes")
CHROMA_DIR    = os.path.join(_ROOT, "data", "chromadb")
COLLECTION    = "nyayasetu_legal"
CHUNK_SIZE    = 512
CHUNK_OVERLAP = 50
EMBED_BATCH   = 32   # Colab /embed handles batching server-side

STATUTE_META = {
    "BNS.pdf":      {"act": "Bharatiya Nyaya Sanhita 2023",            "short": "BNS"},
    "BNSS.pdf":     {"act": "Bharatiya Nagarik Suraksha Sanhita 2023", "short": "BNSS"},
    "BSA.pdf":      {"act": "Bharatiya Sakshya Adhiniyam 2023",        "short": "BSA"},
    "ipc_bns.pdf":  {"act": "IPC to BNS Mapping Reference",           "short": "IPC_BNS"},
}


# ── Text extraction ─────────────────────────────────────────────────────────────
def extract_text(pdf_path: str) -> list[dict]:
    doc   = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text").strip()
        if text:
            pages.append({"page": i + 1, "text": text})
    doc.close()
    print(f"  Extracted {len(pages)} pages with text")
    return pages


# ── Simple chunker (no langchain dependency) ────────────────────────────────────
def chunk_pages(pages: list[dict], filename: str) -> list[dict]:
    meta   = STATUTE_META.get(filename, {"act": filename, "short": filename})
    chunks = []
    for page_data in pages:
        text = page_data["text"]
        # Split into chunks of ~CHUNK_SIZE chars with CHUNK_OVERLAP
        start = 0
        j     = 0
        while start < len(text):
            end   = min(start + CHUNK_SIZE, len(text))
            chunk = text[start:end].strip()
            if len(chunk) > 50:  # skip tiny fragments
                cid = hashlib.md5(
                    f"{filename}_{page_data['page']}_{j}_{chunk[:30]}".encode()
                ).hexdigest()
                chunks.append({
                    "id":   cid,
                    "text": chunk,
                    "metadata": {
                        "source": filename,
                        "act":    meta["act"],
                        "short":  meta["short"],
                        "page":   str(page_data["page"]),
                        "chunk":  str(j),
                    }
                })
            start += CHUNK_SIZE - CHUNK_OVERLAP
            j     += 1
    return chunks


# ── Embed via Colab /embed (ngrok) ──────────────────────────────────────────────
def embed_batch(texts: list[str]) -> list[list[float]]:
    return _colab_embed(texts)


# ── Main ingestion ──────────────────────────────────────────────────────────────
def ingest_all():
    os.makedirs(CHROMA_DIR, exist_ok=True)
    client     = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine"}
    )
    print(f"[INGEST] ChromaDB ready — existing docs: {collection.count()}")

    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]
    if not pdf_files:
        print(f"[WARN] No PDFs found in {PDF_DIR}")
        return

    print(f"[INGEST] Found {len(pdf_files)} PDFs: {pdf_files}\n")

    for filename in pdf_files:
        path = os.path.join(PDF_DIR, filename)
        print(f"[PROCESSING] {filename}")

        pages  = extract_text(path)
        chunks = chunk_pages(pages, filename)
        print(f"  Total chunks: {len(chunks)}")

        # Skip already-indexed chunks
        existing_ids = set(collection.get(ids=[c["id"] for c in chunks])["ids"])
        new_chunks   = [c for c in chunks if c["id"] not in existing_ids]
        print(f"  New chunks to embed: {len(new_chunks)}")

        if not new_chunks:
            print(f"  [SKIP] {filename} already fully indexed.\n")
            continue

        # Embed in batches and upsert
        for i in tqdm(range(0, len(new_chunks), EMBED_BATCH),
                      desc=f"  Embedding {filename}"):
            batch     = new_chunks[i : i + EMBED_BATCH]
            texts     = [c["text"]     for c in batch]
            ids       = [c["id"]       for c in batch]
            metadatas = [c["metadata"] for c in batch]

            try:
                embeddings = embed_batch(texts)
                collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                )
            except Exception as e:
                print(f"\n  [ERROR] Batch {i//EMBED_BATCH + 1} failed: {e}")
                print("  Make sure your Colab ngrok server is running!")
                raise

        # Emoji removed deliberately — can raise UnicodeEncodeError on
        # Windows' default console codepage, crashing the script on its
        # last line after ingestion already succeeded. Message unchanged.
        print(f"  Done. ChromaDB total: {collection.count()}\n")

    # Write manifest
    manifest = {
        "collection": COLLECTION,
        "total_docs": collection.count(),
        "files": pdf_files,
    }
    with open(os.path.join(CHROMA_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[DONE] ChromaDB total: {collection.count()} chunks across {len(pdf_files)} files")
    print(f"[DONE] Manifest written to {CHROMA_DIR}/manifest.json")


if __name__ == "__main__":
    print("=" * 60)
    print("  NYAYA-SETU — Statute PDF Ingestion")
    print("  Uses Colab /embed endpoint via ngrok")
    print("=" * 60)
    print()
    ingest_all()
