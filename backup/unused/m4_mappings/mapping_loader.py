"""
mapping_loader.py — Dynamic IPC → BNS mapping loader from official gazette PDF
Team IKS | SPIT CSE 2025-26
"""

import os
import sys
import re
import json
from typing import Dict, List, Tuple
import fitz  # PyMuPDF

class BNSMappingLoader:
    """
    Load and maintain dynamic IPC → BNS mappings from official PDF
    Also supports fuzzy matching and AI-powered section identification
    """
    
    def __init__(self, pdf_path: str = None):
        self.pdf_path = pdf_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data", "statutes", "ipc_bns.pdf"
        )
        self.mappings = {}
        self.fuzzy_index = {}
        self.load_mappings_from_pdf()
    
    def load_mappings_from_pdf(self):
        """Extract IPC → BNS mappings from the official comparison PDF"""
        print(f"[MappingLoader] Loading from {self.pdf_path}")
        
        if not os.path.exists(self.pdf_path):
            print(f"[MappingLoader] PDF not found at {self.pdf_path}")
            return
        
        try:
            doc = fitz.open(self.pdf_path)
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            doc.close()
            
            # Parse the comparative table structure
            self._parse_comparative_table(full_text)
            print(f"[MappingLoader] Loaded {len(self.mappings)} IPC→BNS mappings")
            
            # Build fuzzy index for intelligent matching
            self._build_fuzzy_index()
            
        except Exception as e:
            print(f"[MappingLoader] Error loading PDF: {e}")
    
    def _parse_comparative_table(self, text: str):
        """
        Parse the comparative table from BNS vs IPC PDF.
        Format: "BNS Section X" followed by "IPC Section Y"
        """
        lines = text.split('\n')
        
        # Patterns to match
        bns_pattern = r'BNS\s+(\d+[A-Z]?(?:\(\d+\))?)'
        ipc_pattern = r'IPC\s+(\d+[A-Z]?(?:\(\d+\))?)'
        
        current_bns = None
        current_ipc = None
        
        for i, line in enumerate(lines):
            # Find BNS section
            bns_match = re.search(bns_pattern, line, re.IGNORECASE)
            if bns_match:
                current_bns = bns_match.group(1)
                # Look for IPC section in same or next lines
                for j in range(i, min(i + 5, len(lines))):
                    ipc_match = re.search(ipc_pattern, lines[j], re.IGNORECASE)
                    if ipc_match:
                        current_ipc = ipc_match.group(1)
                        break
                
                if current_ipc:
                    key = f"IPC {current_ipc}"
                    self.mappings[key] = {
                        "bns": f"BNS {current_bns}",
                        "name": self._extract_section_name(lines, i, current_bns)
                    }
                    current_ipc = None
        
        # Also parse the detailed table from later pages
        self._parse_detailed_table(text)
    
    def _parse_detailed_table(self, text: str):
        """Parse the detailed comparative table from pages 3-23"""
        # Look for patterns like:
        # "2023 (BNS) 1860 (IPC)"
        # "101. 302. Punishment for murder"
        
        pattern = r'(\d+)(?:\.|\))?\s+([^0-9]+?)\s+(\d+)(?:\.|\))?\s+([^0-9\n]+)'
        
        matches = re.findall(pattern, text, re.MULTILINE)
        for bns_num, bns_desc, ipc_num, ipc_desc in matches:
            bns_desc = bns_desc.strip()
            ipc_desc = ipc_desc.strip()
            
            key = f"IPC {ipc_num}"
            if key not in self.mappings:
                self.mappings[key] = {
                    "bns": f"BNS {bns_num}",
                    "name": ipc_desc or bns_desc
                }
    
    def _extract_section_name(self, lines: List[str], idx: int, section_num: str) -> str:
        """Extract the section name/description from context"""
        # Look for the section name in nearby lines
        for offset in [-2, -1, 0, 1, 2]:
            if idx + offset < len(lines) and idx + offset >= 0:
                line = lines[idx + offset]
                # Look for descriptive text without numbers
                desc_match = re.search(r'[A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', line)
                if desc_match and len(desc_match.group()) > 5:
                    return desc_match.group()
        return f"Section {section_num}"
    
    def _build_fuzzy_index(self):
        """Build fuzzy matching index for natural language section references"""
        self.fuzzy_index = {}
        
        for ipc_ref, mapping in self.mappings.items():
            # Extract keywords from section name
            name = mapping["name"].lower()
            keywords = re.findall(r'\b[a-z]{3,}\b', name)
            
            for kw in keywords:
                if kw not in self.fuzzy_index:
                    self.fuzzy_index[kw] = []
                self.fuzzy_index[kw].append(ipc_ref)
    
    def get_mapping(self, ipc_ref: str) -> Dict:
        """Get BNS mapping for an IPC reference"""
        # Standardize the reference
        ipc_ref = self._normalize_reference(ipc_ref)
        
        # Direct lookup
        if ipc_ref in self.mappings:
            return self.mappings[ipc_ref]
        
        # Fuzzy search if exact not found
        return self._fuzzy_match(ipc_ref)
    
    def _normalize_reference(self, ref: str) -> str:
        """Normalize IPC reference to standard format"""
        ref = ref.upper().strip()
        
        # Extract section number
        match = re.search(r'(\d+[A-Z]?(?:\(\d+\))?)', ref)
        if not match:
            return ref
        
        num = match.group(1)
        
        # Check if it's IPC or CrPC or IEA
        if 'CRPC' in ref or 'CR.P.C' in ref:
            return f"CrPC {num}"
        elif 'IEA' in ref or 'EVIDENCE' in ref:
            return f"IEA {num}"
        elif 'BNS' not in ref:
            return f"IPC {num}"
        
        return ref
    
    def _fuzzy_match(self, ref: str) -> Dict:
        """Find closest match using fuzzy logic"""
        ref_lower = ref.lower()
        
        # Extract keywords
        keywords = re.findall(r'\b[a-z]{3,}\b', ref_lower)
        
        # Score each mapping
        scores = {}
        for ipc_ref, mapping in self.mappings.items():
            score = 0
            for kw in keywords:
                if kw in mapping["name"].lower():
                    score += 2
                if kw in ipc_ref.lower():
                    score += 1
            if score > 0:
                scores[ipc_ref] = score
        
        if scores:
            best = max(scores, key=scores.get)
            return {
                **self.mappings[best],
                "fuzzy_match": True,
                "original_ref": ref,
                "matched_ref": best
            }
        
        # Return unknown mapping with confidence
        return {
            "bns": "UNKNOWN",
            "name": "Section not found in mapping database",
            "fuzzy_match": False,
            "confidence": 0
        }
    
    def search_by_description(self, description: str) -> List[Dict]:
        """Find sections by description (for AI-powered matching)"""
        desc_lower = description.lower()
        matches = []
        
        for ipc_ref, mapping in self.mappings.items():
            if any(kw in mapping["name"].lower() for kw in desc_lower.split()):
                matches.append({
                    "ipc": ipc_ref,
                    "bns": mapping["bns"],
                    "name": mapping["name"],
                    "relevance": self._calculate_relevance(desc_lower, mapping["name"])
                })
        
        return sorted(matches, key=lambda x: x["relevance"], reverse=True)[:5]
    
    def _calculate_relevance(self, query: str, text: str) -> float:
        """Calculate relevance score between query and text"""
        query_words = set(query.split())
        text_words = set(text.lower().split())
        
        if not query_words:
            return 0
        
        overlap = len(query_words & text_words)
        return overlap / len(query_words)
    
    def export_to_json(self, output_path: str = None):
        """Export mappings to JSON for caching"""
        if not output_path:
            output_path = os.path.join(
                os.path.dirname(__file__), 
                "ipc_bns_mappings.json"
            )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.mappings, f, indent=2, ensure_ascii=False)
        
        print(f"[MappingLoader] Exported {len(self.mappings)} mappings to {output_path}")


