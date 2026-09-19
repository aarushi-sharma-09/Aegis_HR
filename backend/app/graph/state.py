"""
LangGraph state for cross-document BGV verification.

Architecture:
  1. CV processed first → cv_profile stored in applicants.cv_profile (DB)
  2. EPFO verified AGAINST cv_profile (employer names, dates, UAN, gaps)
  3. Bank statement verified AGAINST cv_profile + epfo_findings
     (only when EPFO cannot confirm a CV-claimed employer)
"""

from typing import TypedDict, Optional, List, Dict, Any


class VerificationState(TypedDict):
    # ── Identity ──────────────────────────────────────────────────────────────
    thread_id: str
    applicant_id: str
    document_id: str
    document_type: str       # "cv_resume" | "epfo_history" | "bank_statement"
    document_url: str        # served by FastAPI /uploads/

    # ── Pipeline data ─────────────────────────────────────────────────────────
    raw_text: str            # OCR output
    masked_text: str         # post-masking
    pii_map: Dict[str, str]  # {"[MASKED_UAN_0]": "100987654321"} — no Redis needed

    # ── Extracted structured data (may contain masked tokens) ─────────────────
    extracted_data: dict

    # ── Cross-document reference ──────────────────────────────────────────────
    # For CV docs:   offer_reference_data from the applicants table (HR baseline)
    # For EPFO docs: cv_profile extracted from the previously-processed CV
    # For Bank docs: cv_profile + epfo_findings combined
    reference_data: dict

    # cv_profile is stored here after CV extraction so later EPFO/bank nodes
    # can access it (loaded from DB by the API and injected into state).
    cv_profile: Optional[Dict[str, Any]]    # full extracted CV data (demasked)
    epfo_findings: Optional[Dict[str, Any]] # summary from EPFO evaluation

    # ── Evaluation ────────────────────────────────────────────────────────────
    evaluation_result: str   # "PASSED" | "NEEDS_REVIEW" | "NEEDS_FALLBACK"
    discrepancies: List[Dict[str, Any]]
    reasoning: List[str]     # step-by-step log shown in admin dashboard

    # ── Human-in-the-loop ─────────────────────────────────────────────────────
    admin_decision: Optional[str]   # "APPROVED" | "REJECTED"
    admin_notes: Optional[str]

    # ── Final ─────────────────────────────────────────────────────────────────
    final_status: Optional[str]     # "VERIFIED" | "REJECTED" | "PENDING"
