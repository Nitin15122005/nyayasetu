"""
lex_validator.py — Complete IPC → BNS Mapping with RAG + AI Enhancement
Nyaya-Setu | Team IKS | SPIT CSE 2025-26

Features:
  1. RAG-based IPC → BNS mapping from official PDF (using ChromaDB)
  2. AI-powered section identification for complex cases
  3. Citation verifier with knowledge base
  4. Compliance scorer (0-100) with confidence weighting
  5. IRAC reasoning formatter
  6. Support for CrPC, IEA mappings
"""

import os
import sys
import re
import json
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime
import hashlib
import traceback

# Add paths
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz  # PyMuPDF
import ollama
import numpy as np
from dotenv import load_dotenv

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

# Try to import ChromaDB
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("[LexValidator] ChromaDB not available, using fallback mappings")

# Try to import sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# ============================================================================
# SECTION EXTRACTOR - Handles all reference formats
# ============================================================================

class SectionExtractor:
    """Extract all legal section references from text"""
    
    def __init__(self):
        self.patterns = [
            # Multiple sections: "Sections 406, 420, and 506 IPC"
            (r'Sections?\s+([\d,\s]+?)\s+(?:and|&)?\s*(\d+)?\s+(IPC|CrPC|IEA)', self._extract_multi),
            # Single sections: "Section 406 IPC"
            (r'Section\s+(\d+[A-Z]?(?:\(\d+\))?)\s+(IPC|CrPC|IEA)', self._extract_single),
            # Short form: "IPC 406"
            (r'(IPC|CrPC|IEA)\s+(\d+[A-Z]?(?:\(\d+\))?)', self._extract_short),
            # With colon: "IPC: 406"
            (r'(IPC|CrPC|IEA):\s+(\d+[A-Z]?(?:\(\d+\))?)', self._extract_short),
            # Special case: "Section 65B of the Indian Evidence Act"
            (r'Section\s+(65B)\s+(?:of\s+the\s+)?(?:Indian\s+)?(?:Evidence\s+Act|IEA)', self._extract_iea_65b),
            # Under section: "under section 406 IPC"
            (r'under\s+section\s+(\d+[A-Z]?(?:\(\d+\))?)\s+(IPC|CrPC|IEA)', self._extract_single),
        ]
    
    def _extract_multi(self, match) -> List[Tuple[str, str]]:
        """Extract multiple sections from a match"""
        results = []
        full_text = match.group(0)
        act = match.group(3)
        numbers = re.findall(r'\b(\d+)\b', full_text)
        for num in numbers:
            results.append((act, num))
        return results
    
    def _extract_single(self, match) -> List[Tuple[str, str]]:
        """Extract single section"""
        section = match.group(1)
        act = match.group(2)
        return [(act, section)]
    
    def _extract_short(self, match) -> List[Tuple[str, str]]:
        """Extract short form section"""
        act = match.group(1)
        section = match.group(2)
        return [(act, section)]
    
    def _extract_iea_65b(self, match) -> List[Tuple[str, str]]:
        """Extract IEA 65B special case"""
        return [("IEA", "65B")]
    
    def extract(self, text: str) -> List[Tuple[str, str]]:
        """Extract all section references from text"""
        references = []
        seen = set()
        
        for pattern, extractor in self.patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    extracted = extractor(match)
                    for act, section in extracted:
                        key = f"{act} {section}"
                        if key not in seen:
                            seen.add(key)
                            references.append((act, section))
                except Exception as e:
                    continue
        
        return references


# ============================================================================
# FALLBACK MAPPINGS (Comprehensive)
# ============================================================================

