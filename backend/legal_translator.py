# -*- coding: utf-8 -*-
"""
legal_translator.py — Legal Document Translation for Nyaya-Setu
NyayaSetu | Team IKS | SPIT CSE 2025-26

Translation Priority:
  1. Colab NLLB model  (via local_models.py HTTP client — no local GPU needed)
  2. Google Gemini 2.5 Flash  (if Colab/NLLB unavailable, chunked for large docs)
  3. Groq Llama 3.3 70B       (final fallback)

Language Detection : Unicode script range → Groq LLM confirmation
Legal Term Analysis: Groq  (post-translation, samples full doc)
FIR Summary        : Groq  (structured 8-point summary from full translation)

Supports: Marathi, Hindi, Tamil, Telugu, Kannada, Bengali, Gujarati,
           Malayalam, Punjabi, Odia, Assamese, Urdu
"""

import os, re, json, time as _time
import sys
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from google.genai import types
from ai_clients import groq_client, GROQ_MODEL, GEMINI_MODEL, get_gemini_client

logger = logging.getLogger(__name__)

# ── Clients & config ──────────────────────────────────────────────────────────
GEMINI_CHUNK_CHARS = 30_000

GROQ_TRANSLATION_MODEL     = "llama-3.3-70b-versatile"
GROQ_TRANSLATE_CHUNK_CHARS = 2500

_gemini_client = get_gemini_client()

# ── Language tables ───────────────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "mr": "Marathi",   "hi": "Hindi",     "ta": "Tamil",
    "te": "Telugu",    "kn": "Kannada",   "bn": "Bengali",
    "gu": "Gujarati",  "ml": "Malayalam", "pa": "Punjabi",
    "or": "Odia",      "as": "Assamese",  "ur": "Urdu",
    "en": "English",
}

GEMINI_LANGS = {
    "mr": "Marathi", "hi": "Hindi", "ta": "Tamil", "te": "Telugu",
    "kn": "Kannada", "bn": "Bengali", "gu": "Gujarati", "ml": "Malayalam",
    "pa": "Punjabi", "or": "Odia", "as": "Assamese", "ur": "Urdu",
    "en": "English",
}

SCRIPT_RANGES = {
    "mr": [(0x0900, 0x097F)],
    "hi": [(0x0900, 0x097F)],
    "ta": [(0x0B80, 0x0BFF)],
    "te": [(0x0C00, 0x0C7F)],
    "kn": [(0x0C80, 0x0CFF)],
    "bn": [(0x0980, 0x09FF)],
    "gu": [(0x0A80, 0x0AFF)],
    "ml": [(0x0D00, 0x0D7F)],
    "pa": [(0x0A00, 0x0A7F)],
    "or": [(0x0B00, 0x0B7F)],
    "as": [(0x0980, 0x09FF)],
    "ur": [(0x0600, 0x06FF), (0xFB50, 0xFDFF)],
}


# ── Utilities ─────────────────────────────────────────────────────────────────
def _split_into_chunks(text: str, max_chars: int) -> list[str]:
    lines = text.split("\n")
    chunks, current = [], ""
    for line in lines:
        candidate = (current + "\n" + line).strip() if current else line
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(line) > max_chars:
                sentences = re.split(r'(?<=[।.!?])\s+', line)
                current = ""
                for sent in sentences:
                    trial = (current + " " + sent).strip() if current else sent
                    if len(trial) <= max_chars:
                        current = trial
                    else:
                        if current:
                            chunks.append(current)
                        current = sent[:max_chars]
            else:
                current = line
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


def _groq_call(prompt: str, max_tokens: int = 1200, temperature: float = 0.1) -> str:
    resp = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


# ── Language detection ────────────────────────────────────────────────────────
def detect_script(text: str) -> str:
    counts: dict[str, int] = {}
    for ch in text:
        cp = ord(ch)
        for lang, ranges in SCRIPT_RANGES.items():
            for lo, hi in ranges:
                if lo <= cp <= hi:
                    counts[lang] = counts.get(lang, 0) + 1
                    break
    return max(counts, key=counts.get) if counts else "en"


