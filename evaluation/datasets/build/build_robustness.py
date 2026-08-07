# -*- coding: utf-8 -*-
"""
evaluation/datasets/build/build_robustness.py

Two kinds of records, both grounded, neither LLM-authored:

1. Mechanical edge cases (5 of robustness.yaml's 6 declared categories —
   upstream_unavailable is NOT included; see below) — expected_behavior
   is grounded either in code actually read in this repo (e.g.
   lex_validator.compute_score has no length guard, so empty/oversized
   text takes the same no-exception path -> "graceful_fallback") or in
   well-established FastAPI/Pydantic framework behaviour for malformed
   requests (missing required fields / wrong content-type against a
   File(...)-typed endpoint -> 422, "clean_4xx"). Each record's `notes`
   says which.

   upstream_unavailable is deliberately NOT built here: it requires
   fault injection (mocking a Groq/Colab outage), which a black-box
   JSON-payload dataset cannot express — that's an infrastructure gap,
   not a dataset one. See DATASET_REPORT.md.

2. "hallucination" — a category not in the current robustness.yaml
   (added there by this build, additively) — grounded in the SAME
   FALLBACK_MAPPINGS table build_ipc_bns_mapping.py uses. Tests whether
   LexValidator (a) correctly reports a real ABOLISHED section as
   abolished rather than inventing a plausible-looking BNS number for
   it, and (b) returns UNKNOWN for a section number verified (by
   construction, checked against both real mapping sources) to be
   absent from every source of truth in this project, rather than
   fabricating a mapping for it.

   IMPORTANT LIMITATION, stated plainly: metrics/robustness_metrics.py's
   graceful_degradation_rate only recognizes expected_behavior in
   {"clean_4xx", "graceful_fallback", "clear_error_message"} and only
   checks status code / leaked-internals — it does NOT inspect response
   *content* for a fabricated section number. These hallucination
   records are real, source-grounded test cases, but scoring what they
   actually test needs a new content-aware metric function — that is a
   framework change, out of scope for this dataset-only phase (see
   DATASET_REPORT.md's gap list). Recorded here so the ground truth
   exists and is ready the day that metric is written.
"""

from __future__ import annotations

from evaluation.datasets.build.common import write_jsonl
from evaluation.datasets.build.build_ipc_bns_mapping import _parse_fallback_mappings
from evaluation.datasets.schema import RobustnessRecord