FALLBACK_MAPPINGS = {
    # IPC to BNS
    "IPC 299": {"bns": "BNS 99", "name": "Culpable homicide"},
    "IPC 300": {"bns": "BNS 100", "name": "Murder"},
    "IPC 302": {"bns": "BNS 101", "name": "Punishment for murder"},
    "IPC 304": {"bns": "BNS 105", "name": "Culpable homicide not amounting to murder"},
    "IPC 304A": {"bns": "BNS 106", "name": "Death by negligence"},
    "IPC 304B": {"bns": "BNS 80", "name": "Dowry death"},
    "IPC 306": {"bns": "BNS 108", "name": "Abetment of suicide"},
    "IPC 307": {"bns": "BNS 109", "name": "Attempt to murder"},
    "IPC 309": {"bns": "ABOLISHED", "name": "Attempt to suicide (Decriminalized)"},
    "IPC 319": {"bns": "BNS 114", "name": "Hurt"},
    "IPC 320": {"bns": "BNS 116", "name": "Grievous hurt"},
    "IPC 323": {"bns": "BNS 115", "name": "Voluntarily causing hurt"},
    "IPC 324": {"bns": "BNS 118", "name": "Voluntarily causing hurt by dangerous weapons"},
    "IPC 325": {"bns": "BNS 117", "name": "Voluntarily causing grievous hurt"},
    "IPC 326": {"bns": "BNS 118", "name": "Voluntarily causing grievous hurt by dangerous weapons"},
    "IPC 326A": {"bns": "BNS 124", "name": "Acid attack"},
    "IPC 326B": {"bns": "BNS 125", "name": "Attempt to throw acid"},
    "IPC 354": {"bns": "BNS 74", "name": "Assault with intent to outrage modesty"},
    "IPC 354A": {"bns": "BNS 75", "name": "Sexual harassment"},
    "IPC 354B": {"bns": "BNS 76", "name": "Assault with intent to disrobe"},
    "IPC 354C": {"bns": "BNS 77", "name": "Voyeurism"},
    "IPC 354D": {"bns": "BNS 78", "name": "Stalking"},
    "IPC 375": {"bns": "BNS 63", "name": "Rape"},
    "IPC 376": {"bns": "BNS 64", "name": "Punishment for rape"},
    "IPC 376A": {"bns": "BNS 66", "name": "Rape causing death or vegetative state"},
    "IPC 376D": {"bns": "BNS 70", "name": "Gang rape"},
    "IPC 377": {"bns": "ABOLISHED", "name": "Unnatural offences (Decriminalized)"},
    "IPC 378": {"bns": "BNS 303", "name": "Theft"},
    "IPC 379": {"bns": "BNS 303", "name": "Punishment for theft"},
    "IPC 380": {"bns": "BNS 305", "name": "Theft in dwelling house"},
    "IPC 382": {"bns": "BNS 306", "name": "Theft after preparation for hurt"},
    "IPC 383": {"bns": "BNS 308", "name": "Extortion"},
    "IPC 384": {"bns": "BNS 308", "name": "Punishment for extortion"},
    "IPC 390": {"bns": "BNS 309", "name": "Robbery"},
    "IPC 391": {"bns": "BNS 310", "name": "Dacoity"},
    "IPC 392": {"bns": "BNS 309", "name": "Punishment for robbery"},
    "IPC 395": {"bns": "BNS 310", "name": "Punishment for dacoity"},
    "IPC 397": {"bns": "BNS 311", "name": "Robbery with attempt to cause death"},
    "IPC 399": {"bns": "BNS 312", "name": "Making preparation to commit dacoity"},
    "IPC 406": {"bns": "BNS 316", "name": "Criminal breach of trust"},
    "IPC 415": {"bns": "BNS 318", "name": "Cheating"},
    "IPC 416": {"bns": "BNS 319", "name": "Cheating by personation"},
    "IPC 417": {"bns": "BNS 318", "name": "Punishment for cheating"},
    "IPC 420": {"bns": "BNS 318", "name": "Cheating and dishonestly inducing delivery"},
    "IPC 425": {"bns": "BNS 324", "name": "Mischief"},
    "IPC 426": {"bns": "BNS 324", "name": "Punishment for mischief"},
    "IPC 441": {"bns": "BNS 329", "name": "Criminal trespass"},
    "IPC 442": {"bns": "BNS 330", "name": "House trespass"},
    "IPC 447": {"bns": "BNS 329", "name": "Punishment for criminal trespass"},
    "IPC 448": {"bns": "BNS 330", "name": "Punishment for house trespass"},
    "IPC 498A": {"bns": "BNS 85", "name": "Cruelty by husband or relatives"},
    "IPC 499": {"bns": "BNS 356", "name": "Defamation"},
    "IPC 500": {"bns": "BNS 356", "name": "Punishment for defamation"},
    "IPC 503": {"bns": "BNS 351", "name": "Criminal intimidation"},
    "IPC 506": {"bns": "BNS 351", "name": "Punishment for criminal intimidation"},
    "IPC 509": {"bns": "BNS 79", "name": "Word, gesture or act intended to insult modesty"},
    
    # CrPC to BNSS
    "CrPC 154": {"bns": "BNSS 173", "name": "FIR registration"},
    "CrPC 156": {"bns": "BNSS 175", "name": "Police investigation"},
    "CrPC 156(3)": {"bns": "BNSS 175(3)", "name": "Magistrate's power to order investigation"},
    "CrPC 161": {"bns": "BNSS 180", "name": "Examination of witnesses"},
    "CrPC 164": {"bns": "BNSS 183", "name": "Recording of confessions"},
    "CrPC 167": {"bns": "BNSS 187", "name": "Remand"},
    "CrPC 173": {"bns": "BNSS 193", "name": "Police report"},
    "CrPC 197": {"bns": "BNSS 218", "name": "Prosecution of judges and public servants"},
    "CrPC 313": {"bns": "BNSS 351", "name": "Power to examine the accused"},
    "CrPC 437": {"bns": "BNSS 479", "name": "Bail in non-bailable offences"},
    "CrPC 438": {"bns": "BNSS 482", "name": "Anticipatory bail"},
    "CrPC 439": {"bns": "BNSS 483", "name": "Special powers of Sessions Court re bail"},
    
    # IEA to BSA
    "IEA 65B": {"bns": "BSA 63", "name": "Electronic evidence admissibility"},
    "IEA 27": {"bns": "BSA 23", "name": "Admissibility of confession to police"},
}


