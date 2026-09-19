"""
Admin API — review queue, state inspection, decision resolution.

GET  /api/admin/review-queue         : All documents in NEEDS_REVIEW / NEEDS_FALLBACK
GET  /api/admin/review/{thread_id}   : Full LangGraph state for one paused thread
POST /api/admin/review/{thread_id}/resolve : Submit APPROVED/REJECTED decision
GET  /api/admin/dashboard/stats      : Counts by status
GET  /api/admin/applicants           : List applicants (for new submission form)
POST /api/admin/applicants           : Create applicant with offer reference data
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.database import get_db, Document, Applicant, VerificationResult

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ─── Pydantic schemas ─────────────────────────────────────────────────────────

class ResolveRequest(BaseModel):
    decision: str          # "APPROVED" | "REJECTED"
    notes: Optional[str] = None


class ApplicantCreate(BaseModel):
    full_name: str
    email: str
    offer_reference_data: Optional[dict] = None


# ─── Review Queue ─────────────────────────────────────────────────────────────

@router.get("/review-queue")
async def get_review_queue(db: AsyncSession = Depends(get_db)):
    """Returns all documents awaiting human review or fallback."""
    result = await db.execute(
        select(Document, Applicant)
        .join(Applicant, Document.applicant_id == Applicant.id)
        .where(Document.verification_status.in_(["NEEDS_REVIEW", "NEEDS_FALLBACK"]))
        .order_by(Document.created_at.asc())  # oldest first
    )
    rows = result.all()

    queue = []
    for doc, applicant in rows:
        queue.append({
            "document_id": str(doc.id),
            "thread_id": doc.thread_id,
            "applicant_id": str(applicant.id),
            "applicant_name": applicant.full_name,
            "applicant_email": applicant.email,
            "document_type": doc.document_type,
            "verification_status": doc.verification_status,
            "file_url": doc.file_url,
            "created_at": doc.created_at.isoformat(),
            "age_hours": round(
                (datetime.utcnow() - doc.created_at).total_seconds() / 3600, 1
            ),
        })

    return {"count": len(queue), "queue": queue}


@router.get("/review/{thread_id}")
async def get_review_detail(
    thread_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Returns full LangGraph state for a paused thread — used to render the split-screen UI."""
    # Get document from DB
    result = await db.execute(
        select(Document, Applicant)
        .join(Applicant, Document.applicant_id == Applicant.id)
        .where(Document.thread_id == thread_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, f"Thread {thread_id} not found")
    doc, applicant = row

    # Get LangGraph state
    compiled_graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}
    try:
        graph_state = await compiled_graph.aget_state(config)
        state_values = graph_state.values
    except Exception as e:
        raise HTTPException(500, f"Could not retrieve graph state: {str(e)}")

    return {
        "thread_id": thread_id,
        "document": {
            "id": str(doc.id),
            "type": doc.document_type,
            "file_url": doc.file_url,
            "status": doc.verification_status,
        },
        "applicant": {
            "id": str(applicant.id),
            "name": applicant.full_name,
            "email": applicant.email,
            "reference_data": applicant.offer_reference_data,
        },
        "reasoning": state_values.get("reasoning", []),
        "discrepancies": state_values.get("discrepancies", []),
        "extracted_data": state_values.get("extracted_data", {}),
        "evaluation_result": state_values.get("evaluation_result"),
        "masked_text_preview": (state_values.get("masked_text", "")[:500] + "…")
            if state_values.get("masked_text") else "",
    }


