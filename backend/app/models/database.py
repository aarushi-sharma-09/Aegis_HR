"""
Database models and async engine.
Tables:
  - applicants        : identity + offer reference data
  - documents         : uploaded file metadata + LangGraph thread_id
  - verification_results : final outcome from demasking node
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey,
    Enum as SAEnum, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from app.config import settings

Base = declarative_base()

engine = create_async_engine(settings.get_postgres_uri, echo=False, future=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ─── Models ──────────────────────────────────────────────────────────────────

class Applicant(Base):
    __tablename__ = "applicants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    # Offer letter / HR-system baseline (manually entered when creating applicant)
    offer_reference_data = Column(JSON, nullable=True)
    # Auto-populated after CV document is successfully processed.
    # Becomes reference_data for subsequent EPFO and bank statement evaluations.
    cv_profile = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="applicant")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    applicant_id = Column(UUID(as_uuid=True), ForeignKey("applicants.id"), nullable=False)
    document_type = Column(
        SAEnum("bank_statement", "epfo_history", "cv_resume", name="document_type_enum"),
        nullable=False,
    )
    file_url = Column(Text, nullable=False)
    verification_status = Column(
        SAEnum(
            "PENDING", "PROCESSING", "PASSED", "NEEDS_REVIEW",
            "NEEDS_FALLBACK", "VERIFIED", "REJECTED",
            name="verification_status_enum",
        ),
        default="PENDING",
    )
    thread_id = Column(String(255), nullable=True)  # LangGraph thread ID
    created_at = Column(DateTime, default=datetime.utcnow)

    applicant = relationship("Applicant", back_populates="documents")
    result = relationship("VerificationResult", back_populates="document", uselist=False)


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    extracted_data = Column(JSON, nullable=True)      # final de-masked values
    discrepancies = Column(JSON, nullable=True)
    reasoning = Column(JSON, nullable=True)           # list[str]
    admin_decision = Column(String(20), nullable=True)
    admin_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="result")


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create all tables (called on startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
