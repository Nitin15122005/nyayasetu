# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/build_ipc_bns_mapping.py

Ground truth: merges TWO real, non-LLM sources already in the project —

  tier_a) backend/lex_validator.py's FALLBACK_MAPPINGS dict — the
          hand-curated table the live LexValidator actually falls back to
          in production (tier 2 of its 3-tier cascade). Extracted by
          parsing the source file's AST (NOT by importing lex_validator,
          which eagerly constructs a Groq client at import time and would
          crash without GROQ_API_KEY set — see ai_clients.py).

  tier_b) data/ipc_bns_mappings.json — 160 entries mechanically
          regex-parsed from the official ipc_bns.pdf gazette comparison
          table by backup/unused/m4_mappings/mapping_loader.py
          (BNSMappingLoader._parse_comparative_table /
          _parse_detailed_table — plain regex over PDF text, no LLM
          anywhere in that path). The source PDF itself is not currently
          in the repo (only BNS.pdf/BNSS.pdf/BSA.pdf are, per
          data/statutes/README.txt) — this JSON is the surviving artifact
          of that extraction, and its provenance is documented here so
          the gap (missing source PDF) is visible, not hidden.

Where both tiers cover the same (act, section), tier_a wins — it's the
one actually compiled into the live production fallback table, so it's
the higher-confidence source for "what the system is supposed to
return". tier_b's mojibake in `name` (PDF-extraction encoding artifact —
see common.clean_mojibake) is cleaned, not re-derived.

text_context is phrased to match backend/lex_validator.py's
SectionExtractor regexes (e.g. "Section 302 IPC") so the ipc_bns_mapping
runner's /api/compliance call can actually find the reference — mirrors
runners/ipc_bns_mapping.py's own fallback phrasing.
"""

from __future__ import annotations

import ast
import re

from evaluation.datasets.build.common import BACKEND_DIR, DATA_DIR, clean_mojibake, load_json, write_jsonl
from evaluation.datasets.schema import IPCBNSMappingRecord


def _parse_fallback_mappings() -> dict:
    src = (BACKEND_DIR / "lex_validator.py").read_text(encoding="utf-8")
    m = re.search(r"FALLBACK_MAPPINGS\s*=\s*(\{.*?\n\})\n", src, re.DOTALL)
    if not m:
        raise RuntimeError("Could not locate FALLBACK_MAPPINGS in backend/lex_validator.py — "
                            "source format changed, update this parser.")
    return ast.literal_eval(m.group(1))


def _act_and_number(key: str) -> tuple[str, str]:
    # keys look like "IPC 406", "CrPC 156(3)", "IEA 65B"
    act, section = key.split(" ", 1)
    return act, section


def build() -> list[IPCBNSMappingRecord]:
    tier_a = _parse_fallback_mappings()
    tier_b_raw = load_json("ipc_bns_mappings.json")

    records: dict[str, IPCBNSMappingRecord] = {}

    # tier_b first (lower priority — filled in, then overwritten by tier_a)
    for key, entry in tier_b_raw.items():
        act = "IPC"  # every key in this file is literally "IPC <n>" per the mapping_loader.py source
        section = entry.get("section_num") or key.split(" ", 1)[-1]
        bns = entry.get("bns", "UNKNOWN")
        name = clean_mojibake(entry.get("name", ""))
        rid = f"ipcbns_{act.lower()}_{section}"
        records[rid] = IPCBNSMappingRecord(
            id=rid,
            tags=["pdf_regex_extraction", "ipc_bns_pdf_gazette_table"],
            notes=(
                "Source: data/ipc_bns_mappings.json, mechanically regex-parsed from the official "
                "ipc_bns.pdf gazette comparison table by backup/unused/m4_mappings/mapping_loader.py "
                "(BNSMappingLoader._parse_comparative_table/_parse_detailed_table). The source PDF is "
                "not present in this repo copy (data/statutes/ only has BNS/BNSS/BSA) — this JSON is "
                "the surviving extraction artifact. `name` field had PDF-encoding mojibake, cleaned "
                "here (see common.clean_mojibake) without altering the underlying section mapping."
            ),
            act=act,
            section=section,
            expected_bns=bns,
            expected_name=name,
            text_context=f"The old provision under Section {section} {act} corresponds to {bns} under the new code.",
        )

    # tier_a overrides — the live production fallback table
    for key, entry in tier_a.items():
        act, section = _act_and_number(key)
        rid = f"ipcbns_{act.lower()}_{section}"
        records[rid] = IPCBNSMappingRecord(
            id=rid,
            tags=["hand_curated", "production_fallback_table"],
            notes=(
                "Source: backend/lex_validator.py FALLBACK_MAPPINGS — the hand-curated table the live "
                "LexValidator actually falls back to (tier 2 of its 3-tier cascade: RAG -> this table "
                "-> Groq zero-shot). Extracted by AST-parsing the source file, not by importing it "
                "(importing lex_validator.py eagerly constructs a Groq client via ai_clients.py and "
                "fails without GROQ_API_KEY set)."
            ),
            act=act,
            section=section,
            expected_bns=entry["bns"],
            expected_name=entry.get("name", ""),
            text_context=f"Charged under Section {section} {act}." if act != "IEA"
                         else f"Electronic evidence submitted under Section {section} of the Indian Evidence Act.",
        )

    return sorted(records.values(), key=lambda r: r.id)


if __name__ == "__main__":
    recs = build()
    write_jsonl(recs, "ipc_bns_mapping.jsonl")
    print(f"[BUILD] ipc_bns_mapping: {len(recs)} unique (act, section) mappings "
          f"({sum(1 for r in recs if 'hand_curated' in r.tags)} production-table, "
          f"{sum(1 for r in recs if 'pdf_regex_extraction' in r.tags)} pdf-extracted-only)")