@router.post("/review/{thread_id}/resolve")
async def resolve_review(
    thread_id: str,
    body: ResolveRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Inject admin_decision into state and resume the LangGraph graph.
    The graph routes to demask (APPROVED) or END (REJECTED).
    """
    if body.decision not in ("APPROVED", "REJECTED"):
        raise HTTPException(400, "decision must be 'APPROVED' or 'REJECTED'")

    compiled_graph = request.app.state.graph
    config = {"configurable": {"thread_id": thread_id}}

    # Inject decision into checkpointed state
    await compiled_graph.aupdate_state(
        config,
        {"admin_decision": body.decision, "admin_notes": body.notes},
        as_node="human_review",
    )

    # Resume the graph
    try:
        await compiled_graph.ainvoke(None, config=config)
    except Exception:
        pass

    # Determine final status
    final_state = await compiled_graph.aget_state(config)
    final_status = final_state.values.get("final_status")
    new_db_status = "VERIFIED" if body.decision == "APPROVED" else "REJECTED"

    # Update document status
    result = await db.execute(
        select(Document).where(Document.thread_id == thread_id)
    )
    doc = result.scalar_one_or_none()
    if doc:
        doc.verification_status = new_db_status
        await db.commit()

        # Write / update verification result
        result2 = await db.execute(
            select(VerificationResult).where(VerificationResult.document_id == doc.id)
        )
        vr = result2.scalar_one_or_none()
        if vr:
            vr.admin_decision = body.decision
            vr.admin_notes = body.notes
            vr.resolved_at = datetime.utcnow()
            vr.extracted_data = final_state.values.get("extracted_data")
            vr.reasoning = final_state.values.get("reasoning")
        else:
            vr = VerificationResult(
                document_id=doc.id,
                extracted_data=final_state.values.get("extracted_data"),
                discrepancies=final_state.values.get("discrepancies"),
                reasoning=final_state.values.get("reasoning"),
                admin_decision=body.decision,
                admin_notes=body.notes,
                resolved_at=datetime.utcnow(),
            )
            db.add(vr)
        await db.commit()

    return {
        "thread_id": thread_id,
        "decision": body.decision,
        "final_status": new_db_status,
        "message": f"Document {new_db_status.lower()} successfully",
    }


@router.get("/dashboard/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Aggregated counts for the dashboard overview cards."""
    statuses = ["PENDING", "PROCESSING", "VERIFIED", "REJECTED", "NEEDS_REVIEW", "NEEDS_FALLBACK"]
    counts = {}
    for status in statuses:
        result = await db.execute(
            select(func.count(Document.id)).where(Document.verification_status == status)
        )
        counts[status.lower()] = result.scalar() or 0

    total_result = await db.execute(select(func.count(Document.id)))
    counts["total"] = total_result.scalar() or 0

    applicant_result = await db.execute(select(func.count(Applicant.id)))
    counts["total_applicants"] = applicant_result.scalar() or 0

    return counts


@router.get("/applicants")
async def list_applicants(db: AsyncSession = Depends(get_db)):
    """List all applicants with their document statuses."""
    result = await db.execute(
        select(Applicant).order_by(Applicant.created_at.desc())
    )
    applicants = result.scalars().all()

    data = []
    for a in applicants:
        docs_result = await db.execute(
            select(Document).where(Document.applicant_id == a.id)
        )
        docs = docs_result.scalars().all()
        data.append({
            "id": str(a.id),
            "full_name": a.full_name,
            "email": a.email,
            "offer_reference_data": a.offer_reference_data,
            "created_at": a.created_at.isoformat(),
            "documents": [
                {
                    "id": str(d.id),
                    "type": d.document_type,
                    "status": d.verification_status,
                    "thread_id": d.thread_id,
                    "created_at": d.created_at.isoformat(),
                }
                for d in docs
            ],
        })

    return {"applicants": data}


from sqlalchemy.exc import IntegrityError

@router.post("/applicants")
async def create_applicant(body: ApplicantCreate, db: AsyncSession = Depends(get_db)):
    """Create a new applicant with offer letter reference data."""
    applicant = Applicant(
        full_name=body.full_name,
        email=body.email,
        offer_reference_data=body.offer_reference_data or {},
    )
    db.add(applicant)
    try:
        await db.commit()
        await db.refresh(applicant)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="An applicant with this email already exists.")

    return {
        "id": str(applicant.id),
        "full_name": applicant.full_name,
        "email": applicant.email,
        "offer_reference_data": applicant.offer_reference_data,
    }
