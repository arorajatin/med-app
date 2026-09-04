from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Account(Base):
    """Application owner for every private family-health resource."""

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    onboarding_status: Mapped[str] = mapped_column(
        String(40), default="not_started", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AuthIdentity(Base):
    """Verified external identity mapped to exactly one application account."""

    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_auth_identity_provider_subject"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    # The account key stays the authentication provider and its stable subject.
    # How the person proved who they are, such as `google`, is provenance beside
    # it, so a later sign-in method never repoints the account.
    upstream_provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Profile(Base):
    """A family member managed inside one application account."""

    __tablename__ = "profiles"
    __table_args__ = (
        Index(
            "uq_profiles_one_self_per_account",
            "account_id",
            unique=True,
            sqlite_where=text("relationship = 'self'"),
            postgresql_where=text("relationship = 'self'"),
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    relationship: Mapped[str] = mapped_column(String(80), default="self", nullable=False)
    sex: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # An empty condition or medication list creates no fact, so these record that the
    # account manager answered the question rather than skipped it.
    conditions_declared_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    medications_declared_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ProfileHealthContext(Base):
    """One user-reported age or unit-aware weight observation for a profile."""

    __tablename__ = "profile_health_context"
    __table_args__ = (
        CheckConstraint(
            "reported_age IS NOT NULL OR entered_weight IS NOT NULL",
            name="ck_profile_health_context_has_value",
        ),
        CheckConstraint(
            "reported_age IS NULL OR (reported_age >= 0 AND reported_age <= 130)",
            name="ck_profile_health_context_age_range",
        ),
        CheckConstraint(
            "weight_unit IS NULL OR weight_unit IN ('kg', 'lb')",
            name="ck_profile_health_context_weight_unit",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True, nullable=False)
    reported_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    age_reported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entered_weight: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    weight_unit: Mapped[str | None] = mapped_column(String(2), nullable=True)
    normalized_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    weight_reported_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Ingestion(Base):
    """Account-owned logical document staged independently of final patient assignment."""

    __tablename__ = "ingestions"
    __table_args__ = (
        CheckConstraint(
            "source_channel IN ('direct_file', 'camera')", name="ck_ingestions_source_channel"
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    provisional_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("profiles.id"), index=True, nullable=True
    )
    resolved_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("profiles.id"), index=True, nullable=True
    )
    resolved_by_identity_id: Mapped[str | None] = mapped_column(
        ForeignKey("auth_identities.id"), nullable=True
    )
    source_channel: Mapped[str] = mapped_column(String(20), nullable=False)
    grouping_id: Mapped[str] = mapped_column(String, nullable=False, default=new_id)
    user_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_filename: Mapped[str | None] = mapped_column(String(260), nullable=True)
    user_renamed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    upload_state: Mapped[str] = mapped_column(String(40), default="receiving", nullable=False)
    assignment_state: Mapped[str] = mapped_column(String(40), default="provisional", nullable=False)
    extraction_state: Mapped[str] = mapped_column(
        String(40), default="not_requested", nullable=False
    )
    review_state: Mapped[str] = mapped_column(String(40), default="not_required", nullable=False)
    patient_match_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tombstoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class IngestionPart(Base):
    """One immutable ordered private source part within a logical document."""

    __tablename__ = "ingestion_parts"
    __table_args__ = (
        UniqueConstraint("ingestion_id", "ordinal", name="uq_ingestion_parts_ordinal"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    ingestion_id: Mapped[str] = mapped_column(
        ForeignKey("ingestions.id"), index=True, nullable=False
    )
    actor_identity_id: Mapped[str] = mapped_column(
        ForeignKey("auth_identities.id"), index=True, nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(260), nullable=False)
    detected_mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(120), nullable=False)
    object_key: Mapped[str] = mapped_column(String(700), nullable=False)
    authorization_basis: Mapped[str] = mapped_column(String(80), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MedicalRecord(Base):
    """Profile-resolved report metadata projected from a completed ingestion."""

    __tablename__ = "medical_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True, nullable=False)
    ingestion_id: Mapped[str] = mapped_column(
        ForeignKey("ingestions.id"), unique=True, index=True, nullable=False
    )
    display_filename: Mapped[str] = mapped_column(String(260), nullable=False)
    record_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    record_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    issuer_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ExtractionJob(Base):
    """Public lifecycle for extracting one immutable logical document."""

    __tablename__ = "extraction_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    ingestion_id: Mapped[str] = mapped_column(
        ForeignKey("ingestions.id"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(40), default="queued", nullable=False)
    current_phase: Mapped[str | None] = mapped_column(String(60), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExtractionAttempt(Base):
    """Atomic provider attempt and protected raw-output object reference."""

    __tablename__ = "extraction_attempts"
    __table_args__ = (
        UniqueConstraint("job_id", "attempt_number", name="uq_extraction_attempt_number"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    job_id: Mapped[str] = mapped_column(
        ForeignKey("extraction_jobs.id"), index=True, nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    internal_phase: Mapped[str | None] = mapped_column(String(60), nullable=True)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_components: Mapped[dict] = mapped_column(JSON, nullable=False)
    processing_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    routing_reason: Mapped[str | None] = mapped_column(String(120), nullable=True)
    raw_output_bucket: Mapped[str | None] = mapped_column(String(120), nullable=True)
    raw_output_object_key: Mapped[str | None] = mapped_column(String(700), nullable=True)
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PatientEvidence(Base):
    """Source-linked literal patient identity evidence used only for local matching."""

    __tablename__ = "patient_evidence"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    ingestion_id: Mapped[str] = mapped_column(
        ForeignKey("ingestions.id"), index=True, nullable=False
    )
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("extraction_attempts.id"), index=True, nullable=False
    )
    extracted_name: Mapped[str] = mapped_column(String(240), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(240), index=True, nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    patient_identifier: Mapped[str | None] = mapped_column(String(160), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentMetadataCandidate(Base):
    """Review-required extracted report metadata."""

    __tablename__ = "document_metadata_candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    ingestion_id: Mapped[str] = mapped_column(
        ForeignKey("ingestions.id"), index=True, nullable=False
    )
    record_id: Mapped[str | None] = mapped_column(
        ForeignKey("medical_records.id"), index=True, nullable=True
    )
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("profiles.id"), nullable=True)
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("extraction_attempts.id"), index=True, nullable=False
    )
    metadata_type: Mapped[str] = mapped_column(String(60), nullable=False)
    original_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    submitted_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    review_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DocumentMetadataReview(Base):
    """Immutable review history for a document-metadata candidate."""

    __tablename__ = "document_metadata_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("document_metadata_candidates.id"), index=True, nullable=False
    )
    reviewer_identity_id: Mapped[str] = mapped_column(
        ForeignKey("auth_identities.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    submitted_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class MetricObservation(Base):
    """Untrusted, auditable measurement kept outside reviewed medical memory."""

    __tablename__ = "metric_observations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    ingestion_id: Mapped[str] = mapped_column(
        ForeignKey("ingestions.id"), index=True, nullable=False
    )
    record_id: Mapped[str | None] = mapped_column(
        ForeignKey("medical_records.id"), index=True, nullable=True
    )
    profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("profiles.id"), index=True, nullable=True
    )
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("extraction_attempts.id"), index=True, nullable=False
    )
    metric_identity: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    original_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    original_unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    normalized_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    normalized_unit: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reference_range: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    flag: Mapped[str | None] = mapped_column(String(40), nullable=True)
    observed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    body_system: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    quality_state: Mapped[str] = mapped_column(
        String(40), default="unreviewed_extracted", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    superseded_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("metric_observations.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MemoryCandidate(Base):
    """Review-required prescription or literal documented-condition candidate."""

    __tablename__ = "memory_candidates"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    ingestion_id: Mapped[str] = mapped_column(
        ForeignKey("ingestions.id"), index=True, nullable=False
    )
    record_id: Mapped[str | None] = mapped_column(
        ForeignKey("medical_records.id"), index=True, nullable=True
    )
    profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("profiles.id"), index=True, nullable=True
    )
    attempt_id: Mapped[str] = mapped_column(
        ForeignKey("extraction_attempts.id"), index=True, nullable=False
    )
    subtype: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    original_value: Mapped[dict] = mapped_column(JSON, nullable=False)
    submitted_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    exact_condition_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    review_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MemoryCandidateReview(Base):
    """Immutable explicit review history for one candidate-memory item."""

    __tablename__ = "memory_candidate_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("memory_candidates.id"), index=True, nullable=False
    )
    reviewer_identity_id: Mapped[str] = mapped_column(
        ForeignKey("auth_identities.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    submitted_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceReference(Base):
    """Resolvable page, block, text, and polygon evidence for one normalized item."""

    __tablename__ = "source_references"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN patient_evidence_id IS NULL THEN 0 ELSE 1 END) + "
            "(CASE WHEN metadata_candidate_id IS NULL THEN 0 ELSE 1 END) + "
            "(CASE WHEN metric_observation_id IS NULL THEN 0 ELSE 1 END) + "
            "(CASE WHEN memory_candidate_id IS NULL THEN 0 ELSE 1 END) = 1",
            name="ck_source_references_one_item",
        ),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    part_id: Mapped[str] = mapped_column(
        ForeignKey("ingestion_parts.id"), index=True, nullable=False
    )
    patient_evidence_id: Mapped[str | None] = mapped_column(
        ForeignKey("patient_evidence.id"), index=True, nullable=True
    )
    metadata_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("document_metadata_candidates.id"), index=True, nullable=True
    )
    metric_observation_id: Mapped[str | None] = mapped_column(
        ForeignKey("metric_observations.id"), index=True, nullable=True
    )
    memory_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("memory_candidates.id"), index=True, nullable=True
    )
    logical_page: Mapped[int] = mapped_column(Integer, nullable=False)
    native_word_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    textract_block_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    text_span: Mapped[str] = mapped_column(Text, nullable=False)
    bounding_polygon: Mapped[list] = mapped_column(JSON, nullable=False)


class MemoryFact(Base):
    """Versioned trusted fact with user-attested or reviewed-candidate provenance."""

    __tablename__ = "memory_facts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True, nullable=False)
    source_record_id: Mapped[str | None] = mapped_column(
        ForeignKey("medical_records.id"), index=True, nullable=True
    )
    source_candidate_id: Mapped[str | None] = mapped_column(
        ForeignKey("memory_candidates.id"), index=True, nullable=True
    )
    source_reference_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_references.id"), nullable=True
    )
    attested_by_identity_id: Mapped[str | None] = mapped_column(
        ForeignKey("auth_identities.id"), nullable=True
    )
    provenance: Mapped[str] = mapped_column(String(40), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    superseded_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("memory_facts.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Appointment(Base):
    """Profile-scoped appointment for a reviewed-memory checklist."""

    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clinician_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(240), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(60), default="scheduled", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppointmentChecklistItem(Base):
    """Stored generic or memory-grounded appointment question."""

    __tablename__ = "appointment_checklist_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True, nullable=False)
    appointment_id: Mapped[str] = mapped_column(
        ForeignKey("appointments.id"), index=True, nullable=False
    )
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    source_fact_id: Mapped[str | None] = mapped_column(ForeignKey("memory_facts.id"), nullable=True)
    is_generic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppointmentReview(Base):
    """One-to-five-star feedback for an owned appointment."""

    __tablename__ = "appointment_reviews"
    __table_args__ = (
        CheckConstraint("stars >= 1 AND stars <= 5", name="ck_appointment_reviews_stars"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True, nullable=False)
    appointment_id: Mapped[str] = mapped_column(
        ForeignKey("appointments.id"), index=True, nullable=False
    )
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
