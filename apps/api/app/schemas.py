from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CurrentUser(BaseModel):
    """Verified authentication identity injected into protected routes."""

    id: str


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    onboarding_status: str
    created_at: datetime
    updated_at: datetime


class ConsentCreate(BaseModel):
    policy_version: str = Field(min_length=1, max_length=80)
    accepted_scope: dict


class ConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    policy_version: str
    accepted_scope: dict
    accepted_at: datetime


class ProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=160)
    relationship: str = Field(default="self", min_length=1, max_length=80)
    sex: str | None = Field(default=None, max_length=40)


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    display_name: str
    relationship: str
    sex: str | None
    created_at: datetime
    updated_at: datetime


class ProfileHealthContextCreate(BaseModel):
    reported_age: int | None = Field(default=None, ge=0, le=130)
    age_reported_at: datetime | None = None
    entered_weight: Decimal | None = Field(default=None, gt=0)
    weight_unit: Literal["kg", "lb"] | None = None
    weight_reported_at: datetime | None = None

    @model_validator(mode="after")
    def validate_reported_values(self):
        if self.reported_age is None and self.entered_weight is None:
            raise ValueError("At least one reported age or weight value is required.")
        if (self.reported_age is None) != (self.age_reported_at is None):
            raise ValueError("Reported age and its reported time must be supplied together.")
        weight_values = (self.entered_weight, self.weight_unit, self.weight_reported_at)
        if any(value is not None for value in weight_values) and not all(
            value is not None for value in weight_values
        ):
            raise ValueError("Weight value, unit, and reported time must be supplied together.")
        if self.entered_weight is not None and self.weight_unit is not None:
            normalized = (
                self.entered_weight
                if self.weight_unit == "kg"
                else self.entered_weight * Decimal("0.45359237")
            )
            if normalized < Decimal("0.5") or normalized > Decimal("500"):
                raise ValueError("Normalized weight must be between 0.5 and 500 kilograms.")
        return self


class ProfileHealthContextRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    reported_age: int | None
    age_reported_at: datetime | None
    entered_weight: Decimal | None
    weight_unit: str | None
    normalized_weight_kg: Decimal | None
    weight_reported_at: datetime | None
    created_at: datetime


class IngestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provisional_profile_id: str | None
    resolved_profile_id: str | None
    source_channel: str
    user_context: str | None
    display_filename: str | None
    upload_state: str
    assignment_state: str
    extraction_state: str
    review_state: str
    completed_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class IngestionPartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ingestion_id: str
    ordinal: int
    original_filename: str
    detected_mime_type: str
    size_bytes: int
    received_at: datetime


class MedicalRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    ingestion_id: str
    display_filename: str
    record_type: str | None
    record_date: date | None
    issuer_name: str | None
    created_at: datetime
    updated_at: datetime


class ExtractionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ingestion_id: str
    status: str
    current_phase: str | None
    failure_code: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class ExtractionAttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    attempt_number: int
    status: str
    internal_phase: str | None
    provider: str
    provider_components: dict
    processing_method: str | None
    routing_reason: str | None
    failure_code: str | None
    started_at: datetime
    finished_at: datetime | None


class PatientEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ingestion_id: str
    attempt_id: str
    extracted_name: str
    date_of_birth: date | None
    patient_identifier: str | None
    confidence: float


class DocumentMetadataCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    record_id: str | None
    attempt_id: str
    metadata_type: str
    original_value: dict
    submitted_value: dict | None
    confidence: float
    review_status: str


class MetricObservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    record_id: str | None
    profile_id: str | None
    attempt_id: str
    metric_identity: str
    label: str
    original_value: dict
    original_unit: str | None
    normalized_value: dict | None
    normalized_unit: str | None
    reference_range: dict | None
    flag: str | None
    observed_on: date | None
    body_system: str | None
    confidence: float
    quality_state: str
    is_active: bool


class MemoryCandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    record_id: str | None
    attempt_id: str
    subtype: str
    label: str
    original_value: dict
    submitted_value: dict | None
    exact_condition_text: str | None
    confidence: float
    review_status: str


class SourceReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    part_id: str
    patient_evidence_id: str | None
    metadata_candidate_id: str | None
    metric_observation_id: str | None
    memory_candidate_id: str | None
    logical_page: int
    native_word_ids: list | None
    textract_block_ids: list | None
    text_span: str
    bounding_polygon: list


class IngestionUploadResult(BaseModel):
    ingestion: IngestionRead
    parts: list[IngestionPartRead]
    record: MedicalRecordRead | None
    extraction_job: ExtractionJobRead | None


class ExtractionRead(BaseModel):
    ingestion: IngestionRead
    record: MedicalRecordRead | None
    jobs: list[ExtractionJobRead]
    attempts: list[ExtractionAttemptRead]
    patient_evidence: list[PatientEvidenceRead]
    metadata_candidates: list[DocumentMetadataCandidateRead]
    observations: list[MetricObservationRead]
    memory_candidates: list[MemoryCandidateRead]
    source_references: list[SourceReferenceRead]


ReviewAction = Literal["confirm", "edit", "ignore"]
CandidateType = Literal["metadata", "memory"]


class ReviewCandidateDecision(BaseModel):
    candidate_type: CandidateType
    candidate_id: str
    action: ReviewAction
    value: dict | None = None

    @model_validator(mode="after")
    def validate_edit_value(self):
        if self.action == "edit" and self.value is None:
            raise ValueError("An edit decision requires a replacement value.")
        if self.action != "edit" and self.value is not None:
            raise ValueError("Only an edit decision may include a replacement value.")
        return self


class RecordReviewRequest(BaseModel):
    decisions: list[ReviewCandidateDecision] = Field(min_length=1)


class MemoryFactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    profile_id: str
    source_record_id: str | None
    source_candidate_id: str | None
    source_reference_id: str | None
    provenance: str
    category: str
    title: str
    details: dict
    is_active: bool
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
