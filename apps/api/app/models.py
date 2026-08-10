from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.database import Base


def new_id() -> str:
    return str(uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    relationship: Mapped[str] = mapped_column(String(80), default="self", nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    records: Mapped[list["MedicalRecord"]] = orm_relationship(back_populates="profile")


class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(ForeignKey("profiles.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(60), default="uploaded", nullable=False)
    record_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    record_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    ai_processing_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    profile: Mapped[Profile] = orm_relationship(back_populates="records")
    files: Mapped[list["RecordFile"]] = orm_relationship(back_populates="record")
    extraction_jobs: Mapped[list["ExtractionJob"]] = orm_relationship(back_populates="record")
    extracted_fields: Mapped[list["ExtractedField"]] = orm_relationship(back_populates="record")


class RecordFile(Base):
    __tablename__ = "record_files"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    record_id: Mapped[str] = mapped_column(ForeignKey("medical_records.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(260), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(600), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    record: Mapped[MedicalRecord] = orm_relationship(back_populates="files")
    extraction_jobs: Mapped[list["ExtractionJob"]] = orm_relationship(back_populates="file")


class ExtractionJob(Base):
    __tablename__ = "extraction_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    record_id: Mapped[str] = mapped_column(ForeignKey("medical_records.id"), index=True, nullable=False)
    file_id: Mapped[str] = mapped_column(ForeignKey("record_files.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(60), default="queued", nullable=False)
    provider: Mapped[str] = mapped_column(String(80), default="mock", nullable=False)
    raw_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    record: Mapped[MedicalRecord] = orm_relationship(back_populates="extraction_jobs")
    file: Mapped[RecordFile] = orm_relationship(back_populates="extraction_jobs")
    extracted_fields: Mapped[list["ExtractedField"]] = orm_relationship(back_populates="job")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    record_id: Mapped[str] = mapped_column(ForeignKey("medical_records.id"), index=True, nullable=False)
    job_id: Mapped[str] = mapped_column(ForeignKey("extraction_jobs.id"), index=True, nullable=False)
    field_type: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    normalized_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(240), nullable=True)
    confirmation_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    record: Mapped[MedicalRecord] = orm_relationship(back_populates="extracted_fields")
    job: Mapped[ExtractionJob] = orm_relationship(back_populates="extracted_fields")


class MemoryFact(Base):
    __tablename__ = "memory_facts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    source_record_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    source_field_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, nullable=False)
    body_system: Mapped[str | None] = mapped_column(String(120), nullable=True)
    occurred_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clinician_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    location: Mapped[str | None] = mapped_column(String(240), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(60), default="scheduled", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppointmentChecklistItem(Base):
    __tablename__ = "appointment_checklist_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    appointment_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    question: Mapped[str] = mapped_column(String(500), nullable=False)
    source_fact_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_generic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AppointmentReview(Base):
    __tablename__ = "appointment_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    appointment_id: Mapped[str] = mapped_column(String, index=True, nullable=False)
    stars: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
