"""
Human Review Node — interrupt point in the BGV pipeline.

Calls LangGraph's interrupt() to pause execution.
State (including discrepancies, reasoning, pii_map) is persisted
in Postgres via AsyncPostgresSaver.

The admin dashboard reads the paused state and renders the review UI.
When the admin submits a decision, the /api/resolve-review endpoint
injects admin_decision into state and resumes the graph.
"""

from langgraph.types import interrupt

from app.graph.state import VerificationState


def human_review_node(state: VerificationState) -> dict:
    """
    LangGraph node: pauses the graph and waits for admin input.

    The interrupt() call causes LangGraph to:
    1. Persist current state to the Postgres checkpointer
    2. Return control to the caller (the FastAPI endpoint)
    3. Resume when graph.aupdate_state() + graph.ainvoke() are called
    """
    reasoning = list(state.get("reasoning", []))
    discrepancies = state.get("discrepancies", [])

    reasoning.append(
        f"[REVIEW] Graph paused — awaiting admin decision. "
        f"{len(discrepancies)} discrepancies flagged for review."
    )

    # interrupt() pauses the graph here. The value passed is available
    # to the caller via GraphInterrupt.args[0] (used for display purposes).
    interrupt({
        "message": "Human review required",
        "discrepancy_count": len(discrepancies),
        "evaluation_result": state.get("evaluation_result"),
    })

    # ── Execution resumes here after admin submits decision ──────────────────
    admin_decision = state.get("admin_decision")
    reasoning.append(f"[REVIEW] Admin decision received: {admin_decision}")

    return {"reasoning": reasoning}
