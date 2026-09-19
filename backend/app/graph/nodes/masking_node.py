"""
Masking Node — Step 2 of the BGV pipeline.

Uses Regex for structured IDs (UAN, PAN, bank account, IFSC, Aadhaar)
and Presidio for general PII (names, emails, phones).

The pii_map is stored directly in LangGraph state — no external session store.

Includes a strict try/except fallback: if masking fails for any reason,
the pipeline continues with raw_text unchanged.
"""

import re
from typing import Dict, Tuple

from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

from app.graph.state import VerificationState

from presidio_analyzer.nlp_engine import NlpEngineProvider

# ─── Presidio setup (module-level singleton) ─────────────────────────────────
try:
    configuration = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]
    }
    provider = NlpEngineProvider(nlp_configuration=configuration)
    nlp_engine = provider.create_engine()
    
    _analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])
    _anonymizer = AnonymizerEngine()
    _presidio_available = True
except Exception:
    _presidio_available = False


# ─── Regex patterns ──────────────────────────────────────────────────────────
PATTERNS = [
    # (token_prefix, regex, description)
    ("MASKED_UAN",      r"\b\d{12}\b",                       "UAN (12-digit)"),
    ("MASKED_AADHAAR",  r"\b\d{4}\s?\d{4}\s?\d{4}\b",       "Aadhaar (12-digit with optional spaces)"),
    ("MASKED_PAN",      r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",       "PAN card"),
    ("MASKED_IFSC",     r"\b[A-Z]{4}0[A-Z0-9]{6}\b",        "IFSC code"),
    ("MASKED_ACCT",     r"\b\d{9,18}\b",                     "Bank account number (9-18 digits)"),
    # OCR often introduces spaces around @ or dots. We allow optional spaces.
    ("MASKED_EMAIL",    r"\b[A-Za-z0-9._%+-]+\s*@\s*[A-Za-z0-9.-]+\s*\.\s*[A-Z|a-z]{2,}\b", "Email"),
    ("MASKED_PHONE",    r"\b(?:\+91[-.\s]?)?[6-9]\d{9}\b",  "Indian mobile number"),
    # Compensate for the smaller spaCy model by explicitly capturing names that follow "Name:"
    ("MASKED_PERSON",   r"(?i)(?:name\s*:\s*)([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){0,2})", "Structured Name field"),
]


def _apply_regex_masking(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Apply all regex patterns in order.
    Returns (masked_text, pii_map).
    """
    pii_map: Dict[str, str] = {}
    counters: Dict[str, int] = {}

    for prefix, pattern, _ in PATTERNS:
        counters[prefix] = 0
        for match in re.finditer(pattern, text):
            # If pattern has a capture group, use it. Otherwise use the whole match.
            real_value = match.group(1) if match.lastindex else match.group()
            # Skip if this real value already has a token
            if real_value in pii_map.values():
                continue
            i = counters[prefix]
            token = f"[{prefix}_{i}]"
            pii_map[token] = real_value
            counters[prefix] += 1

        # Replace all occurrences with their tokens (build reverse map for this pass)
        for token, real_val in pii_map.items():
            if token.startswith(f"[{prefix}_"):
                text = text.replace(real_val, token)

    return text, pii_map


def masking_node(state: VerificationState) -> dict:
    """
    LangGraph node: masks PII in raw_text and returns masked_text + pii_map.

    Fallback contract: if ANY exception is raised during masking, we fall
    back to raw_text with an empty pii_map so the pipeline never breaks.
    """
    text = state.get("raw_text", "")
    reasoning = list(state.get("reasoning", []))

    reasoning.append("[MASK] Starting PII masking with Regex + Presidio")

    try:
        # ── Step 1: Regex masking for structured IDs ─────────────────────────
        masked_text, pii_map = _apply_regex_masking(text)

        masked_count = len(pii_map)
        reasoning.append(f"[MASK] Regex: masked {masked_count} structured identifiers")

        # ── Step 2: Presidio for names/general PII ───────────────────────────
        if _presidio_available and masked_text.strip():
            try:
                results = _analyzer.analyze(text=masked_text, language="en")
                name_results = [r for r in results if r.entity_type == "PERSON"]

                name_counter = len([k for k in pii_map if k.startswith("[MASKED_PERSON_")])
                for r in name_results:
                    real_val = masked_text[r.start:r.end]
                    if real_val in pii_map.values() or real_val.startswith("["):
                        continue  # already masked
                    token = f"[MASKED_PERSON_{name_counter}]"
                    pii_map[token] = real_val
                    masked_text = masked_text.replace(real_val, token)
                    name_counter += 1

                reasoning.append(f"[MASK] Presidio: masked {len(name_results)} person names")
            except Exception as presidio_err:
                reasoning.append(f"[MASK] Presidio skipped: {str(presidio_err)}")
        else:
            reasoning.append("[MASK] Presidio not applied (not available or empty text)")

        total = len(pii_map)
        reasoning.append(f"[MASK] Complete. Total tokens created: {total}")
        return {"masked_text": masked_text, "pii_map": pii_map, "reasoning": reasoning}

    except Exception as e:
        # ── Graceful fallback ────────────────────────────────────────────────
        reasoning.append(
            f"[MASK] Masking failed: {str(e)} — falling back to raw text (pipeline continues)"
        )
        return {"masked_text": text, "pii_map": {}, "reasoning": reasoning}
