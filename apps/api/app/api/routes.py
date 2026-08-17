from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import models
from app.ai.base import Extractor
from app.ai.condition_safety import is_permitted_memory_category
from app.api.deps import get_extractor, get_storage
from app.auth import get_current_user
from app.config import Settings, get_settings
from app.database import get_db
from app.schemas import (
    AccountRead,
    AppointmentCreate,
    AppointmentRead,
    AppointmentReviewCreate,
    AppointmentReviewRead,
    ChecklistItemRead,
    ConsentCreate,
    ConsentRead,
    CurrentUser,
    ExtractionJobRead,
    ExtractionRead,
    IngestionUploadResult,
    MedicalRecordRead,
    MemoryRead,
    ProfileCreate,
    ProfileHealthContextCreate,
    ProfileHealthContextRead,
    ProfileRead,
    RecordReviewRequest,
)
from app.services.accounts import AccountContext, latest_consent, resolve_account_context
from app.services.appointments import generate_checklist
from app.services.common import (
    require_appointment,
    require_ingestion,
    require_profile,
    require_record,
)
from app.services.extraction import create_extraction_job, retry_extraction_job, run_extraction_job
from app.services.ingestions import resolve_ingestion_assignment
from app.services.memory import apply_record_review
from app.storage import LocalPrivateStorage

router = APIRouter()