def detect_language_with_llm(text: str) -> dict:
    sample = text[:500]
    prompt = (
        "Identify the language of this Indian legal document text.\n"
        "Reply with ONLY a JSON object, no other text.\n\n"
        f"TEXT:\n{sample}\n\n"
        '{"language_code": "mr", "language_name": "Marathi", "confidence": 95}\n\n'
        "Codes: mr=Marathi, hi=Hindi, ta=Tamil, te=Telugu, kn=Kannada, "
        "bn=Bengali, gu=Gujarati, ml=Malayalam, pa=Punjabi, or=Odia, "
        "as=Assamese, ur=Urdu, en=English"
    )
    try:
        raw = _groq_call(prompt, max_tokens=100, temperature=0.0)
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        logger.warning("[TRANSLATOR] LLM language detection failed: %s", e)

    code = detect_script(text)
    return {
        "language_code": code,
        "language_name": SUPPORTED_LANGUAGES.get(code, "Unknown"),
        "confidence": 60,
    }


# ── Gemini translation ────────────────────────────────────────────────────────
_GEMINI_SYSTEM_PROMPT = (
    "You are a certified court interpreter and legal translator specialised in Indian law. "
    "Your ONLY task is to produce a faithful, verbatim translation of the source document. "
    "STRICT RULES — violation is not permitted:\n"
    "  1. Translate EVERY sentence. Do NOT skip, summarise, or paraphrase.\n"
    "  2. Preserve all proper nouns, personal names, addresses, and dates EXACTLY as in the source.\n"
    "  3. Preserve all section numbers, act names, and legal references without alteration.\n"
    "  4. Maintain the formal, impersonal legal register of the original.\n"
    "  5. Output ONLY the translated text — no preamble, no commentary, no explanations."
)


def _gemini_call_single(chunk: str, src_lang: str, tgt_lang: str) -> str:
    src_name = GEMINI_LANGS.get(src_lang, src_lang)
    tgt_name = GEMINI_LANGS.get(tgt_lang, tgt_lang)
    user_prompt = (
        f"Translate the following legal document excerpt from {src_name} to {tgt_name}.\n"
        "This may be part of a larger document — translate ALL lines completely.\n\n"
        f"SOURCE TEXT ({src_name}):\n{chunk}"
    )

    last_err = None
    for attempt in range(1, 4):
        try:
            response = _gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_GEMINI_SYSTEM_PROMPT,
                    temperature=0.0,
                    max_output_tokens=16384,
                ),
            )
            translated = (response.text or "").strip()
            if not translated:
                raise ValueError("Gemini returned an empty translation for this chunk.")
            return translated
        except Exception as e:
            last_err = e
            msg = str(e)
            if any(code in msg for code in ("503", "429", "500", "UNAVAILABLE", "rate_limit")):
                wait = 5 * attempt
                logger.warning("[TRANSLATOR] Gemini transient error (attempt %d/3): %s. Retrying in %ds...",
                                attempt, msg[:80], wait)
                _time.sleep(wait)
            else:
                break

    raise ValueError(f"Gemini failed after retries: {last_err}")


def _gemini_translate(text: str, src_lang: str, tgt_lang: str) -> tuple[str, float]:
    if not _gemini_client:
        raise ValueError("GEMINI_API_KEY not set in .env")

    src_name = GEMINI_LANGS.get(src_lang, src_lang)
    tgt_name = GEMINI_LANGS.get(tgt_lang, tgt_lang)

    if len(text) > GEMINI_CHUNK_CHARS:
        chunks = _split_into_chunks(text, GEMINI_CHUNK_CHARS)
        logger.info("[TRANSLATOR] Gemini: %d chars -> %d chunks (%s -> %s)",
                     len(text), len(chunks), src_name, tgt_name)
        parts = []
        for i, chunk in enumerate(chunks, 1):
            logger.info("[TRANSLATOR] Gemini chunk %d/%d (%d chars)...", i, len(chunks), len(chunk))
            try:
                parts.append(_gemini_call_single(chunk, src_lang, tgt_lang))
            except Exception as e:
                raise ValueError(f"Gemini chunk {i}/{len(chunks)} failed: {e}")
        full = "\n\n".join(parts)
        logger.info("[TRANSLATOR] Gemini OK — %d chars (chunked)", len(full))
        return full, 95.0

    logger.info("[TRANSLATOR] Gemini: %d chars (%s -> %s)...", len(text), src_name, tgt_name)
    try:
        out = _gemini_call_single(text, src_lang, tgt_lang)
        logger.info("[TRANSLATOR] Gemini OK — %d chars", len(out))
        return out, 95.0
    except Exception as e:
        logger.error("[TRANSLATOR] Gemini API error: %s", e)
        raise ValueError(f"Gemini translation failed: {e}")


