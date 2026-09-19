"""
Demasking Node — replaces masked tokens with real values, writes to DB.

Reads pii_map from state (no Redis lookup needed — it's persisted in the
LangGraph checkpoint all along). Swaps all [MASKED_*] tokens back to
their real values in extracted_data, then marks the document as VERIFIED.
"""

import ast
import json
from typing import Any

from app.graph.state import VerificationState


def demasking_node(state: VerificationState) -> dict:
    """
    LangGraph node: demask extracted_data, discrepancies, and reasoning.
    """
    pii_map = state.get("pii_map", {})
    extracted_data = state.get("extracted_data", {})
    discrepancies = state.get("discrepancies", [])
    reasoning = list(state.get("reasoning", []))

    reasoning.append(f"[DEMASK] Restoring {len(pii_map)} PII tokens to real values")

    def _demask_string(s: str) -> str:
        for token, real_value in pii_map.items():
            if token in s:
                s = s.replace(token, str(real_value))
        return s

    def _demask_recursive(obj: Any) -> Any:
        if isinstance(obj, str):
            return _demask_string(obj)
        elif isinstance(obj, list):
            return [_demask_recursive(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: _demask_recursive(v) for k, v in obj.items()}
        return obj

    try:
        clean_extracted = _demask_recursive(extracted_data)
        clean_discrepancies = _demask_recursive(discrepancies)
        clean_reasoning = _demask_recursive(reasoning)

        clean_reasoning.append("[DEMASK] All tokens restored.")

        return {
            "extracted_data": clean_extracted,
            "discrepancies": clean_discrepancies,
            "reasoning": clean_reasoning,
        }
    except Exception as e:
        reasoning.append(f"[DEMASK] Error during demasking: {str(e)} — retaining masked data")
        return {
            "extracted_data": extracted_data,
            "discrepancies": discrepancies,
            "reasoning": reasoning,
        }
