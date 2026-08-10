from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app import models
from app.ai.base import Extractor
from app.api.deps import get_extractor, get_storage
from app.auth import get_current_user
from app.config import Settings, get_settings
from app.database import get_db
from app.schemas import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentReviewCreate,
    AppointmentReviewRead,
    ChecklistItemRead,
    CurrentUser,
    ExtractionJobRead,
    ExtractionRead,
    ExtractedFieldRead,
    FileUploadResult,
    MedicalRecordCreate,
    MedicalRecordRead,
    MemoryRead,
    ProfileCreate,
    ProfileRead,
    RecordFileRead,
    RecordReviewRequest,
)
from app.services.appointments import generate_checklist
from app.services.common import require_appointment, require_profile, require_record
from app.services.extraction import create_extraction_job, retry_extraction_job, run_extraction_job
from app.services.memory import apply_record_review
from app.storage import LocalPrivateStorage

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/profiles", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> models.Profile:
    profile = models.Profile(user_id=user.id, **payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profiles", response_model=list[ProfileRead])
def list_profiles(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[models.Profile]:
    return (
        db.query(models.Profile)
        .filter(models.Profile.user_id == user.id)
        .order_by(models.Profile.created_at.desc())
        .all()
    )


@router.get("/profiles/{profile_id}", response_model=ProfileRead)
def get_profile(
    profile_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> models.Profile:
    return require_profile(db, user_id=user.id, profile_id=profile_id)


@router.post("/records", response_model=MedicalRecordRead, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: MedicalRecordCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> models.MedicalRecord:
    require_profile(db, user_id=user.id, profile_id=payload.profile_id)
    record = models.MedicalRecord(
        user_id=user.id,
        profile_id=payload.profile_id,
        title=payload.title,
        ai_processing_consent=payload.ai_processing_consent,
        status="uploaded",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/profiles/{profile_id}/records", response_model=list[MedicalRecordRead])
def list_records(
    profile_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[models.MedicalRecord]:
    require_profile(db, user_id=user.id, profile_id=profile_id)
    return (
        db.query(models.MedicalRecord)
        .filter(models.MedicalRecord.user_id == user.id, models.MedicalRecord.profile_id == profile_id)
        .order_by(models.MedicalRecord.created_at.desc())
        .all()
    )


@router.get("/records/{record_id}", response_model=MedicalRecordRead)
def get_record(
    record_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> models.MedicalRecord:
    return require_record(db, user_id=user.id, record_id=record_id)


@router.post(
    "/records/{record_id}/files",
    response_model=FileUploadResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_record_file(
    record_id: str,
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
    storage: LocalPrivateStorage = Depends(get_storage),
    extractor: Extractor = Depends(get_extractor),
) -> FileUploadResult:
    record = require_record(db, user_id=user.id, record_id=record_id)
    try:
        stored = await storage.save_upload(
            user_id=user.id,
            profile_id=record.profile_id,
            record_id=record.id,
            upload=upload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)) from exc

    record_file = models.RecordFile(
        user_id=user.id,
        profile_id=record.profile_id,
        record_id=record.id,
        filename=stored.filename,
        mime_type=stored.mime_type,
        storage_path=stored.storage_path,
        size_bytes=stored.size_bytes,
    )
    db.add(record_file)
    db.commit()
    db.refresh(record_file)

    job = None
    if record.ai_processing_consent:
        job = create_extraction_job(db, settings=settings, record=record, record_file=record_file)
        if settings.extraction_run_inline:
            job = run_extraction_job(db, job_id=job.id, storage=storage, extractor=extractor)

    return FileUploadResult(
        file=RecordFileRead.model_validate(record_file),
        extraction_job=ExtractionJobRead.model_validate(job) if job else None,
    )


@router.get("/records/{record_id}/extraction", response_model=ExtractionRead)
def get_record_extraction(
    record_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ExtractionRead:
    record = require_record(db, user_id=user.id, record_id=record_id)
    jobs = (
        db.query(models.ExtractionJob)
        .filter(models.ExtractionJob.user_id == user.id, models.ExtractionJob.record_id == record.id)
        .order_by(models.ExtractionJob.created_at.desc())
        .all()
    )
    fields = (
        db.query(models.ExtractedField)
        .filter(models.ExtractedField.user_id == user.id, models.ExtractedField.record_id == record.id)
        .order_by(models.ExtractedField.created_at.asc())
        .all()
    )
    return ExtractionRead(record=record, jobs=jobs, fields=fields)


@router.patch("/records/{record_id}/review", response_model=ExtractionRead)
def review_record_extraction(
    record_id: str,
    payload: RecordReviewRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> ExtractionRead:
    record = require_record(db, user_id=user.id, record_id=record_id)
    field_count = (
        db.query(models.ExtractedField)
        .filter(
            models.ExtractedField.user_id == user.id,
            models.ExtractedField.record_id == record.id,
            models.ExtractedField.id.in_([decision.field_id for decision in payload.decisions]),
        )
        .count()
    )
    if field_count != len(payload.decisions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more review fields do not belong to this record.",
        )

    apply_record_review(db, user_id=user.id, record=record, review=payload)
    return get_record_extraction(record_id, db, user)


@router.get("/extraction/jobs/{job_id}", response_model=ExtractionJobRead)
def get_extraction_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> models.ExtractionJob:
    job = (
        db.query(models.ExtractionJob)
        .filter(models.ExtractionJob.id == job_id, models.ExtractionJob.user_id == user.id)
        .one_or_none()
    )
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction job not found.")
    return job


@router.post("/extraction/jobs/{job_id}/run", response_model=ExtractionJobRead)
def run_job(
    job_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
    storage: LocalPrivateStorage = Depends(get_storage),
    extractor: Extractor = Depends(get_extractor),
) -> models.ExtractionJob:
    job = get_extraction_job(job_id, db, user)
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
    storage: LocalPrivateStorage = Depends(get_storage),
    extractor: Extractor = Depends(get_extractor),
) -> models.ExtractionJob:
    job = get_extraction_job(job_id, db, user)
    return retry_extraction_job(db, job=job, storage=storage, extractor=extractor)


@router.get("/profiles/{profile_id}/memory", response_model=MemoryRead)
def get_memory(
    profile_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> MemoryRead:
    profile = require_profile(db, user_id=user.id, profile_id=profile_id)
    facts = (
        db.query(models.MemoryFact)
        .filter(models.MemoryFact.user_id == user.id, models.MemoryFact.profile_id == profile.id)
        .order_by(models.MemoryFact.created_at.desc())
        .all()
    )
    return MemoryRead(profile=profile, facts=facts)


@router.post("/appointments", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> models.Appointment:
    require_profile(db, user_id=user.id, profile_id=payload.profile_id)
    appointment = models.Appointment(user_id=user.id, **payload.model_dump())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.get("/profiles/{profile_id}/appointments", response_model=list[AppointmentRead])
def list_appointments(
    profile_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[models.Appointment]:
    require_profile(db, user_id=user.id, profile_id=profile_id)
    return (
        db.query(models.Appointment)
        .filter(models.Appointment.user_id == user.id, models.Appointment.profile_id == profile_id)
        .order_by(models.Appointment.scheduled_for.asc())
        .all()
    )


@router.post("/appointments/{appointment_id}/checklist/generate", response_model=list[ChecklistItemRead])
def generate_appointment_checklist(
    appointment_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[models.AppointmentChecklistItem]:
    appointment = require_appointment(db, user_id=user.id, appointment_id=appointment_id)
    return generate_checklist(db, appointment=appointment)


@router.get("/appointments/{appointment_id}/checklist", response_model=list[ChecklistItemRead])
def get_appointment_checklist(
    appointment_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> list[models.AppointmentChecklistItem]:
    appointment = require_appointment(db, user_id=user.id, appointment_id=appointment_id)
    return (
        db.query(models.AppointmentChecklistItem)
        .filter(
            models.AppointmentChecklistItem.user_id == user.id,
            models.AppointmentChecklistItem.appointment_id == appointment.id,
        )
        .order_by(models.AppointmentChecklistItem.created_at.asc())
        .all()
    )


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
) -> models.AppointmentReview:
    appointment = require_appointment(db, user_id=user.id, appointment_id=appointment_id)
    review = models.AppointmentReview(
        user_id=user.id,
        profile_id=appointment.profile_id,
        appointment_id=appointment.id,
        stars=payload.stars,
    )
    appointment.status = "reviewed"
    db.add(review)
    db.commit()
    db.refresh(review)
    return review