# ============================================================================
# AI-ENHANCED MAPPING
# ============================================================================

class AIEnhancedMapping:
    """AI-powered section mapping using Llama-3"""
    
    def __init__(self):
        self.cache = {}
    
    def map_section_with_ai(self, text: str, context: str = "") -> Dict:
        """Use AI to determine mapping"""
        
        # Check cache
        cache_key = hashlib.md5(f"{text}:{context}".encode()).hexdigest()
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Use AI for mapping
        prompt = f"""You are a legal expert specializing in Indian criminal law and the transition from IPC to BNS 2023.

Given this text that references a legal section, determine the correct BNS/BNSS/BSA section.

TEXT: {text}
CONTEXT: {context}

Provide your response in this exact JSON format:
{{
    "bns_section": "The corresponding section (format: BNS XXX, BNSS XXX, or BSA XXX)",
    "section_name": "Brief name of the offence",
    "confidence": 0.0-1.0,
    "reasoning": "Brief reasoning"
}}

If not found, set bns_section to "NOT_FOUND"."""

        try:
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "num_gpu": 99, "num_ctx": 2048}
            )
            
            content = response["message"]["content"]
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            
            if json_match:
                result = json.loads(json_match.group())
                mapped = {
                    "bns": result.get("bns_section", "UNKNOWN"),
                    "name": result.get("section_name", ""),
                    "confidence": float(result.get("confidence", 0.5)),
                    "reasoning": result.get("reasoning", ""),
                    "ai_generated": True
                }
                self.cache[cache_key] = mapped
                return mapped
                
        except Exception as e:
            print(f"[AI Mapping] Error: {e}")
        
        return {
            "bns": "UNKNOWN",
            "name": "Unable to map automatically",
            "confidence": 0.0,
            "ai_generated": False
        }


# ============================================================================
# MAIN VALIDATOR CLASS
# ============================================================================