# ── Groq fallback translation ─────────────────────────────────────────────────
def _groq_translate(text: str, src_name: str, tgt_name: str, document_type: str) -> tuple[str, float]:
    if len(text) > GROQ_TRANSLATE_CHUNK_CHARS:
        chunks = _split_into_chunks(text, GROQ_TRANSLATE_CHUNK_CHARS)
        logger.info("[TRANSLATOR] Groq fallback: %d chars -> %d chunks", len(text), len(chunks))
        parts, min_conf = [], 100.0
        for i, chunk in enumerate(chunks, 1):
            t, c = _groq_translate(chunk, src_name, tgt_name, document_type)
            if t:
                parts.append(t)
            min_conf = min(min_conf, c)
            if i < len(chunks):
                _time.sleep(2)
        return "\n\n".join(parts), min_conf

    prompt = (
        f"Translate the following {document_type} excerpt from {src_name} to {tgt_name}.\n"
        "Preserve all legal terms, section numbers, act names, and proper nouns.\n"
        "Output ONLY the translated text, no explanations.\n\n"
        f"SOURCE TEXT:\n{text}"
    )
    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_TRANSLATION_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=3000,
        )
        translated = resp.choices[0].message.content.strip()
        logger.info("[TRANSLATOR] Groq chunk OK — %d chars", len(translated))
        return translated, 75.0
    except Exception as e:
        logger.error("[TRANSLATOR] Groq fallback failed: %s", e)
        return "", 0.0


