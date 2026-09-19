"""
Documents API — handles file upload and BGV pipeline trigger.

Upload flow per document type:
  cv_resume:      Starts pipeline. On PASSED, stores extracted cv_profile in
                  applicants.cv_profile for subsequent EPFO/bank cross-verification.
  epfo_history:   Loads cv_profile as reference_data → EPFO cross-verified against CV.
  bank_statement: Loads cv_profile + epfo_findings → bank cross-verified against both.

Endpoints:
  POST /api/documents/upload
  POST /api/documents/fallback-upload/{document_id}
"""

import uuid
import shutil
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.database import get_db, Document, Applicant, VerificationResult

router = APIRouter(prefix="/api/documents", tags=["documents"])

VALID_TYPES = {"cv_resume", "epfo_history", "bank_statement"}


def _save_file(upload: UploadFile, dest_dir: str) -> str:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    ext = Path(upload.filename).suffix or ".bin"
    filename = f"{uuid.uuid4()}{ext}"
    file_path = dest / filename
    with file_path.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return str(file_path)


def _build_reference_data(
    applicant: Applicant,
    doc_type: str,
    epfo_findings: dict | None = None,
) -> dict:
    """
    Build the reference_data dict injected into LangGraph state.

    CV:   use offer_reference_data (HR baseline — expected employer from offer letter)
    EPFO: use cv_profile (extracted CV employers/dates) + offer baseline
    Bank: use cv_profile + epfo_findings (which employer is unverified)
    """
    offer = applicant.offer_reference_data or {}
    cv    = applicant.cv_profile or {}

    if doc_type == "cv_resume":
        return {
            **offer,
            "_doc_type": "cv_resume",
        }
    elif doc_type == "epfo_history":
        return {
            **cv,           # full_name, employment_history[], declared_uan
            "_offer": offer,
            "_doc_type": "epfo_history",
        }
    elif doc_type == "bank_statement":
        return {
            **cv,
            "_offer": offer,
            "_epfo": epfo_findings or {},
            "_doc_type": "bank_statement",
        }
    return offer


async def _run_pipeline(
    compiled_graph,
    initial_state: dict,
    thread_id: str,
) -> tuple[dict, list]:
    """Run the graph and return (state_values, next_nodes)."""
    config = {"configurable": {"thread_id": thread_id}}
    try:
        await compiled_graph.ainvoke(initial_state, config=config)
    except Exception:
        pass  # interrupt() causes a raised exception — expected
    graph_state = await compiled_graph.aget_state(config)
    return graph_state.values, list(graph_state.next or [])


def _determine_status(state_values: dict, next_nodes: list) -> str:
    if "human_review" in next_nodes:
        return "NEEDS_REVIEW"
    final = state_values.get("final_status")
    if final == "VERIFIED":
        return "VERIFIED"
    if final == "PENDING":
        return "NEEDS_FALLBACK"
    eval_result = state_values.get("evaluation_result", "")
    if eval_result == "PASSED":
        return "VERIFIED"
    if eval_result == "NEEDS_FALLBACK":
        return "NEEDS_FALLBACK"
    return "NEEDS_REVIEW"