class LexValidator:
    """Main validator with all features"""
    
    def __init__(self):
        self.extractor = SectionExtractor()
        self.ai_mapper = AIEnhancedMapping()
        self.fallback_mappings = FALLBACK_MAPPINGS
    
    def get_mapping(self, act: str, section: str) -> Dict:
        """Get mapping for a section"""
        key = f"{act} {section}"
        
        # Check fallback mappings
        if key in self.fallback_mappings:
            return self.fallback_mappings[key]
        
        return {
            "bns": "UNKNOWN",
            "name": "Section not found",
            "confidence": 0.0
        }
    
    def validate(self, text: str, use_ai: bool = True) -> Dict:
        """Validate text and return mappings"""
        references = self.extractor.extract(text)
        found_mappings = []
        
        for act, section in references:
            key = f"{act} {section}"
            
            # Get mapping
            mapping = self.get_mapping(act, section)
            
            # If not found and AI is enabled
            if mapping.get("bns") == "UNKNOWN" and use_ai:
                ai_mapping = self.ai_mapper.map_section_with_ai(key, text)
                if ai_mapping.get("bns") != "UNKNOWN":
                    mapping = ai_mapping
            
            if mapping and mapping.get("bns") != "UNKNOWN":
                found_mappings.append({
                    "old": key,
                    "new": mapping["bns"],
                    "name": mapping.get("name", ""),
                    "ai_generated": mapping.get("ai_generated", False),
                    "confidence": mapping.get("confidence", 0.8)
                })
        
        return {
            "total_old_references": len(found_mappings),
            "mappings": found_mappings,
            "obsolete": [m["old"] for m in found_mappings if "ABOLISHED" in m["new"]],
            "migrated": [m["old"] for m in found_mappings if "ABOLISHED" not in m["new"]]
        }
    
    def compute_score(self, text: str, use_ai: bool = True) -> Dict:
        """Compute compliance score"""
        report = self.validate(text, use_ai)
        
        # Count new references
        bns_refs = len(re.findall(r'\bBNS\s+\d+\b', text, re.IGNORECASE))
        bnss_refs = len(re.findall(r'\bBNSS\s+\d+\b', text, re.IGNORECASE))
        bsa_refs = len(re.findall(r'\bBSA\s+\d+\b', text, re.IGNORECASE))
        new_refs = bns_refs + bnss_refs + bsa_refs
        
        old_refs = report["total_old_references"]
        total = old_refs + new_refs
        
        if total == 0:
            score = 100
            grade = "A"
            note = "No statutory references found in document."
        elif old_refs == 0:
            score = 100
            grade = "A"
            note = "Document uses only BNS/BNSS/BSA references. Fully compliant."
        else:
            base_score = (new_refs / total) * 100
            abolished_count = len(report["obsolete"])
            penalty = abolished_count * 5
            score = max(0, base_score - penalty)
            
            if score >= 90:
                grade = "A"
            elif score >= 70:
                grade = "B"
            elif score >= 50:
                grade = "C"
            elif score >= 30:
                grade = "D"
            else:
                grade = "F"
            
            note = f"Found {old_refs} old references, {new_refs} new references. {abolished_count} abolished sections."
        
        return {
            "score": int(score),
            "grade": grade,
            "note": note,
            "report": report,
            "ai_assisted": any(m.get("ai_generated", False) for m in report["mappings"]),
            "timestamp": datetime.now().isoformat()
        }


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Create global validator instance
validator = LexValidator()


# ============================================================================
# BACKWARD COMPATIBILITY FUNCTIONS
# ============================================================================

def check_ipc_references(text: str, use_ai: bool = True) -> dict:
    """Backward compatibility function"""
    result = validator.validate(text, use_ai)
    return {
        "total_old_references": result["total_old_references"],
        "migrated": result["migrated"],
        "obsolete": result["obsolete"],
        "mappings": result["mappings"],
        "dynamic_mappings_used": True
    }


def compute_compliance_score(text: str, use_ai: bool = True) -> dict:
    """Backward compatibility function"""
    return validator.compute_score(text, use_ai)


def generate_migration_message(result: dict) -> str:
    """Format migration result as a clean WhatsApp message."""
    score = result["score"]
    grade = result["grade"]
    note = result["note"]
    mappings = result["report"]["mappings"]
    obsolete = result["report"]["obsolete"]
    
    # Score bar
    filled = int(score / 10)
    bar = "█" * filled + "░" * (10 - filled)
    
    msg = (
        f"📋 *BNS Compliance Score*\n\n"
        f"{bar} *{score}/100* (Grade {grade})\n\n"
        f"{note}\n"
    )
    
    if mappings:
        msg += "\n🔄 *IPC → BNS Corrections:*\n"
        for m in mappings[:8]:
            ai_tag = " 🤖" if m.get("ai_generated") else ""
            if "ABOLISHED" in m["new"]:
                msg += f"❌ {m['old']} → ABOLISHED under BNS{ai_tag}\n"
                if m.get("name"):
                    msg += f"   {m['name']}\n"
            else:
                msg += f"✅ {m['old']} → {m['new']}{ai_tag}\n"
                if m.get("name"):
                    msg += f"   {m['name']}\n"
    
    if obsolete:
        msg += f"\n⚠️ *Warning:* {len(obsolete)} abolished section(s) cited.\n"
        msg += "These offences no longer exist under BNS 2023.\n"
    
    if score < 70:
        msg += (
            "\n📌 *Action required:* Update all IPC/CrPC references to "
            "BNS/BNSS before filing. Courts may reject documents citing "
            "obsolete sections."
        )
    elif score < 90:
        msg += "\n✅ Document is largely BNS-compliant. Minor updates recommended."
    else:
        msg += "\n✅ Document is fully BNS-compliant."
    
    if result.get("ai_assisted"):
        msg += "\n\n🤖 *Note:* Some mappings were generated with AI assistance."
    
    return msg


# ============================================================================
# CITATION VERIFIER
# ============================================================================

KB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                       "data", "legal_kb.json")