# ── Post-processing helpers ───────────────────────────────────────────────────
def _extract_legal_terms(original: str, translated: str, src_name: str) -> list[str]:
    def _sample(t: str, total: int = 2400) -> str:
        if len(t) <= total:
            return t
        third = total // 3
        mid = max(0, len(t) // 2 - third // 2)
        return t[:third] + "\n...\n" + t[mid: mid + third] + "\n...\n" + t[-third:]

    prompt = (
        f"You are a legal analyst. Given this {src_name} -> English translation of a legal document, "
        "list the key legal terms that appear in the English translation. "
        "Include section numbers, act names, legal roles (Complainant, Accused, etc.), and legal procedures.\n\n"
        f"ORIGINAL ({src_name}):\n{_sample(original)}\n\n"
        f"ENGLISH TRANSLATION:\n{_sample(translated)}\n\n"
        'Reply with ONLY a JSON array of strings, e.g. ["Section 302", "Bharatiya Nyaya Sanhita", "Complainant"]'
    )
    try:
        raw = _groq_call(prompt, max_tokens=400, temperature=0.0)
        m = re.search(r'\[.*\]', raw, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception as e:
        logger.warning("[TRANSLATOR] Legal term extraction failed: %s", e)
    return []


def _generate_fir_summary(translated_text: str, src_name: str) -> str:
    body = translated_text[:6_000]
    prompt = (
        f"You are an expert Indian legal analyst. The following is the COMPLETE English translation "
        f"of a {src_name} First Information Report (FIR) / legal complaint.\n\n"
        "Read the ENTIRE text and produce a structured summary covering:\n"
        "  1. Document Type & Police Station\n"
        "  2. Complainant details (name, age, address)\n"
        "  3. Accused details (name / description / count)\n"
        "  4. Incident — what happened, when, where (date, time, location)\n"
        "  5. Offences / Sections invoked (list every BNS / IPC / other section)\n"
        "  6. Key evidence mentioned\n"
        "  7. Witness names (if any)\n"
        "  8. Action taken / next steps\n\n"
        "Be factual. Use ONLY what is in the document. "
        "If a field is absent, write 'Not mentioned'.\n"
        "Format as a clean numbered list matching the headings above.\n\n"
        f"FULL TRANSLATED FIR:\n{body}"
    )
    try:
        return _groq_call(prompt, max_tokens=800, temperature=0.1)
    except Exception as e:
        logger.warning("[TRANSLATOR] FIR summary generation failed: %s", e)
        return ""


# ── Shared result builders ────────────────────────────────────────────────────
def _ok_result(
    translated_text, fir_summary, source_lang, src_name,
    target_lang, tgt_name, legal_terms, confidence,
    detection_confidence, notes, engine, original_char_count,
) -> dict:
    return {
        "translated_text":       translated_text,
        "fir_summary":           fir_summary,
        "source_language":       source_lang,
        "source_language_name":  src_name,
        "target_language":       target_lang,
        "target_language_name":  tgt_name,
        "legal_terms_preserved": legal_terms,
        "confidence":            confidence,
        "detection_confidence":  detection_confidence,
        "notes":                 notes,
        "engine":                engine,
        "char_count_original":   original_char_count,
        "char_count_translated": len(translated_text),
    }


def _error_result(source_lang: str, target_lang: str, msg: str) -> dict:
    return {
        "translated_text":       "",
        "fir_summary":           "",
        "source_language":       source_lang,
        "source_language_name":  SUPPORTED_LANGUAGES.get(source_lang, source_lang),
        "target_language":       target_lang,
        "target_language_name":  SUPPORTED_LANGUAGES.get(target_lang, target_lang),
        "legal_terms_preserved": [],
        "confidence":            0,
        "detection_confidence":  0,
        "notes":                 msg,
        "engine":                "error",
        "error":                 msg,
        "char_count_original":   0,
        "char_count_translated": 0,
    }


# ── Core public function ──────────────────────────────────────────────────────
def translate_legal_text(
    text: str,
    source_lang: str = None,
    target_lang: str = "en",
    document_type: str = "FIR / Police Complaint",
) -> dict:
    """
    Translate an entire legal document.

    Priority:
      1. Colab NLLB (via local_models.translate_chunks_nllb → HTTP)
      2. Google Gemini 2.5 Flash
      3. Groq Llama 3.3 70B

    Returns a dict with keys:
        translated_text, fir_summary, source_language, source_language_name,
        target_language, target_language_name, legal_terms_preserved,
        confidence, detection_confidence, notes, engine,
        char_count_original, char_count_translated
    """
    if not text or not text.strip():
        return _error_result("", "en", "Empty text provided.")

    _stage_start = _time.time()
    logger.info("[TRANSLATOR] STAGE ENTER — translate_legal_text: %d chars, %s -> %s",
                len(text), source_lang or "auto", target_lang)

    # ── Step 1: Language detection ─────────────────────────────────────────────
    if not source_lang or source_lang == "auto":
        detection = detect_language_with_llm(text)
        source_lang = detection["language_code"]
        src_name = detection["language_name"]
        detection_confidence = detection.get("confidence", 60)
    else:
        src_name = SUPPORTED_LANGUAGES.get(source_lang, source_lang)
        detection_confidence = 100

    tgt_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)

    # Already in target language — return as-is
    if source_lang == target_lang:
        logger.info("[TRANSLATOR] STAGE EXIT — already in target language, no translation needed (%.2fs)",
                    _time.time() - _stage_start)
        return _ok_result(
            translated_text=text,
            fir_summary="",
            source_lang=source_lang,
            src_name=src_name,
            target_lang=target_lang,
            tgt_name=tgt_name,
            legal_terms=[],
            confidence=100,
            detection_confidence=detection_confidence,
            notes="Text is already in the target language.",
            engine="none",
            original_char_count=len(text),
        )

    # ── Step 2: Translate (Colab NLLB → Gemini → Groq) ────────────────────────
    translated_text, confidence, engine, notes = "", 0.0, "error", ""

    # ── 2a. Try Colab NLLB (fastest, no API cost) ─────────────────────────────
    from local_models import translate_chunks_nllb, NLLB_LANG_MAP
    if source_lang in NLLB_LANG_MAP and target_lang in NLLB_LANG_MAP:
        try:
            logger.info("[TRANSLATOR] Using Colab NLLB (%s -> %s)...", src_name, tgt_name)
            translated_text = translate_chunks_nllb(
                text, src_lang=source_lang, tgt_lang=target_lang
            )
            if translated_text:
                confidence = 88.0
                engine     = "nllb-colab"
                notes      = (
                    f"Translated via Colab NLLB-200 model · "
                    f"{src_name} -> {tgt_name}"
                )
                logger.info("[TRANSLATOR] Colab NLLB OK — %d chars", len(translated_text))
            else:
                logger.warning("[TRANSLATOR] Colab NLLB returned empty — trying Gemini...")
        except Exception as nllb_err:
            logger.warning("[TRANSLATOR] Colab NLLB failed (%s), trying Gemini...", nllb_err)
            translated_text = ""

    # ── 2b. Fallback to Gemini ─────────────────────────────────────────────────
    if not translated_text:
        engine = GEMINI_MODEL
        notes  = f"Translated using Google Gemini ({GEMINI_MODEL}) · {src_name} -> {tgt_name}"
        try:
            translated_text, confidence = _gemini_translate(text, source_lang, target_lang)
        except Exception as e:
            logger.warning("[TRANSLATOR] Gemini failed (%s), falling back to Groq (%s)...", e, GROQ_MODEL)
            engine = f"groq-{GROQ_MODEL}"
            notes  = f"Gemini unavailable — used Groq fallback ({GROQ_MODEL}) · {src_name} -> {tgt_name}"
            translated_text, confidence = _groq_translate(
                text, src_name, tgt_name, document_type
            )
            if not translated_text:
                logger.error("[TRANSLATOR] STAGE EXIT — all engines failed (%.2fs): %s",
                             _time.time() - _stage_start, e)
                return _error_result(source_lang, target_lang, f"All engines failed: {e}")

    # ── Step 3: Post-processing ────────────────────────────────────────────────
    logger.info("[TRANSLATOR] Extracting legal terms from full document...")
    legal_terms = _extract_legal_terms(text, translated_text, src_name)

    fir_summary = ""
    if target_lang == "en":
        logger.info("[TRANSLATOR] Generating structured FIR summary...")
        fir_summary = _generate_fir_summary(translated_text, src_name)

    logger.info("[TRANSLATOR] STAGE EXIT — engine=%s confidence=%.0f%% (%.2fs)",
                engine, confidence, _time.time() - _stage_start)
    return _ok_result(
        translated_text=translated_text,
        fir_summary=fir_summary,
        source_lang=source_lang,
        src_name=src_name,
        target_lang=target_lang,
        tgt_name=tgt_name,
        legal_terms=legal_terms,
        confidence=confidence,
        detection_confidence=detection_confidence,
        notes=notes,
        engine=engine,
        original_char_count=len(text),
    )


# ── Convenience wrappers ──────────────────────────────────────────────────────
def translate_fir(text: str, source_lang: str = None) -> dict:
    return translate_legal_text(
        text=text,
        source_lang=source_lang,
        document_type="FIR / First Information Report (Police Complaint)",
    )


def get_supported_languages() -> list[dict]:
    return [
        {"code": code, "name": name}
        for code, name in SUPPORTED_LANGUAGES.items()
        if code != "en"
    ]


# ── CLI test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sample_marathi = """
    प्रथम खबर अहवाल (FIR)
    पोलीस ठाणे: अंधेरी पूर्व, मुंबई

    फिर्यादी: श्री. राजेश पाटील, वय ३५ वर्षे

    घटनेचा तपशील:
    दिनांक १५/०३/२०२५ रोजी रात्री ९:३० वाजता दोन अज्ञात व्यक्तींनी
    माझा मोबाईल फोन हिसकावून घेतला.

    कलम: भारतीय न्याय संहिता (BNS) कलम ३०४
    """

    print("Testing Colab NLLB → Gemini → Groq translation pipeline...")
    result = translate_fir(sample_marathi)
    SEP = "=" * 60
    print(f"\n{SEP}")
    print(f"Engine             : {result['engine']}")
    print(f"Source             : {result['source_language_name']}")
    print(f"Confidence         : {result['confidence']}%")
    print(f"Chars (orig/trans) : {result['char_count_original']} / {result['char_count_translated']}")
    print(f"\n── Full Translation {'─'*40}")
    print(result["translated_text"])
    print(f"\nNotes: {result['notes']}")
