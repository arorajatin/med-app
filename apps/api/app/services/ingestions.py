from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app import models
from app.services.common import recalculate_review_state


def resolve_ingestion_assignment(
    db: Session,
    *,
    ingestion: models.Ingestion,
    profile: models.Profile,
    resolver_identity_id: str,
) -> models.MedicalRecord:
    """Resolve an owned ingestion and publish its profile-scoped rows atomically."""

    existing = (
        db.query(models.MedicalRecord)
        .filter(models.MedicalRecord.ingestion_id == ingestion.id)
        .one_or_none()
    )
    if existing is None:
        first_part = (
            db.query(models.IngestionPart)
            .filter(models.IngestionPart.ingestion_id == ingestion.id)
            .order_by(models.IngestionPart.ordinal.asc())
            .first()
        )
        display_filename = ingestion.display_filename or (
            first_part.original_filename if first_part else "medical-record"
        )
        record = models.MedicalRecord(
            account_id=ingestion.account_id,
            profile_id=profile.id,
            ingestion_id=ingestion.id,
            display_filename=display_filename,
        )
        db.add(record)
        db.flush()
    else:
        record = existing
        record.profile_id = profile.id

    ingestion.resolved_profile_id = profile.id
    ingestion.resolved_by_identity_id = resolver_identity_id
    ingestion.assignment_state = "resolved"
    ingestion.resolved_at = datetime.now(UTC)

    metadata = (
        db.query(models.DocumentMetadataCandidate)
        .filter(models.DocumentMetadataCandidate.ingestion_id == ingestion.id)
        .all()
    )
    observations = (
        db.query(models.MetricObservation)
        .filter(models.MetricObservation.ingestion_id == ingestion.id)
        .all()
    )
    memory_candidates = (
        db.query(models.MemoryCandidate)
        .filter(models.MemoryCandidate.ingestion_id == ingestion.id)
        .all()
    )
    for metadata_candidate in metadata:
        metadata_candidate.record_id = record.id
        metadata_candidate.profile_id = profile.id
    for observation in observations:
        observation.record_id = record.id
        observation.profile_id = profile.id
    for memory_candidate in memory_candidates:
        memory_candidate.record_id = record.id
        memory_candidate.profile_id = profile.id

    recalculate_review_state(db, ingestion=ingestion)
    db.commit()
    db.refresh(record)
    return record