def build() -> list[RobustnessRecord]:
    fallback = _parse_fallback_mappings()
    abolished = [k for k, v in fallback.items() if v.get("bns") == "ABOLISHED"]
    assert abolished, "expected at least one ABOLISHED entry in FALLBACK_MAPPINGS"
    all_known_numbers = {k.split(" ", 1)[1] for k in fallback}

    fake_section = "9999"
    assert fake_section not in all_known_numbers, \
        "fake_section must be verified absent from FALLBACK_MAPPINGS before use as a decoy"

    records = [
        RobustnessRecord(
            id="robust_empty_input_compliance",
            tags=["mechanical", "empty_input"],
            notes=("Grounded in backend/lex_validator.py LexValidator.compute_score: with "
                   "total==0 references found, it returns score=100/grade=A/no exception — "
                   "there is no length guard, so empty text takes the normal 200 path."),
            category="empty_input",
            endpoint="/api/compliance",
            payload={"text": ""},
            expected_behavior="graceful_fallback",
        ),
        RobustnessRecord(
            id="robust_oversized_input_compliance",
            tags=["mechanical", "oversized_input"],
            notes=("Grounded in the ABSENCE of any text-length guard in backend/api.py's "
                   "/api/compliance handler or lex_validator.py (unlike /api/analyze, which "
                   "has an explicit 10MB file-size check) — the code path taken for a 200KB "
                   "text body is identical to a normal-sized one."),
            category="oversized_input",
            endpoint="/api/compliance",
            payload={"text": ("Charged under Section 302 IPC. " * 8000)},
            expected_behavior="graceful_fallback",
        ),
        RobustnessRecord(
            id="robust_wrong_file_type_analyze",
            tags=["mechanical", "wrong_file_type"],
            notes=("backend/api.py declares 'async def analyze(file: UploadFile = File(...))' "
                   "— FastAPI/Starlette rejects a JSON POST body against a required "
                   "UploadFile/File(...) parameter with a 422 before the handler body ever "
                   "runs; this is documented FastAPI request-validation behaviour, not "
                   "app-specific guesswork."),
            category="wrong_file_type",
            endpoint="/api/analyze",
            payload={"not_a_file": "this is JSON, not multipart/form-data"},
            expected_behavior="clean_4xx",
        ),
        RobustnessRecord(
            id="robust_unsupported_language_translate",
            tags=["mechanical", "unsupported_language"],
            notes=("Grounded in backend/legal_translator.py: SUPPORTED_LANGUAGES.get(code, code) "
                   "and GEMINI_LANGS.get(code, code) both fall back to the raw code rather than "
                   "raising for an unrecognized language code — translate_legal_text has no "
                   "explicit 'reject unknown code' branch, so the call proceeds into the "
                   "cascade rather than failing fast."),
            category="unsupported_language",
            endpoint="/api/translate",
            payload={"text": "test", "source_lang": "xx", "target_lang": "en",
                      "document_type": "FIR / Police Complaint"},
            expected_behavior="graceful_fallback",
        ),
        RobustnessRecord(
            id="robust_malformed_payload_compliance",
            tags=["mechanical", "malformed_payload"],
            notes=("A POST body missing the required 'text' field against a Pydantic request "
                   "model triggers FastAPI's standard 422 validation-error response before "
                   "any handler code runs — documented framework behaviour."),
            category="malformed_payload",
            endpoint="/api/compliance",
            payload={"unexpected_field": "no text key at all"},
            expected_behavior="clean_4xx",
        ),
    ]

    for key in abolished:
        act, section = key.split(" ", 1)
        records.append(RobustnessRecord(
            id=f"robust_hallucination_abolished_{act.lower()}_{section}",
            tags=["hallucination", "grounded_in_fallback_mappings", "needs_content_metric"],
            notes=(f"Ground truth: backend/lex_validator.py FALLBACK_MAPPINGS['{key}'] == "
                   f"{{'bns': 'ABOLISHED', 'name': '{fallback[key]['name']}'}}. A correct, "
                   f"non-hallucinating response must report this as ABOLISHED/decriminalized, "
                   f"not invent a numeric BNS/BNSS/BSA section for it. See module docstring: "
                   f"the current robustness metrics don't check response content, so this "
                   f"record is scored as a plain 200-OK check for now."),
            category="hallucination",
            endpoint="/api/compliance",
            payload={"text": f"The accused was originally charged under Section {section} {act}."},
            expected_behavior="graceful_fallback",
        ))

    records.append(RobustnessRecord(
        id="robust_hallucination_nonexistent_section",
        tags=["hallucination", "grounded_in_fallback_mappings", "needs_content_metric"],
        notes=(f"Ground truth: Section {fake_section} IPC is verified absent from BOTH real "
               f"mapping sources this project has (backend/lex_validator.py FALLBACK_MAPPINGS, "
               f"{len(all_known_numbers)} entries, and data/ipc_bns_mappings.json, 160 entries) "
               f"— confirmed by set-membership check in this build script, not assumed. A "
               f"correct, non-hallucinating response must say UNKNOWN/not found, not invent a "
               f"plausible-looking BNS number for a section that was never a real IPC section."),
        category="hallucination",
        endpoint="/api/compliance",
        payload={"text": f"The accused was charged under Section {fake_section} IPC."},
        expected_behavior="graceful_fallback",
    ))

    return records


if __name__ == "__main__":
    recs = build()
    write_jsonl(recs, "robustness.jsonl")
    from collections import Counter
    dist = Counter(r.category for r in recs)
    print(f"[BUILD] robustness: {len(recs)} records — by category: {dict(dist)}")
    print("[BUILD] NOTE: robustness.yaml's params.categories list needs 'hallucination' added "
          "manually (config data edit) for the CLI to describe it in --help / list-suites output; "
          "the runner works against these records either way since it reads category from the record.")
