"""
ipc_bns_mapper.py — RAG-Based IPC to BNS Mapping using ChromaDB
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

This module uses ChromaDB to store and retrieve mappings from the IPC-BNS PDF
"""

import os
import sys
import re
import json
from typing import Dict, List, Tuple, Optional
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import fitz
import chromadb
from chromadb.utils import embedding_functions
import ollama
from sentence_transformers import SentenceTransformer
import numpy as np

class IPCBnsRAGMapper:
    """
    RAG-based mapper that uses ChromaDB to store and retrieve IPC→BNS mappings
    from the official PDF
    """
    
    def __init__(self, pdf_path: str = None):
        self.pdf_path = pdf_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "statutes", "ipc_bns.pdf"
        )
        
        # ChromaDB path
        self.chroma_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data", "chromadb_ipc_mappings"
        )
        
        self.collection = None
        self.embedder = None
        self.mappings_cache = {}
        
        # Initialize
        self.init_chromadb()
        self.load_and_index_pdf()
    
    def init_chromadb(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Create persistent client
            os.makedirs(self.chroma_path, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            
            # Use sentence transformer for embeddings
            self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="ipc_bns_mappings",
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
            
            print(f"[RAGMapper] ChromaDB initialized. Collection has {self.collection.count()} documents")
            
        except Exception as e:
            print(f"[RAGMapper] ChromaDB error: {e}")
            self.collection = None
    
    def load_and_index_pdf(self):
        """Load PDF and index all mappings into ChromaDB"""
        if self.collection and self.collection.count() > 0:
            print(f"[RAGMapper] Using existing index with {self.collection.count()} documents")
            return
        
        if not os.path.exists(self.pdf_path):
            print(f"[RAGMapper] PDF not found: {self.pdf_path}")
            self.create_fallback_index()
            return
        
        try:
            print(f"[RAGMapper] Loading PDF: {self.pdf_path}")
            doc = fitz.open(self.pdf_path)
            full_text = ""
            for page_num, page in enumerate(doc):
                full_text += page.get_text()
            doc.close()
            
            # Extract mapping chunks
            chunks = self.extract_mapping_chunks(full_text)
            
            if chunks:
                # Add to ChromaDB
                self.add_to_chromadb(chunks)
                print(f"[RAGMapper] Indexed {len(chunks)} mapping chunks")
            else:
                self.create_fallback_index()
                
        except Exception as e:
            print(f"[RAGMapper] Error: {e}")
            self.create_fallback_index()
    
    def extract_mapping_chunks(self, text: str) -> List[Dict]:
        """Extract meaningful mapping chunks from PDF text"""
        chunks = []
        lines = text.split('\n')
        
        # Look for lines containing both IPC and BNS
        current_chunk = []
        current_ipc = None
        current_bns = None
        
        for i, line in enumerate(lines):
            # Check for IPC section
            ipc_match = re.search(r'IPC\s+(\d+[A-Z]?(?:\(\d+\))?)', line, re.IGNORECASE)
            bns_match = re.search(r'BNS\s+(\d+[A-Z]?(?:\(\d+\))?)', line, re.IGNORECASE)
            
            if ipc_match or bns_match:
                # Save previous chunk
                if current_chunk and (current_ipc or current_bns):
                    chunk_text = "\n".join(current_chunk)
                    chunk_id = hashlib.md5(chunk_text.encode()).hexdigest()
                    
                    chunks.append({
                        "id": chunk_id,
                        "text": chunk_text,
                        "metadata": {
                            "ipc": current_ipc or "",
                            "bns": current_bns or "",
                            "page": i // 50
                        }
                    })
                
                # Start new chunk
                current_chunk = [line]
                current_ipc = ipc_match.group(1) if ipc_match else None
                current_bns = bns_match.group(1) if bns_match else None
            else:
                if current_chunk:
                    current_chunk.append(line)
        
        # Add last chunk
        if current_chunk:
            chunk_text = "\n".join(current_chunk)
            chunk_id = hashlib.md5(chunk_text.encode()).hexdigest()
            chunks.append({
                "id": chunk_id,
                "text": chunk_text,
                "metadata": {
                    "ipc": current_ipc or "",
                    "bns": current_bns or "",
                    "page": 0
                }
            })
        
        return chunks
    
    def add_to_chromadb(self, chunks: List[Dict]):
        """Add chunks to ChromaDB"""
        if not self.collection:
            return
        
        try:
            ids = [chunk["id"] for chunk in chunks]
            documents = [chunk["text"] for chunk in chunks]
            metadatas = [chunk["metadata"] for chunk in chunks]
            
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            print(f"[RAGMapper] Added {len(chunks)} documents to ChromaDB")
            
        except Exception as e:
            print(f"[RAGMapper] Error adding to ChromaDB: {e}")
    
    def create_fallback_index(self):
        """Create fallback index with verified mappings"""
        print("[RAGMapper] Creating fallback index with verified mappings")
        
        # Verified mappings from official BNS 2023
        verified_mappings = {
            "IPC 299": "BNS 99",
            "IPC 300": "BNS 100",
            "IPC 302": "BNS 101",
            "IPC 304": "BNS 105",
            "IPC 304A": "BNS 106",
            "IPC 304B": "BNS 80",
            "IPC 306": "BNS 108",
            "IPC 307": "BNS 109",
            "IPC 319": "BNS 114",
            "IPC 320": "BNS 116",
            "IPC 323": "BNS 115",
            "IPC 354": "BNS 74",
            "IPC 354A": "BNS 75",
            "IPC 354B": "BNS 76",
            "IPC 354C": "BNS 77",
            "IPC 354D": "BNS 78",
            "IPC 375": "BNS 63",
            "IPC 376": "BNS 64",
            "IPC 377": "ABOLISHED",
            "IPC 378": "BNS 303",
            "IPC 379": "BNS 303",
            "IPC 383": "BNS 308",
            "IPC 384": "BNS 308",
            "IPC 390": "BNS 309",
            "IPC 391": "BNS 310",
            "IPC 406": "BNS 316",
            "IPC 415": "BNS 318",
            "IPC 416": "BNS 319",
            "IPC 417": "BNS 318",
            "IPC 420": "BNS 318",
            "IPC 441": "BNS 329",
            "IPC 447": "BNS 329",
            "IPC 498A": "BNS 85",
            "IPC 499": "BNS 356",
            "IPC 500": "BNS 356",
            "IPC 503": "BNS 351",
            "IPC 506": "BNS 351",
            "IPC 509": "BNS 79",
            "CrPC 154": "BNSS 173",
            "CrPC 156": "BNSS 175",
            "CrPC 156(3)": "BNSS 175(3)",
            "CrPC 161": "BNSS 180",
            "CrPC 164": "BNSS 183",
            "CrPC 167": "BNSS 187",
            "CrPC 173": "BNSS 193",
            "IEA 65B": "BSA 63",
            "IEA 27": "BSA 23",
        }
        
        # Create chunks for ChromaDB
        chunks = []
        for ipc_ref, bns_ref in verified_mappings.items():
            chunks.append({
                "id": hashlib.md5(ipc_ref.encode()).hexdigest(),
                "text": f"{ipc_ref} corresponds to {bns_ref} under BNS 2023",
                "metadata": {
                    "ipc": ipc_ref.split()[1] if len(ipc_ref.split()) > 1 else "",
                    "bns": bns_ref.split()[1] if bns_ref != "ABOLISHED" else "ABOLISHED",
                    "type": ipc_ref.split()[0]
                }
            })
            
            # Also cache for quick lookup
            self.mappings_cache[ipc_ref] = {
                "bns": bns_ref,
                "name": self.get_section_name(ipc_ref)
            }
        
        if self.collection and self.collection.count() == 0:
            self.add_to_chromadb(chunks)
        
        print(f"[RAGMapper] Created fallback index with {len(chunks)} mappings")
    
    def get_section_name(self, ipc_ref: str) -> str:
        """Get section name for display"""
        names = {
            "IPC 354": "Assault with intent to outrage modesty",
            "IPC 420": "Cheating and dishonestly inducing delivery",
            "IPC 406": "Criminal breach of trust",
            "IPC 506": "Criminal intimidation",
            "IPC 498A": "Cruelty by husband or relatives",
            "CrPC 154": "FIR registration",
            "CrPC 156": "Police investigation",
            "CrPC 156(3)": "Magistrate's power to order investigation",
            "IEA 65B": "Electronic evidence admissibility",
        }
        return names.get(ipc_ref, "")
    
    def search_mapping(self, section_ref: str) -> Dict:
        """
        Search for mapping using RAG
        """
        # Check cache first
        if section_ref in self.mappings_cache:
            return self.mappings_cache[section_ref]
        
        # Search in ChromaDB
        if self.collection:
            try:
                results = self.collection.query(
                    query_texts=[section_ref],
                    n_results=3
                )
                
                if results['documents'] and results['documents'][0]:
                    # Look for exact match in results
                    for doc, metadata in zip(results['documents'][0], results['metadatas'][0]):
                        ipc_num = metadata.get('ipc', '')
                        if ipc_num and ipc_num in section_ref:
                            bns_ref = f"BNS {metadata['bns']}" if metadata['bns'] != 'ABOLISHED' else "ABOLISHED"
                            result = {
                                "bns": bns_ref,
                                "name": self.get_section_name(section_ref),
                                "confidence": 0.9
                            }
                            self.mappings_cache[section_ref] = result
                            return result
            except Exception as e:
                print(f"[RAGMapper] Search error: {e}")
        
        # Return unknown
        return {
            "bns": "UNKNOWN",
            "name": "Section not found",
            "confidence": 0.0
        }
    
    def get_mapping(self, act: str, section: str) -> Dict:
        """Get mapping for a section"""
        key = f"{act} {section}"
        return self.search_mapping(key)


# Global instance
_mapper = None

def get_mapper():
    global _mapper
    if _mapper is None:
        _mapper = IPCBnsRAGMapper()
    return _mapper