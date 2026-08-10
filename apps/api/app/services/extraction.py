from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app import models
from app.ai.base import Extractor
from app.config import Settings
from app.storage import LocalPrivateStorage


def create_extraction_job(
    db: Session,
    *,
    settings: Settings,
    record: models.MedicalRecord,
    record_file: models.RecordFile,
) -> models.ExtractionJob:
    job = models.ExtractionJob(
        user_id=record.user_id,
        profile_id=record.profile_id,
        record_id=record.id,
        file_id=record_file.id,
        status="queued",
        provider=settings.extraction_provider,
    )
    record.status = "queued_for_extraction"
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_extraction_job(
    db: Session,
    *,
    job_id: str,
    storage: LocalPrivateStorage,
    extractor: Extractor,
) -> models.ExtractionJob:
    job = db.query(models.ExtractionJob).filter(models.ExtractionJob.id == job_id).one_or_none()
    if job is None:
        raise ValueError(f"Extraction job not found: {job_id}")

    record = job.record
    record_file = job.file
    job.status = "extracting"
    job.started_at = datetime.now(UTC)
    record.status = "extracting"
    db.commit()

    try:
        file_bytes = storage.read_bytes(record_file.storage_path)
        extraction = extractor.extract_document(
            file_bytes=file_bytes,
            filename=record_file.filename,
            mime_type=record_file.mime_type,
            profile_context={"profile_id": record.profile_id},
        )

        job.raw_output = extraction.raw_output
        job.provider = extractor.provider_name
        for datum in extraction.fields:
            db.add(
                models.ExtractedField(
                    user_id=job.user_id,
                    profile_id=job.profile_id,
                    record_id=job.record_id,
                    job_id=job.id,
                    field_type=datum.field_type,
                    label=datum.label,
                    value=datum.value,
                    normalized_value=datum.normalized_value,
                    confidence=datum.confidence,
                    source_reference=datum.source_reference,
                    confirmation_status="pending",
                )
            )

        job.status = "ready"
        job.failure_reason = None
        job.finished_at = datetime.now(UTC)
        record.status = "extraction_ready"
    except Exception as exc:  # noqa: BLE001
        job.status = "failed"
        job.failure_reason = str(exc)
        job.finished_at = datetime.now(UTC)
        record.status = "extraction_failed"

    db.commit()
    db.refresh(job)
    return job


def retry_extraction_job(
    db: Session,
    *,
    job: models.ExtractionJob,
    storage: LocalPrivateStorage,
    extractor: Extractor,
) -> models.ExtractionJob:
    (
        db.query(models.ExtractedField)
        .filter(models.ExtractedField.job_id == job.id, models.ExtractedField.confirmation_status == "pending")
        .delete()
    )
    job.status = "queued"
    job.failure_reason = None
    job.started_at = None
    job.finished_at = None
    db.commit()
    return run_extraction_job(db, job_id=job.id, storage=storage, extractor=extractor)


def parse_iso_date(value: dict | None) -> date | None:
    if not value:
        return None
    raw = value.get("date")
    if not raw:
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None

