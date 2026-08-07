# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/build_research.py

Ground truth: queries built from data/legal_kb.json's 18 curated
offence records (each with a real bns_section + offence_name — see
build_ipc_bns_mapping.py's sibling docstring for this file's own
provenance: "source": "Bharatiya Nyaya Sanhita 2023 / BNSS 2023 / BSA
2023", hand-curated for this project, not LLM output). expected_topics
uses the exact 6 category names backend/api.py's research_topics()
literally returns (read from source, not guessed).

min_citations is deliberately conservative (1): POST /api/research/ask
depends on the live IndianKanoon API (external, requires
INDIANKANOON_API_KEY — see backend/document_analyzer.py's fetch_case_laws,
which returns a single "API key not configured" placeholder doc when the
key is absent). This project's evaluation environment does not have that
key configured (checked during the infra_health validation), so no
record here asserts a specific real citation COUNT — only citation
VALIDITY (do inline [N] markers point at citations actually returned) is
testable without an internet-dependent, non-reproducible live count.
"""

from __future__ import annotations

from evaluation.datasets.build.common import load_json, write_jsonl
from evaluation.datasets.schema import ResearchRecord

# category -> the research_topics() label it maps to, per backend/api.py's
# literal return value: [{"name": "Constitutional & Administrative", ...},
# {"name": "Criminal Law", ...}, {"name": "Civil & Property", ...},
# {"name": "Corporate & Commercial", ...}, {"name": "Tax Laws", ...},
# {"name": "Labour & Service", ...}]
_CATEGORY_TO_TOPIC = {
    "theft": "Criminal Law",
    "assault": "Criminal Law",
    "cybercrime": "Criminal Law",
    "domestic_violence": "Criminal Law",
    "property": "Civil & Property",
    "workplace": "Labour & Service",
}


def build() -> list[ResearchRecord]:
    kb = load_json("legal_kb.json")
    records = []
    for offence in kb["offences"]:
        topic = _CATEGORY_TO_TOPIC.get(offence["category"])
        query = f"Case law on {offence['offence_name'].lower()} under {offence['bns_section']}"
        records.append(ResearchRecord(
            id=f"research_{offence['id']}",
            tags=["legal_kb_grounded", offence["category"]],
            notes=(
                f"Source: data/legal_kb.json offence id='{offence['id']}' "
                f"(bns_section='{offence['bns_section']}', offence_name='{offence['offence_name']}'). "
                f"expected_topics uses the literal category label backend/api.py's "
                f"research_topics() returns. min_citations kept at 1 (not a claim of exact "
                f"real-world citation count) — see module docstring: this environment has no "
                f"INDIANKANOON_API_KEY configured, so no larger number would be reproducible."
            ),
            query=query,
            min_citations=1,
            expected_topics=[topic] if topic else [],
        ))
    return records


if __name__ == "__main__":
    recs = build()
    write_jsonl(recs, "research.jsonl")
    print(f"[BUILD] research: {len(recs)} queries grounded in data/legal_kb.json's 18 curated offences")