class AIEnhancedMapping:
    """
    AI-powered section mapping that uses Llama-3 for complex cases
    """
    
    def __init__(self):
        self.mapping_loader = BNSMappingLoader()
        self.cache = {}
    
    def map_section_with_ai(self, text: str, context: str = "") -> Dict:
        """
        Use AI to determine the correct BNS section mapping
        Especially useful for complex references or when direct mapping fails
        """
        import ollama
        
        # First try direct mapping
        direct_match = self.mapping_loader.get_mapping(text)
        if direct_match.get("bns") != "UNKNOWN":
            return direct_match
        
        # Use AI for complex cases
        prompt = f"""You are a legal expert specializing in Indian criminal law.

Given this text that references an IPC section or describes an offence, determine the correct BNS 2023 section.

TEXT: {text}
CONTEXT: {context}

Provide your response in JSON format:
{{
    "ipc_section": "The IPC section if mentioned, or 'UNKNOWN'",
    "bns_section": "The corresponding BNS section number (e.g., 'BNS 303')",
    "section_name": "Brief name of the offence",
    "confidence": 0.0-1.0,
    "reasoning": "Why you chose this mapping"
}}

Use the official mapping from the BNS 2023 notification.
If the text describes an offence, match it to the most appropriate BNS section."""

        try:
            response = ollama.chat(
                model=os.getenv("OLLAMA_MODEL", "llama3"),
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_gpu": 99}
            )
            
            # Parse JSON from response
            import json
            import re
            
            content = response["message"]["content"]
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    "bns": result.get("bns_section", "UNKNOWN"),
                    "name": result.get("section_name", ""),
                    "confidence": result.get("confidence", 0.5),
                    "ai_generated": True,
                    "reasoning": result.get("reasoning", "")
                }
        except Exception as e:
            print(f"[AI Mapping] Error: {e}")
        
        return {
            "bns": "UNKNOWN",
            "name": "Unable to map automatically",
            "confidence": 0,
            "ai_generated": False
        }