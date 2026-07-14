from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CurrentUser(BaseModel):
    id: str


class ProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)
    relationship: str = Field(default="self", min_length=1, max_length=80)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=40)


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    relationship: str
    date_of_birth: date | None
    sex: str | None
    created_at: datetime
    updated_at: datetime


class MedicalRecordCreate(BaseModel):
    profile_id: str
    title: str = Field(min_length=1, max_length=240)
    ai_processing_consent: bool = True


class MedicalRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    title: str
    status: str
    record_type: str | None
    record_date: date | None
    provider_name: str | None
    ai_processing_consent: bool
    created_at: datetime
    updated_at: datetime


class RecordFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    record_id: str
    filename: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


class ExtractionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    record_id: str
    file_id: str
    status: str
    provider: str
    failure_reason: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class FileUploadResult(BaseModel):
    file: RecordFileRead
    extraction_job: ExtractionJobRead | None


class ExtractedFieldRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    record_id: str
    job_id: str
    field_type: str
    label: str
    value: dict
    normalized_value: dict | None
    confidence: float
    source_reference: str | None
    confirmation_status: str
    created_at: datetime
    reviewed_at: datetime | None


class ExtractionRead(BaseModel):
    record: MedicalRecordRead
    jobs: list[ExtractionJobRead]
    fields: list[ExtractedFieldRead]


ReviewAction = Literal["confirm", "edit", "ignore", "incorrect"]


class ReviewFieldDecision(BaseModel):
    field_id: str
    action: ReviewAction
    value: dict | None = None


class RecordReviewRequest(BaseModel):
    decisions: list[ReviewFieldDecision] = Field(min_length=1)


class MemoryFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    source_record_id: str
    source_field_id: str
    category: str
    title: str
    details: dict
    body_system: str | None
    occurred_on: date | None
    created_at: datetime


class MemoryRead(BaseModel):
    profile: ProfileRead
    facts: list[MemoryFactRead]


class AppointmentCreate(BaseModel):
    profile_id: str
    scheduled_for: datetime
    clinician_name: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=240)
    reason: str | None = Field(default=None, max_length=300)


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    scheduled_for: datetime
    clinician_name: str | None
    location: str | None
    reason: str | None
    status: str
    created_at: datetime


class ChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    appointment_id: str
    question: str
    source_fact_id: str | None
    is_generic: bool
    created_at: datetime


class AppointmentReviewCreate(BaseModel):
    stars: int = Field(ge=1, le=5)


class AppointmentReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    appointment_id: str
    stars: int
    created_at: datetime