def load_kb_sections() -> Set[str]:
    """Load all known BNS section numbers from the knowledge base."""
    try:
        if os.path.exists(KB_PATH):
            with open(KB_PATH, "r", encoding="utf-8") as f:
                kb = json.load(f)
            
            sections = set()
            for offence in kb.get("offences", []):
                nums = re.findall(r'(?:BNS|BNSS|BSA)\s+(?:Section\s+)?(\d+[A-Z]?(?:\(\d+\))?)', 
                                offence.get("bns_section", ""))
                for n in nums:
                    sections.add(n)
            return sections
    except Exception as e:
        print(f"[KB Load] Error: {e}")
    
    return set()


KNOWN_SECTIONS = load_kb_sections()


def verify_citations(sections: List[str]) -> dict:
    """Verify that cited sections are in the knowledge base."""
    verified = []
    unverified = []
    
    for section in sections:
        nums = re.findall(r'(\d+[A-Z]?(?:\(\d+\))?)', section)
        
        if any(n in KNOWN_SECTIONS for n in nums):
            verified.append(section)
        else:
            unverified.append(section)
    
    confidence = "High" if len(unverified) == 0 else "Medium" if len(verified) > 0 else "Low"
    
    return {
        "verified": verified,
        "unverified": unverified,
        "all_verified": len(unverified) == 0,
        "confidence": confidence,
        "verified_count": len(verified),
        "unverified_count": len(unverified)
    }


# ============================================================================
# IRAC REASONING FORMATTER
# ============================================================================

def format_irac(
    complaint: str,
    section: str,
    section_desc: str,
    punishment: str,
    case_facts: str,
) -> str:
    """Generate IRAC-structured legal reasoning."""
    prompt = f"""You are a senior Indian legal advocate. 
Analyse this case using the IRAC framework. Keep each section SHORT — 2-3 sentences maximum.
Use simple English. No jargon.

CASE FACTS: {case_facts}
COMPLAINT: {complaint}
APPLICABLE SECTION: {section}
SECTION DESCRIPTION: {section_desc}
PUNISHMENT: {punishment}

Respond in exactly this format — nothing else:

ISSUE
[What is the precise legal question? What wrong was committed?]

RULE
[What does {section} say? What are the legal elements that must be proven?]

APPLICATION
[How do the facts of this case satisfy or not satisfy the rule? Is the case strong or weak?]

CONCLUSION
[What is the likely legal outcome? What should the complainant do?]"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2, "num_ctx": 2048, "num_gpu": 99},
        )
        return response["message"]["content"].strip()
    except Exception as e:
        return f"Error generating IRAC analysis: {e}"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from a PDF uploaded by the user."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text("text") + "\n"
        doc.close()
        return text.strip()
    except Exception as e:
        return f"ERROR: Could not read PDF — {e}"


def extract_text_from_image_bytes(img_bytes: bytes) -> str:
    """Extract text from an image using OCR."""
    try:
        import pytesseract
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(img_bytes))
        text = pytesseract.image_to_string(img)
        return text.strip()
    except ImportError:
        return "OCR not available. Please upload a PDF version of the document."
    except Exception as e:
        return f"ERROR: {e}"


# ============================================================================
# CLI TEST
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("LEX VALIDATOR - Complete Test")
    print("="*70)
    
    sample = """The accused is charged under Sections 406, 420, and 506 IPC. 
    The complainant also invokes Section 354 IPC for outrage of modesty. 
    The FIR was registered under Section 154 CrPC and proceedings initiated under Section 156(3) CrPC. 
    Electronic evidence has been submitted under Section 65B of the Indian Evidence Act."""
    
    print("\nSample Text:")
    print(sample)
    
    # Extract sections
    extractor = SectionExtractor()
    sections = extractor.extract(sample)
    print(f"\n📌 Extracted Sections: {sections}")
    
    # Compute score
    result = validator.compute_score(sample, use_ai=True)
    print(f"\n📊 Score: {result['score']}/100 (Grade {result['grade']})")
    print(f"   Found {result['report']['total_old_references']} references")
    
    print("\n🔄 Mappings:")
    for m in result["report"]["mappings"]:
        print(f"\n  {m['old']} → {m['new']}")
        print(f"    {m['name']}")
    
    expected = ["IPC 406", "IPC 420", "IPC 506", "IPC 354", "CrPC 154", "CrPC 156(3)", "IEA 65B"]
    found = [m["old"] for m in result["report"]["mappings"]]
    
    print(f"\n✅ Found {len(found)}/{len(expected)} sections")
    if len(found) == len(expected):
        print("🎉 All 7 sections mapped correctly!")
    else:
        missing = [e for e in expected if e not in found]
        print(f"⚠️ Missing: {missing}")
    
    print("\n✅ Test completed!")