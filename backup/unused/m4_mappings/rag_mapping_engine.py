"""
rag_mapping_engine.py — RAG-Based IPC → BNS Mapping
Uses the IPC-BNS PDF as a knowledge base with semantic search
"""

import os
import sys
import json
import re
import numpy as np
from typing import Dict, List, Tuple, Optional
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import fitz  # PyMuPDF
import ollama
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import chromadb
from chromadb.utils import embedding_functions

class RAGMappingEngine:
    """
    RAG-based mapping engine that uses the IPC-BNS PDF as a knowledge base
    """
    
    def __init__(self, pdf_path: str = None, use_chromadb: bool = True):
        self.pdf_path = pdf_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "statutes", "ipc_bns.pdf"
        )
        
        self.use_chromadb = use_chromadb
        self.embedder = None
        self.chunks = []
        self.chunk_embeddings = None
        self.collection = None
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")
        
        # Initialize embedding model
        self.init_embedder()
        
        # Load and index the PDF
        self.load_and_index_pdf()
    
    def init_embedder(self):
        """Initialize the sentence transformer model"""
        try:
            model_path = r"C:\Users\Nitin Sharma\.cache\huggingface\hub\models--sentence-transformers--all-MiniLM-L6-v2\snapshots\8b3219a92973c328a8e22fadcfa821b5dc75636a"
            
            if os.path.exists(model_path):
                self.embedder = SentenceTransformer(model_path, device="cuda")
                print("[RAGMapping] Embedder loaded")
            else:
                print("[RAGMapping] Using default sentence-transformers model")
                self.embedder = SentenceTransformer('all-MiniLM-L6-v2', device="cuda")
        except Exception as e:
            print(f"[RAGMapping] Error loading embedder: {e}")
            self.embedder = None
    
    def load_and_index_pdf(self):
        """Load PDF and create searchable index"""
        print(f"[RAGMapping] Loading PDF: {self.pdf_path}")
        
        if not os.path.exists(self.pdf_path):
            print(f"[RAGMapping] PDF not found at {self.pdf_path}")
            self.create_fallback_index()
            return
        
        try:
            # Extract text with page numbers
            doc = fitz.open(self.pdf_path)
            all_chunks = []
            
            for page_num, page in enumerate(doc):
                text = page.get_text()
                
                # Split into meaningful chunks (by sections)
                chunks = self.split_into_chunks(text, page_num)
                all_chunks.extend(chunks)
            
            doc.close()
            
            # Store chunks
            self.chunks = all_chunks
            print(f"[RAGMapping] Created {len(self.chunks)} chunks from PDF")
            
            # Create embeddings
            if self.embedder:
                self.create_embeddings()
            
            # Also try to use ChromaDB if available
            if self.use_chromadb:
                self.index_with_chromadb()
            
        except Exception as e:
            print(f"[RAGMapping] Error loading PDF: {e}")
            self.create_fallback_index()
    
    def split_into_chunks(self, text: str, page_num: int) -> List[Dict]:
        """Intelligently split text into meaningful chunks"""
        chunks = []
        
        # Split by sections (look for patterns like "IPC XXX" or "BNS XXX")
        lines = text.split('\n')
        current_chunk = []
        current_sections = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if this line contains section information
            ipc_match = re.search(r'IPC\s+(\d+[A-Z]?(?:\(\d+\))?)', line, re.IGNORECASE)
            bns_match = re.search(r'BNS\s+(\d+[A-Z]?(?:\(\d+\))?)', line, re.IGNORECASE)
            
            if ipc_match or bns_match:
                # Save previous chunk if it exists
                if current_chunk:
                    chunks.append({
                        "text": "\n".join(current_chunk),
                        "page": page_num,
                        "sections": current_sections,
                        "has_ipc": bool(current_sections)
                    })
                
                # Start new chunk
                current_chunk = [line]
                current_sections = []
                
                if ipc_match:
                    current_sections.append(f"IPC {ipc_match.group(1)}")
                if bns_match:
                    current_sections.append(f"BNS {bns_match.group(1)}")
            else:
                current_chunk.append(line)
        
        # Add last chunk
        if current_chunk:
            chunks.append({
                "text": "\n".join(current_chunk),
                "page": page_num,
                "sections": current_sections
            })
        
        return chunks
    
    def create_embeddings(self):
        """Create embeddings for all chunks"""
        if not self.embedder:
            return
        
        try:
            texts = [chunk["text"] for chunk in self.chunks]
            self.chunk_embeddings = self.embedder.encode(
                texts,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=True
            )
            print(f"[RAGMapping] Created embeddings for {len(texts)} chunks")
        except Exception as e:
            print(f"[RAGMapping] Error creating embeddings: {e}")
            self.chunk_embeddings = None
    
    def index_with_chromadb(self):
        """Index chunks with ChromaDB for persistent storage"""
        try:
            chroma_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "data", "chromadb_ipc_mappings"
            )
            
            client = chromadb.PersistentClient(path=chroma_path)
            
            # Create or get collection
            embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name='all-MiniLM-L6-v2'
            )
            
            self.collection = client.get_or_create_collection(
                name="ipc_bns_mappings",
                embedding_function=embedding_fn
            )
            
            # Add chunks if collection is empty
            if self.collection.count() == 0:
                for i, chunk in enumerate(self.chunks):
                    self.collection.add(
                        documents=[chunk["text"]],
                        metadatas=[{
                            "page": chunk["page"],
                            "sections": str(chunk.get("sections", []))
                        }],
                        ids=[f"chunk_{i}"]
                    )
                print(f"[RAGMapping] Indexed {len(self.chunks)} chunks in ChromaDB")
            
        except Exception as e:
            print(f"[RAGMapping] ChromaDB error: {e}")
            self.collection = None
    
    def search_semantic(self, query: str, top_k: int = 5) -> List[Dict]:
        """Semantic search using embeddings"""
        if self.collection:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=top_k
                )
                
                documents = results['documents'][0] if results['documents'] else []
                distances = results['distances'][0] if results['distances'] else []
                metadatas = results['metadatas'][0] if results['metadatas'] else []
                
                return [{
                    "text": doc,
                    "distance": dist,
                    "metadata": meta
                } for doc, dist, meta in zip(documents, distances, metadatas)]
                
            except Exception as e:
                print(f"[RAGMapping] ChromaDB query error: {e}")
        
        # Fallback to numpy embeddings
        if self.chunk_embeddings is not None and self.embedder:
            try:
                query_emb = self.embedder.encode([query], normalize_embeddings=True)
                similarities = cosine_similarity(query_emb, self.chunk_embeddings)[0]
                
                top_indices = np.argsort(similarities)[::-1][:top_k]
                
                results = []
                for idx in top_indices:
                    results.append({
                        "text": self.chunks[idx]["text"],
                        "similarity": float(similarities[idx]),
                        "metadata": self.chunks[idx]
                    })
                
                return results
            except Exception as e:
                print(f"[RAGMapping] Embedding search error: {e}")
        
        return []
    
    def extract_mapping_with_llm(self, query: str, context: str) -> Dict:
        """Use LLM to extract mapping from context"""
        prompt = f"""You are a legal expert analyzing the transition from IPC to BNS 2023.

Based on the following context from the official BNS 2023 notification PDF, determine the correct BNS section for the given IPC section.

IPC Section Reference: {query}

Context from Official Document:
{context}

Extract the mapping information and respond with ONLY a JSON object in this exact format:
{{
    "ipc_section": "The IPC section number",
    "bns_section": "The corresponding BNS section number (format: BNS XXX)",
    "section_name": "Brief name/description of the offence",
    "confidence": 0.0-1.0,
    "reasoning": "Brief reasoning based on the context"
}}

If the mapping is not found in the context, set bns_section to "NOT_FOUND" and confidence to 0.0.
Be precise - only use information from the provided context."""

        try:
            response = ollama.chat(
                model=self.ollama_model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_gpu": 99}
            )
            
            content = response["message"]["content"]
            
            # Extract JSON
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
                
        except Exception as e:
            print(f"[RAGMapping] LLM error: {e}")
        
        return {
            "ipc_section": query,
            "bns_section": "NOT_FOUND",
            "section_name": "",
            "confidence": 0.0,
            "reasoning": "Error processing query"
        }
    
    def get_mapping(self, ipc_ref: str) -> Dict:
        """
        Get BNS mapping for an IPC reference using RAG
        """
        # Normalize reference
        ipc_ref = self.normalize_reference(ipc_ref)
        
        # First, try semantic search in the PDF
        search_results = self.search_semantic(ipc_ref, top_k=3)
        
        if search_results:
            # Combine relevant contexts
            context = "\n\n".join([r["text"] for r in search_results[:2]])
            
            # Use LLM to extract the mapping
            mapping = self.extract_mapping_with_llm(ipc_ref, context)
            
            if mapping.get("bns_section") != "NOT_FOUND":
                return {
                    "bns": mapping["bns_section"],
                    "name": mapping.get("section_name", ""),
                    "confidence": mapping.get("confidence", 0.7),
                    "reasoning": mapping.get("reasoning", ""),
                    "source": "rag_with_llm"
                }
        
        # Fallback to direct keyword matching in chunks
        mapping = self.direct_keyword_match(ipc_ref)
        if mapping:
            return mapping
        
        # Final fallback
        return {
            "bns": "UNKNOWN",
            "name": "Mapping not found in knowledge base",
            "confidence": 0.0,
            "source": "fallback"
        }
    
    def direct_keyword_match(self, ipc_ref: str) -> Optional[Dict]:
        """Direct keyword matching in chunks"""
        ipc_num = ipc_ref.split()[-1]
        
        for chunk in self.chunks:
            text = chunk["text"]
            
            # Look for patterns like "IPC X → BNS Y"
            pattern = rf'IPC\s+{ipc_num}\b.*?BNS\s+(\d+[A-Z]?(?:\(\d+\))?)'
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                bns_num = match.group(1)
                return {
                    "bns": f"BNS {bns_num}",
                    "name": self.extract_section_name(text, ipc_num),
                    "confidence": 0.85,
                    "source": "keyword_match"
                }
        
        return None
    
    def extract_section_name(self, text: str, ipc_num: str) -> str:
        """Extract section name from text"""
        # Look for description after the section number
        pattern = rf'IPC\s+{ipc_num}\b[^.\n]*\.\s*([A-Z][a-z\s]+)'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            name = match.group(1).strip()
            if len(name) > 10:
                return name[:100]
        
        return f"Section {ipc_num}"
    
    def normalize_reference(self, ref: str) -> str:
        """Normalize IPC reference"""
        ref = ref.upper().strip()
        
        # Extract section number
        match = re.search(r'(\d+[A-Z]?(?:\(\d+\))?)', ref)
        if not match:
            return ref
        
        num = match.group(1)
        
        # Determine act type
        if 'CRPC' in ref:
            return f"CrPC {num}"
        elif 'IEA' in ref:
            return f"IEA {num}"
        else:
            return f"IPC {num}"
    
    def create_fallback_index(self):
        """Create fallback index with known mappings"""
        print("[RAGMapping] Creating fallback index")
        
        # Create chunks from known mappings
        known_mappings = [
            "IPC 299 Culpable homicide → BNS 99",
            "IPC 300 Murder → BNS 100",
            "IPC 302 Punishment for murder → BNS 101",
            "IPC 304 Culpable homicide not amounting to murder → BNS 105",
            "IPC 304A Death by negligence → BNS 106",
            "IPC 304B Dowry death → BNS 80",
            "IPC 306 Abetment of suicide → BNS 108",
            "IPC 307 Attempt to murder → BNS 109",
            "IPC 309 Attempt to suicide (Abolished) → ABOLISHED",
            "IPC 319 Hurt → BNS 114",
            "IPC 320 Grievous hurt → BNS 116",
            "IPC 323 Voluntarily causing hurt → BNS 115",
            "IPC 354 Assault with intent to outrage modesty → BNS 74",
            "IPC 354A Sexual harassment → BNS 75",
            "IPC 354B Assault with intent to disrobe → BNS 76",
            "IPC 354C Voyeurism → BNS 77",
            "IPC 354D Stalking → BNS 78",
            "IPC 375 Rape → BNS 63",
            "IPC 376 Punishment for rape → BNS 64",
            "IPC 377 Unnatural offences (Abolished) → ABOLISHED",
            "IPC 378 Theft → BNS 303",
            "IPC 379 Punishment for theft → BNS 303",
            "IPC 383 Extortion → BNS 308",
            "IPC 384 Punishment for extortion → BNS 308",
            "IPC 390 Robbery → BNS 309",
            "IPC 391 Dacoity → BNS 310",
            "IPC 406 Criminal breach of trust → BNS 316",
            "IPC 415 Cheating → BNS 318",
            "IPC 420 Cheating and dishonestly inducing delivery → BNS 318",
            "IPC 498A Cruelty by husband or relatives → BNS 85",
            "IPC 499 Defamation → BNS 356",
            "IPC 503 Criminal intimidation → BNS 351",
            "IPC 506 Punishment for criminal intimidation → BNS 351",
            "IPC 509 Word/gesture to insult modesty → BNS 79",
            "CrPC 154 FIR registration → BNSS 173",
            "CrPC 156 Police investigation → BNSS 175",
            "CrPC 161 Examination of witnesses → BNSS 180",
            "CrPC 164 Recording of confessions → BNSS 183",
            "CrPC 173 Police report → BNSS 193",
            "IEA 65B Electronic evidence → BSA 63",
        ]
        
        self.chunks = [{"text": mapping, "page": 0, "sections": []} for mapping in known_mappings]
        
        if self.embedder:
            self.create_embeddings()
        
        print(f"[RAGMapping] Created fallback index with {len(self.chunks)} chunks")


# Singleton instance
_mapping_engine = None

def get_mapping_engine():
    global _mapping_engine
    if _mapping_engine is None:
        _mapping_engine = RAGMappingEngine()
    return _mapping_engine


if __name__ == "__main__":
    engine = RAGMappingEngine()
    
    # Test mappings
    test_refs = ["IPC 354", "IPC 420", "IPC 498A", "CrPC 154", "IEA 65B", "IPC 377"]
    
    for ref in test_refs:
        result = engine.get_mapping(ref)
        print(f"\n{ref}")
        print(f"  → {result['bns']}")
        print(f"  → {result['name']}")
        print(f"  → Confidence: {result['confidence']:.2f}")
        print(f"  → Source: {result.get('source', 'unknown')}")