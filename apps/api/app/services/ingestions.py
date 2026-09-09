from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app import models
from app.services.common import recalculate_review_state
from app.services.patient_matching import MATCH_VERSION, match_patient


def resolve_ingestion_assignment(
    db: Session,
    *,
    ingestion: models.Ingestion,
    profile: models.Profile,
    resolver_identity_id: str,
) -> models.MedicalRecord:
    """Resolve a pending document; retries of the same decision are idempotent."""

    ingestion = (
        db.query(models.Ingestion)
        .filter(
            models.Ingestion.id == ingestion.id, models.Ingestion.account_id == ingestion.account_id
        )
        .populate_existing()
        .with_for_update()
        .one()
    )
    if (
        profile.account_id != ingestion.account_id
        or not db.query(models.AuthIdentity)
        .filter(
            models.AuthIdentity.id == resolver_identity_id,
            models.AuthIdentity.account_id == ingestion.account_id,
        )
        .first()
    ):
        raise HTTPException(404, "Profile or resolver not found.")
    if ingestion.tombstoned_at is not None or ingestion.upload_state != "complete":
        raise HTTPException(409, "Only a completed, available report can be assigned.")
    if ingestion.assignment_state == "resolved":
        if ingestion.resolved_profile_id != profile.id:
            raise HTTPException(409, "This report is already assigned.")
        return (
            db.query(models.MedicalRecord)
            .filter(models.MedicalRecord.ingestion_id == ingestion.id)
            .one()
        )
    if ingestion.assignment_state != "needs_assignment" or ingestion.extraction_state != "ready":
        raise HTTPException(409, "Wait for extraction before resolving patient assignment.")
    attempt = latest_successful_attempt(db, ingestion_id=ingestion.id)
    if attempt is None:
        raise HTTPException(409, "This report has no successful extraction to assign.")
    record = _publish_assignment(
        db, ingestion=ingestion, profile=profile, resolver_identity_id=resolver_identity_id
    )
    _record_assignment(
        db, ingestion=ingestion, attempt_id=attempt.id, method="manual", candidates=[profile.id]
    )
    db.commit()
    db.refresh(record)
    return record


def latest_successful_attempt(db: Session, *, ingestion_id: str) -> models.ExtractionAttempt | None:
    return (
        db.query(models.ExtractionAttempt)
        .join(models.ExtractionJob)
        .filter(
            models.ExtractionJob.ingestion_id == ingestion_id,
            models.ExtractionAttempt.status == "ready",
        )
        .order_by(models.ExtractionAttempt.started_at.desc(), models.ExtractionAttempt.id.desc())
        .first()
    )


def automatic_assignment(db: Session, *, ingestion: models.Ingestion, attempt_id: str) -> None:
    evidence = (
        db.query(models.PatientEvidence)
        .filter(
            models.PatientEvidence.ingestion_id == ingestion.id,
            models.PatientEvidence.attempt_id == attempt_id,
        )
        .all()
    )
    profile, candidates = match_patient(
        db, account_id=ingestion.account_id, names=[item.extracted_name for item in evidence]
    )
    # A person's decision is not a provisional hint. Reprocessing the same immutable
    # source cannot undo it. An automatic replacement must agree with prior assignment.
    if ingestion.resolved_profile_id is not None:
        if ingestion.resolved_by_identity_id is not None:
            return
        if profile is None or profile.id != ingestion.resolved_profile_id:
            from app.ai.source_layout import ExtractionValidationError

            raise ExtractionValidationError("assignment_conflict")
    ingestion.patient_match_version = MATCH_VERSION
    if profile is None:
        ingestion.assignment_state = "needs_assignment"
    else:
        _publish_assignment(db, ingestion=ingestion, profile=profile, resolver_identity_id=None)
    _record_assignment(
        db, ingestion=ingestion, attempt_id=attempt_id, method="automatic", candidates=candidates
    )


def _record_assignment(
    db: Session, *, ingestion: models.Ingestion, attempt_id: str, method: str, candidates: list[str]
) -> None:
    evidence_ids = [
        item.id
        for item in db.query(models.PatientEvidence)
        .filter(
            models.PatientEvidence.ingestion_id == ingestion.id,
            models.PatientEvidence.attempt_id == attempt_id,
        )
        .order_by(models.PatientEvidence.id)
        .all()
    ]
    db.add(
        models.IngestionAssignment(
            account_id=ingestion.account_id,
            ingestion_id=ingestion.id,
            attempt_id=attempt_id,
            profile_id=ingestion.resolved_profile_id,
            resolver_identity_id=ingestion.resolved_by_identity_id,
            method=method,
            match_version=MATCH_VERSION,
            evidence_ids=evidence_ids,
            candidate_profile_ids=candidates,
        )
    )


def _publish_assignment(
    db: Session,
    *,
    ingestion: models.Ingestion,
    profile: models.Profile,
    resolver_identity_id: str | None,
) -> models.MedicalRecord:

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
    db.flush()
    return record