SUPPORTED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/png"}
IMAGE_MIME_TYPES = {"image/jpeg", "image/png"}
MAX_LOGICAL_PARTS = 20
MAX_IMAGE_BYTES = 10_000_000


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/account", response_model=AccountRead)
def get_account(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> models.Account:
    return _account_context(db, user=user, settings=settings).account


@router.post("/account/consents", response_model=ConsentRead, status_code=status.HTTP_201_CREATED)
def accept_consent(
    payload: ConsentCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> models.ConsentEvidence:
    context = _account_context(db, user=user, settings=settings)
    consent = models.ConsentEvidence(
        account_id=context.account.id,
        actor_identity_id=context.identity.id,
        accepted_scope=payload.accepted_scope,
        policy_version=payload.policy_version,
        accepted_at=datetime.now(UTC),
    )
    db.add(consent)
    db.commit()
    db.refresh(consent)
    return consent


@router.post("/profiles", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> models.Profile:
    context = _account_context(db, user=user, settings=settings)
    profile = models.Profile(account_id=context.account.id, **payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profiles", response_model=list[ProfileRead])
def list_profiles(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[models.Profile]:
    account_id = _account_context(db, user=user, settings=settings).account.id
    return (
        db.query(models.Profile)
        .filter(models.Profile.account_id == account_id)
        .order_by(models.Profile.created_at.desc())
        .all()
    )


@router.get("/profiles/{profile_id}", response_model=ProfileRead)
def get_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> models.Profile:
    account_id = _account_context(db, user=user, settings=settings).account.id
    return require_profile(db, account_id=account_id, profile_id=profile_id)


@router.post(
    "/profiles/{profile_id}/health-context",
    response_model=ProfileHealthContextRead,
    status_code=status.HTTP_201_CREATED,
)
def create_profile_health_context(
    profile_id: str,
    payload: ProfileHealthContextCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> models.ProfileHealthContext:
    account_id = _account_context(db, user=user, settings=settings).account.id
    require_profile(db, account_id=account_id, profile_id=profile_id)
    normalized_weight = None
    if payload.entered_weight is not None and payload.weight_unit is not None:
        normalized_weight = (
            payload.entered_weight
            if payload.weight_unit == "kg"
            else payload.entered_weight * Decimal("0.45359237")
        )
    health_context = models.ProfileHealthContext(
        account_id=account_id,
        profile_id=profile_id,
        reported_age=payload.reported_age,
        age_reported_at=payload.age_reported_at,
        entered_weight=payload.entered_weight,
        weight_unit=payload.weight_unit,
        normalized_weight_kg=normalized_weight,
        weight_reported_at=payload.weight_reported_at,
    )
    db.add(health_context)
    db.commit()
    db.refresh(health_context)
    return health_context


@router.post(
    "/ingestions/direct-file",
    response_model=IngestionUploadResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_direct_file(
    uploads: list[UploadFile] = File(...),
    provisional_profile_id: str | None = Form(default=None),
    display_filename: str | None = Form(default=None),
    user_context: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    storage: LocalPrivateStorage = Depends(get_storage),
    extractor: Extractor = Depends(get_extractor),
) -> IngestionUploadResult:
    return await _receive_ingestion(
        uploads=uploads,
        provisional_profile_id=provisional_profile_id,
        display_filename=display_filename,
        user_context=user_context,
        source_channel="direct_file",
        db=db,
        user=user,
        settings=settings,
        storage=storage,
        extractor=extractor,
    )


@router.post(
    "/ingestions/camera",
    response_model=IngestionUploadResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_camera_capture(
    uploads: list[UploadFile] = File(...),
    provisional_profile_id: str | None = Form(default=None),
    display_filename: str | None = Form(default=None),
    user_context: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    storage: LocalPrivateStorage = Depends(get_storage),
    extractor: Extractor = Depends(get_extractor),
) -> IngestionUploadResult:
    return await _receive_ingestion(
        uploads=uploads,
        provisional_profile_id=provisional_profile_id,
        display_filename=display_filename,
        user_context=user_context,
        source_channel="camera",
        db=db,
        user=user,
        settings=settings,
        storage=storage,
        extractor=extractor,
    )


@router.post("/ingestions/{ingestion_id}/assignment/{profile_id}", response_model=MedicalRecordRead)
def assign_ingestion(
    ingestion_id: str,
    profile_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> models.MedicalRecord:
    context = _account_context(db, user=user, settings=settings)
    ingestion = require_ingestion(db, account_id=context.account.id, ingestion_id=ingestion_id)
    profile = require_profile(db, account_id=context.account.id, profile_id=profile_id)
    return resolve_ingestion_assignment(
        db,
        ingestion=ingestion,
        profile=profile,
        resolver_identity_id=context.identity.id,
    )


@router.get("/profiles/{profile_id}/records", response_model=list[MedicalRecordRead])
def list_records(
    profile_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[models.MedicalRecord]:
    account_id = _account_context(db, user=user, settings=settings).account.id
    require_profile(db, account_id=account_id, profile_id=profile_id)
    return (
        db.query(models.MedicalRecord)
        .join(models.Ingestion, models.Ingestion.id == models.MedicalRecord.ingestion_id)
        .filter(
            models.MedicalRecord.account_id == account_id,
            models.MedicalRecord.profile_id == profile_id,
            models.Ingestion.tombstoned_at.is_(None),
        )
        .order_by(models.MedicalRecord.created_at.desc())
        .all()
    )


@router.get("/records/{record_id}", response_model=MedicalRecordRead)
def get_record(
    record_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> models.MedicalRecord:
    account_id = _account_context(db, user=user, settings=settings).account.id
    return require_record(db, account_id=account_id, record_id=record_id)


@router.get("/ingestions/{ingestion_id}/extraction", response_model=ExtractionRead)
def get_ingestion_extraction(
    ingestion_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ExtractionRead:
    account_id = _account_context(db, user=user, settings=settings).account.id
    ingestion = require_ingestion(db, account_id=account_id, ingestion_id=ingestion_id)
    return _extraction_read(db, ingestion=ingestion)


@router.get("/records/{record_id}/extraction", response_model=ExtractionRead)
def get_record_extraction(
    record_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ExtractionRead:
    account_id = _account_context(db, user=user, settings=settings).account.id
    record = require_record(db, account_id=account_id, record_id=record_id)
    ingestion = require_ingestion(db, account_id=account_id, ingestion_id=record.ingestion_id)
    return _extraction_read(db, ingestion=ingestion)


@router.patch("/records/{record_id}/review", response_model=ExtractionRead)
def review_record_extraction(
    record_id: str,
    payload: RecordReviewRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> ExtractionRead:
    context = _account_context(db, user=user, settings=settings)
    record = require_record(db, account_id=context.account.id, record_id=record_id)
    apply_record_review(
        db,
        account_id=context.account.id,
        reviewer_identity_id=context.identity.id,
        record=record,
        review=payload,
    )
    ingestion = require_ingestion(
        db, account_id=context.account.id, ingestion_id=record.ingestion_id
    )
    return _extraction_read(db, ingestion=ingestion)


@router.get("/extraction/jobs/{job_id}", response_model=ExtractionJobRead)
def get_extraction_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> models.ExtractionJob:
    account_id = _account_context(db, user=user, settings=settings).account.id
    job = (
        db.query(models.ExtractionJob)
        .filter(models.ExtractionJob.id == job_id, models.ExtractionJob.account_id == account_id)
        .one_or_none()
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Extraction job not found."
        )
    return job


@router.post("/extraction/jobs/{job_id}/run", response_model=ExtractionJobRead)
def run_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    storage: LocalPrivateStorage = Depends(get_storage),
    extractor: Extractor = Depends(get_extractor),
) -> models.ExtractionJob:
    job = get_extraction_job(job_id, db, user, settings)
    if job.status not in {"queued", "failed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job cannot be run from status: {job.status}",
        )
    return run_extraction_job(db, job_id=job.id, storage=storage, extractor=extractor)


@router.post("/extraction/jobs/{job_id}/retry", response_model=ExtractionJobRead)
def retry_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    storage: LocalPrivateStorage = Depends(get_storage),
    extractor: Extractor = Depends(get_extractor),
) -> models.ExtractionJob:
    job = get_extraction_job(job_id, db, user, settings)
    return retry_extraction_job(db, job=job, storage=storage, extractor=extractor)


@router.get("/profiles/{profile_id}/memory", response_model=MemoryRead)
def get_memory(
    profile_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> MemoryRead:
    account_id = _account_context(db, user=user, settings=settings).account.id
    profile = require_profile(db, account_id=account_id, profile_id=profile_id)
    stored_facts = (
        db.query(models.MemoryFact)
        .filter(
            models.MemoryFact.account_id == account_id,
            models.MemoryFact.profile_id == profile.id,
            models.MemoryFact.is_active.is_(True),
        )
        .order_by(models.MemoryFact.created_at.desc())
        .all()
    )
    facts = [fact for fact in stored_facts if is_permitted_memory_category(fact.category)]
    return MemoryRead.model_validate({"profile": profile, "facts": facts})


@router.post("/appointments", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> models.Appointment:
    account_id = _account_context(db, user=user, settings=settings).account.id
    require_profile(db, account_id=account_id, profile_id=payload.profile_id)
    appointment = models.Appointment(account_id=account_id, **payload.model_dump())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.get("/profiles/{profile_id}/appointments", response_model=list[AppointmentRead])
def list_appointments(
    profile_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[models.Appointment]:
    account_id = _account_context(db, user=user, settings=settings).account.id
    require_profile(db, account_id=account_id, profile_id=profile_id)
    return (
        db.query(models.Appointment)
        .filter(
            models.Appointment.account_id == account_id,
            models.Appointment.profile_id == profile_id,
        )
        .order_by(models.Appointment.scheduled_for.asc())
        .all()
    )


@router.post(
    "/appointments/{appointment_id}/checklist/generate", response_model=list[ChecklistItemRead]
)
def generate_appointment_checklist(
    appointment_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[models.AppointmentChecklistItem]:
    account_id = _account_context(db, user=user, settings=settings).account.id
    appointment = require_appointment(db, account_id=account_id, appointment_id=appointment_id)
    return generate_checklist(db, appointment=appointment)


@router.get("/appointments/{appointment_id}/checklist", response_model=list[ChecklistItemRead])
def get_appointment_checklist(
    appointment_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> list[models.AppointmentChecklistItem]:
    account_id = _account_context(db, user=user, settings=settings).account.id
    appointment = require_appointment(db, account_id=account_id, appointment_id=appointment_id)
    items = (
        db.query(models.AppointmentChecklistItem)
        .filter(
            models.AppointmentChecklistItem.account_id == account_id,
            models.AppointmentChecklistItem.appointment_id == appointment.id,
        )
        .order_by(models.AppointmentChecklistItem.created_at.asc())
        .all()
    )
    source_fact_ids = {item.source_fact_id for item in items if item.source_fact_id}
    permitted_source_fact_ids = {
        fact.id
        for fact in db.query(models.MemoryFact)
        .filter(
            models.MemoryFact.id.in_(source_fact_ids),
            models.MemoryFact.is_active.is_(True),
        )
        .all()
        if is_permitted_memory_category(fact.category)
    }
    return [
        item
        for item in items
        if (item.is_generic and item.source_fact_id is None)
        or item.source_fact_id in permitted_source_fact_ids
    ]


@router.post(
    "/appointments/{appointment_id}/review",
    response_model=AppointmentReviewRead,
    status_code=status.HTTP_201_CREATED,
)
def create_appointment_review(
    appointment_id: str,
    payload: AppointmentReviewCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> models.AppointmentReview:
    account_id = _account_context(db, user=user, settings=settings).account.id
    appointment = require_appointment(db, account_id=account_id, appointment_id=appointment_id)
    review = models.AppointmentReview(
        account_id=account_id,
        profile_id=appointment.profile_id,
        appointment_id=appointment.id,
        stars=payload.stars,
    )
    appointment.status = "reviewed"
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def _account_context(db: Session, *, user: CurrentUser, settings: Settings) -> AccountContext:
    provider = "development" if settings.dev_auth_enabled else "supabase"
    return resolve_account_context(db, provider=provider, provider_subject=user.id)


async def _receive_ingestion(
    *,
    uploads: list[UploadFile],
    provisional_profile_id: str | None,
    display_filename: str | None,
    user_context: str | None,
    source_channel: str,
    db: Session,
    user: CurrentUser,
    settings: Settings,
    storage: LocalPrivateStorage,
    extractor: Extractor,
) -> IngestionUploadResult:
    if not uploads or len(uploads) > MAX_LOGICAL_PARTS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="A logical document must contain between 1 and 20 source parts.",
        )
    allowed_mime_types = IMAGE_MIME_TYPES if source_channel == "camera" else SUPPORTED_MIME_TYPES
    if any((upload.content_type or "") not in allowed_mime_types for upload in uploads):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only unencrypted PDF, JPEG, and PNG documents are supported.",
        )

    context = _account_context(db, user=user, settings=settings)
    profile = None
    if provisional_profile_id is not None:
        profile = require_profile(
            db, account_id=context.account.id, profile_id=provisional_profile_id
        )
    consent = latest_consent(db, account_id=context.account.id)
    ingestion = models.Ingestion(
        account_id=context.account.id,
        provisional_profile_id=provisional_profile_id,
        consent_evidence_id=consent.id if consent else None,
        source_channel=source_channel,
        display_filename=display_filename,
        user_context=user_context,
    )
    db.add(ingestion)
    db.flush()

    stored_keys: list[str] = []
    parts: list[models.IngestionPart] = []
    total_size = 0
    try:
        for ordinal, upload in enumerate(uploads):
            part_id = models.new_id()
            stored = await storage.save_upload(
                account_id=context.account.id,
                ingestion_id=ingestion.id,
                part_id=part_id,
                upload=upload,
            )
            stored_keys.append(stored.object_key)
            total_size += stored.size_bytes
            if total_size > settings.max_upload_bytes or (
                stored.mime_type in IMAGE_MIME_TYPES and stored.size_bytes > MAX_IMAGE_BYTES
            ):
                raise ValueError("Logical document exceeds the configured size limits.")
            part = models.IngestionPart(
                id=part_id,
                account_id=context.account.id,
                ingestion_id=ingestion.id,
                actor_identity_id=context.identity.id,
                ordinal=ordinal,
                original_filename=stored.filename,
                detected_mime_type=stored.mime_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                storage_bucket=stored.storage_bucket,
                object_key=stored.object_key,
                authorization_basis="authenticated_web_upload",
                received_at=datetime.now(UTC),
            )
            db.add(part)
            parts.append(part)
        ingestion.upload_state = "complete"
        ingestion.completed_at = datetime.now(UTC)
        ingestion.display_filename = ingestion.display_filename or parts[0].original_filename
        db.commit()
    except ValueError as exc:
        db.rollback()
        for object_key in stored_keys:
            storage.delete_object(object_key)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc

    record = None
    job = None
    if consent is None:
        if profile is not None:
            record = resolve_ingestion_assignment(
                db,
                ingestion=ingestion,
                profile=profile,
                resolver_identity_id=context.identity.id,
            )
        else:
            ingestion.assignment_state = "needs_assignment"
            db.commit()
    else:
        job = create_extraction_job(db, settings=settings, ingestion=ingestion)
        if settings.extraction_run_inline:
            job = run_extraction_job(db, job_id=job.id, storage=storage, extractor=extractor)

    for part in parts:
        db.refresh(part)
    db.refresh(ingestion)
    return IngestionUploadResult.model_validate(
        {
            "ingestion": ingestion,
            "parts": parts,
            "record": record,
            "extraction_job": job,
        }
    )


def _extraction_read(db: Session, *, ingestion: models.Ingestion) -> ExtractionRead:
    record = (
        db.query(models.MedicalRecord)
        .filter(models.MedicalRecord.ingestion_id == ingestion.id)
        .one_or_none()
    )
    jobs = (
        db.query(models.ExtractionJob)
        .filter(models.ExtractionJob.ingestion_id == ingestion.id)
        .order_by(models.ExtractionJob.created_at.desc())
        .all()
    )
    job_ids = [job.id for job in jobs]
    attempts = (
        db.query(models.ExtractionAttempt)
        .filter(models.ExtractionAttempt.job_id.in_(job_ids))
        .order_by(models.ExtractionAttempt.attempt_number.asc())
        .all()
        if job_ids
        else []
    )
    patient_evidence = (
        db.query(models.PatientEvidence)
        .filter(models.PatientEvidence.ingestion_id == ingestion.id)
        .all()
    )
    metadata_candidates = (
        db.query(models.DocumentMetadataCandidate)
        .filter(models.DocumentMetadataCandidate.ingestion_id == ingestion.id)
        .all()
    )
    observations = (
        db.query(models.MetricObservation)
        .filter(
            models.MetricObservation.ingestion_id == ingestion.id,
            models.MetricObservation.is_active.is_(True),
        )
        .all()
    )
    memory_candidates = (
        db.query(models.MemoryCandidate)
        .filter(models.MemoryCandidate.ingestion_id == ingestion.id)
        .all()
    )
    source_references = (
        db.query(models.SourceReference)
        .join(models.IngestionPart, models.IngestionPart.id == models.SourceReference.part_id)
        .filter(models.IngestionPart.ingestion_id == ingestion.id)
        .all()
    )
    return ExtractionRead.model_validate(
        {
            "ingestion": ingestion,
            "record": record,
            "jobs": jobs,
            "attempts": attempts,
            "patient_evidence": patient_evidence,
            "metadata_candidates": metadata_candidates,
            "observations": observations,
            "memory_candidates": memory_candidates,
            "source_references": source_references,
        }
    )