@router.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    applicant_id: str = Form(...),
    document_type: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a document and start the LangGraph BGV pipeline.

    document_type: cv_resume | epfo_history | bank_statement

    Ordering constraint (enforced by reference_data logic):
      1. Upload cv_resume FIRST — it becomes the baseline profile.
      2. Upload epfo_history — cross-verified against CV.
      3. Upload bank_statement — only needed when EPFO returns NEEDS_FALLBACK.
    """
    if document_type not in VALID_TYPES:
        raise HTTPException(400, f"document_type must be one of {VALID_TYPES}")

    # ── Load applicant ────────────────────────────────────────────────────────
    result = await db.execute(
        select(Applicant).where(Applicant.id == uuid.UUID(applicant_id))
    )
    applicant = result.scalar_one_or_none()
    if not applicant:
        raise HTTPException(404, f"Applicant {applicant_id} not found")

    # ── Warn if EPFO/bank uploaded before CV ─────────────────────────────────
    if document_type in ("epfo_history", "bank_statement") and not applicant.cv_profile:
        raise HTTPException(
            400,
            f"Cannot process {document_type} before CV. "
            "Upload cv_resume first so the system has a baseline to cross-verify against."
        )

    # ── Save file ─────────────────────────────────────────────────────────────
    file_path = _save_file(file, settings.upload_dir)
    file_url  = f"/uploads/{Path(file_path).name}"

    # ── Create document record ────────────────────────────────────────────────
    thread_id = str(uuid.uuid4())
    doc = Document(
        applicant_id=applicant.id,
        document_type=document_type,
        file_url=file_url,
        verification_status="PROCESSING",
        thread_id=thread_id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    # ── Build reference_data for this document type ───────────────────────────
    reference_data = _build_reference_data(applicant, document_type)

    # ── Build initial state ───────────────────────────────────────────────────
    initial_state = {
        "thread_id": thread_id,
        "applicant_id": str(applicant.id),
        "document_id": str(doc.id),
        "document_type": document_type,
        "document_url": file_path,
        "raw_text": "",
        "masked_text": "",
        "pii_map": {},
        "extracted_data": {},
        "reference_data": reference_data,
        "cv_profile": applicant.cv_profile,
        "epfo_findings": None,
        "evaluation_result": "",
        "discrepancies": [],
        "reasoning": [
            f"[INIT] {document_type} verification started for {applicant.full_name}"
        ],
        "admin_decision": None,
        "admin_notes": None,
        "final_status": None,
    }

    # ── Run graph ─────────────────────────────────────────────────────────────
    compiled_graph = request.app.state.graph
    state_values, next_nodes = await _run_pipeline(
        compiled_graph, initial_state, thread_id
    )

    new_status = _determine_status(state_values, next_nodes)
    doc.verification_status = new_status
    await db.commit()

    # ── Post-processing: store cv_profile after CV success ────────────────────
    if document_type == "cv_resume" and new_status in ("VERIFIED", "NEEDS_REVIEW"):
        # Demask cv_profile before storing (pii_map is in state)
        raw_extracted = state_values.get("extracted_data", {})
        pii_map = state_values.get("pii_map", {})
        import json as _json
        data_str = _json.dumps(raw_extracted)
        for token, real_val in pii_map.items():
            data_str = data_str.replace(token, str(real_val))
        try:
            cv_profile = _json.loads(data_str)
        except Exception:
            cv_profile = raw_extracted
        applicant.cv_profile = cv_profile
        await db.commit()

    # ── Write verification result ─────────────────────────────────────────────
    if new_status in ("VERIFIED", "REJECTED"):
        vr = VerificationResult(
            document_id=doc.id,
            extracted_data=state_values.get("extracted_data"),
            discrepancies=state_values.get("discrepancies"),
            reasoning=state_values.get("reasoning"),
        )
        db.add(vr)
        await db.commit()

    return {
        "document_id": str(doc.id),
        "thread_id": thread_id,
        "status": new_status,
        "document_type": document_type,
        "evaluation_result": state_values.get("evaluation_result"),
        "discrepancy_count": len(state_values.get("discrepancies", [])),
        "message": _status_message(document_type, new_status),
    }


def _status_message(doc_type: str, status: str) -> str:
    if status == "VERIFIED":
        return "Document verified successfully."
    if status == "NEEDS_REVIEW":
        return "Discrepancies found — document queued for admin review."
    if status == "NEEDS_FALLBACK":
        if doc_type == "epfo_history":
            return (
                "One or more CV employers could not be confirmed in EPFO. "
                "Please upload a bank statement as supporting evidence."
            )
        return "Additional evidence required."
    return "Processing complete."


@router.post("/fallback-upload/{document_id}")
async def fallback_upload(
    document_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Admin uploads additional evidence (bank statement) for a NEEDS_FALLBACK document.
    Re-triggers pipeline with bank_statement type using cv_profile as reference.
    """
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")

    if doc.verification_status not in ("NEEDS_FALLBACK", "NEEDS_REVIEW"):
        raise HTTPException(400, "Document is not in a re-uploadable state")

    result2 = await db.execute(
        select(Applicant).where(Applicant.id == doc.applicant_id)
    )
    applicant = result2.scalar_one_or_none()
    if not applicant:
        raise HTTPException(404, "Applicant not found")

    file_path = _save_file(file, settings.upload_dir)
    file_url  = f"/uploads/{Path(file_path).name}"
    doc.file_url = file_url

    new_thread_id = str(uuid.uuid4())
    doc.thread_id = new_thread_id
    doc.verification_status = "PROCESSING"
    await db.commit()

    # Bank statement cross-verifies against cv_profile
    reference_data = _build_reference_data(applicant, "bank_statement")

    initial_state = {
        "thread_id": new_thread_id,
        "applicant_id": str(doc.applicant_id),
        "document_id": str(doc.id),
        "document_type": "bank_statement",
        "document_url": file_path,
        "raw_text": "",
        "masked_text": "",
        "pii_map": {},
        "extracted_data": {},
        "reference_data": reference_data,
        "cv_profile": applicant.cv_profile,
        "epfo_findings": None,
        "evaluation_result": "",
        "discrepancies": [],
        "reasoning": [
            "[INIT] Bank statement re-upload — cross-verifying against CV profile"
        ],
        "admin_decision": None,
        "admin_notes": None,
        "final_status": None,
    }

    compiled_graph = request.app.state.graph
    state_values, next_nodes = await _run_pipeline(
        compiled_graph, initial_state, new_thread_id
    )

    new_status = _determine_status(state_values, next_nodes)
    doc.verification_status = new_status
    await db.commit()

    return {
        "document_id": document_id,
        "thread_id": new_thread_id,
        "status": new_status,
        "message": _status_message("bank_statement", new_status),
    }
