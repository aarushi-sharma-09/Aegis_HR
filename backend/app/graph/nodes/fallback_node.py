"""
Fallback Node — handles cases where the document is insufficient.

Instead of sending an email, this node sets the document status to
NEEDS_FALLBACK and the admin manually triggers a re-upload from the
dashboard.
"""

from app.graph.state import VerificationState


def fallback_node(state: VerificationState) -> dict:
    """
    LangGraph node: marks document as pending manual evidence upload.
    Admin sees this in the review queue and can upload additional docs.
    """
    reasoning = list(state.get("reasoning", []))
    discrepancies = state.get("discrepancies", [])

    reasoning.append(
        "[FALLBACK] Insufficient document evidence detected. "
        "Setting status to PENDING — admin must upload additional evidence."
    )
    reasoning.append(
        f"[FALLBACK] Flagged discrepancies: "
        + ", ".join(d.get("field", "unknown") for d in discrepancies)
    )
    reasoning.append(
        "[FALLBACK] Action required: Upload supporting document via dashboard re-upload."
    )

    return {
        "final_status": "PENDING",
        "reasoning": reasoning,
    }
