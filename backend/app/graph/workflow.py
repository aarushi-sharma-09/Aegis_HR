"""
LangGraph Workflow — wires all nodes into a compiled graph.

Flow:
  ocr → mask_pii → extract → evaluate → [demask | human_review | fallback]
  human_review → [demask | END]  (based on admin_decision)

Checkpointing: AsyncPostgresSaver persists the full VerificationState
(including pii_map) after every node — no Redis required.
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.graph.state import VerificationState
from app.graph.nodes.ocr_node import ocr_node
from app.graph.nodes.masking_node import masking_node
from app.graph.nodes.extraction_node import extraction_node
from app.graph.nodes.evaluation_node import evaluation_node
from app.graph.nodes.demasking_node import demasking_node
from app.graph.nodes.human_review_node import human_review_node
from app.graph.nodes.fallback_node import fallback_node
from app.config import settings


# ─── Routing functions ────────────────────────────────────────────────────────

def route_evaluation(state: VerificationState) -> str:
    result = state.get("evaluation_result", "NEEDS_REVIEW")
    return result  # "PASSED" | "NEEDS_REVIEW" | "NEEDS_FALLBACK"


def route_admin_decision(state: VerificationState) -> str:
    decision = state.get("admin_decision", "REJECTED")
    return "APPROVED" if decision == "APPROVED" else "REJECTED"


# ─── Graph builder ────────────────────────────────────────────────────────────

def build_graph_definition() -> StateGraph:
    """Returns the StateGraph (not yet compiled — needs a checkpointer)."""
    g = StateGraph(VerificationState)

    # Register nodes
    g.add_node("ocr", ocr_node)
    g.add_node("mask_pii", masking_node)
    g.add_node("extract", extraction_node)
    g.add_node("evaluate", evaluation_node)
    g.add_node("demask", demasking_node)
    g.add_node("human_review", human_review_node)
    g.add_node("trigger_fallback", fallback_node)

    # Entry point
    g.set_entry_point("ocr")

    # Linear path
    g.add_edge("ocr", "mask_pii")
    g.add_edge("mask_pii", "extract")
    g.add_edge("extract", "demask")
    g.add_edge("demask", "evaluate")

    # Conditional routing after evaluation
    g.add_conditional_edges(
        "evaluate",
        route_evaluation,
        {
            "PASSED": END,
            "NEEDS_REVIEW": "human_review",
            "NEEDS_FALLBACK": "trigger_fallback",
        },
    )

    # After admin review
    g.add_conditional_edges(
        "human_review",
        route_admin_decision,
        {
            "APPROVED": END,
            "REJECTED": END,
        },
    )

    # Terminal nodes
    g.add_edge("trigger_fallback", END)

    return g


async def create_compiled_graph(checkpointer: AsyncPostgresSaver):
    """
    Compiles the graph with a Postgres checkpointer.
    Call once during FastAPI lifespan startup.
    """
    graph_def = build_graph_definition()
    return graph_def.compile(checkpointer=checkpointer)
