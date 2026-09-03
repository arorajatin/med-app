import json
from datetime import UTC, date, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import models
from app.ai.base import Extractor, SourceReferenceData
from app.ai.condition_safety import enforce_condition_safety
from app.ai.mock_provider import MockExtractor
from app.config import Settings
from app.services.common import recalculate_review_state
from app.storage import LocalPrivateStorage


def create_extraction_job(
    db: Session,
    *,
    settings: Settings,
    ingestion: models.Ingestion,
) -> models.ExtractionJob:
    job = models.ExtractionJob(
        account_id=ingestion.account_id,
        ingestion_id=ingestion.id,
        status="queued",
    )
    ingestion.extraction_state = "queued"
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def run_extraction_job(
    db: Session,
    *,
    job_id: str,
    settings: Settings,
    storage: LocalPrivateStorage,
    extractor: Extractor,
) -> models.ExtractionJob:
    job = db.query(models.ExtractionJob).filter(models.ExtractionJob.id == job_id).one_or_none()
    if job is None:
        raise ValueError(f"Extraction job not found: {job_id}")

    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == job.ingestion_id).one()
    parts = (
        db.query(models.IngestionPart)
        .filter(models.IngestionPart.ingestion_id == ingestion.id)
        .order_by(models.IngestionPart.ordinal.asc())
        .all()
    )
    if not parts:
        raise ValueError(f"Ingestion has no source parts: {ingestion.id}")

    attempt_number = (
        db.query(func.max(models.ExtractionAttempt.attempt_number))
        .filter(models.ExtractionAttempt.job_id == job.id)
        .scalar()
        or 0
    ) + 1
    now = datetime.now(UTC)
    attempt = models.ExtractionAttempt(
        account_id=job.account_id,
        job_id=job.id,
        attempt_number=attempt_number,
        status="extracting",
        internal_phase="native_parsing",
        provider=extractor.provider_name,
        provider_components={"extractor": extractor.provider_name},
        started_at=now,
    )
    job.status = "extracting"
    job.current_phase = "native_parsing"
    job.started_at = job.started_at or now
    job.failure_code = None
    ingestion.extraction_state = "extracting"
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    try:
        file_bytes = b"\n".join(storage.read_bytes(part.object_key) for part in parts)
        extraction = extractor.extract_document(
            file_bytes=file_bytes,
            filename=parts[0].original_filename,
            mime_type=parts[0].detected_mime_type,
        )
        extraction = enforce_condition_safety(
            extraction,
            allow_baseline_items=type(extractor) is MockExtractor,
        )

        raw_bucket, raw_key = storage.save_raw_output(
            account_id=job.account_id,
            ingestion_id=ingestion.id,
            attempt_id=attempt.id,
            payload=json.dumps(extraction.raw_output, sort_keys=True).encode(),
        )
        attempt.raw_output_bucket = raw_bucket
        attempt.raw_output_object_key = raw_key
        attempt.processing_method = extraction.processing_method
        attempt.routing_reason = extraction.routing_reason
        attempt.internal_phase = "normalization"
        job.current_phase = "normalization"

        record = (
            db.query(models.MedicalRecord)
            .filter(models.MedicalRecord.ingestion_id == ingestion.id)
            .one_or_none()
        )
        part_by_ordinal = {part.ordinal: part for part in parts}
        _persist_result(
            db,
            job=job,
            attempt=attempt,
            ingestion=ingestion,
            record=record,
            part_by_ordinal=part_by_ordinal,
            extraction=extraction,
            publish_observations=settings.feature_observations_enabled,
        )

        finished_at = datetime.now(UTC)
        attempt.status = "ready"
        attempt.finished_at = finished_at
        job.status = "ready"
        job.current_phase = None
        job.finished_at = finished_at
        ingestion.extraction_state = "ready"
        recalculate_review_state(db, ingestion=ingestion)
        if ingestion.resolved_profile_id is None:
            ingestion.assignment_state = "needs_assignment"
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        job = db.query(models.ExtractionJob).filter(models.ExtractionJob.id == job_id).one()
        attempt = (
            db.query(models.ExtractionAttempt)
            .filter(
                models.ExtractionAttempt.job_id == job.id,
                models.ExtractionAttempt.attempt_number == attempt_number,
            )
            .one()
        )
        ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == job.ingestion_id).one()
        finished_at = datetime.now(UTC)
        attempt.status = "failed"
        attempt.failure_code = "extraction_failed"
        attempt.finished_at = finished_at
        job.status = "failed"
        job.current_phase = None
        job.failure_code = "extraction_failed"
        job.finished_at = finished_at
        ingestion.extraction_state = "failed"
        db.commit()

    db.refresh(job)
    return job


def retry_extraction_job(
    db: Session,
    *,
    job: models.ExtractionJob,
    settings: Settings,
    storage: LocalPrivateStorage,
    extractor: Extractor,
) -> models.ExtractionJob:
    job.status = "queued"
    job.current_phase = None
    job.failure_code = None
    job.finished_at = None
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == job.ingestion_id).one()
    ingestion.extraction_state = "queued"
    db.commit()
    return run_extraction_job(
        db, job_id=job.id, settings=settings, storage=storage, extractor=extractor
    )


def parse_iso_date(value: dict | None) -> date | None:
    if not value:
        return None
    raw = value.get("date")
    if not isinstance(raw, str):
        return None
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return None


def _persist_result(
    db: Session,
    *,
    job: models.ExtractionJob,
    attempt: models.ExtractionAttempt,
    ingestion: models.Ingestion,
    record: models.MedicalRecord | None,
    part_by_ordinal: dict[int, models.IngestionPart],
    extraction,
    publish_observations: bool,
) -> None:
    reviewed_metadata_types, reviewed_memory_keys = _discard_unreviewed_prior_items(
        db, ingestion=ingestion, attempt_id=attempt.id
    )

    for datum in extraction.patient_evidence:
        patient_item = models.PatientEvidence(
            account_id=job.account_id,
            ingestion_id=ingestion.id,
            attempt_id=attempt.id,
            extracted_name=datum.extracted_name,
            normalized_name=datum.normalized_name,
            date_of_birth=datum.date_of_birth,
            patient_identifier=datum.patient_identifier,
            confidence=datum.confidence,
        )
        db.add(patient_item)
        db.flush()
        _add_references(
            db,
            account_id=job.account_id,
            part_by_ordinal=part_by_ordinal,
            references=datum.source_references,
            patient_evidence_id=patient_item.id,
        )

    for datum in extraction.metadata_candidates:
        if datum.metadata_type in reviewed_metadata_types:
            continue
        metadata_item = models.DocumentMetadataCandidate(
            account_id=job.account_id,
            ingestion_id=ingestion.id,
            record_id=record.id if record else None,
            profile_id=ingestion.resolved_profile_id,
            attempt_id=attempt.id,
            metadata_type=datum.metadata_type,
            original_value=datum.value,
            confidence=datum.confidence,
        )
        db.add(metadata_item)
        db.flush()
        _add_references(
            db,
            account_id=job.account_id,
            part_by_ordinal=part_by_ordinal,
            references=datum.source_references,
            metadata_candidate_id=metadata_item.id,
        )

    # Observations stay unpublished until the observation slice is enabled.
    observations = extraction.observations if publish_observations else []
    for datum in observations:
        prior_active = (
            db.query(models.MetricObservation)
            .filter(
                models.MetricObservation.ingestion_id == ingestion.id,
                models.MetricObservation.metric_identity == datum.metric_identity,
                models.MetricObservation.is_active.is_(True),
            )
            .all()
        )
        observation_item = models.MetricObservation(
            account_id=job.account_id,
            ingestion_id=ingestion.id,
            record_id=record.id if record else None,
            profile_id=ingestion.resolved_profile_id,
            attempt_id=attempt.id,
            metric_identity=datum.metric_identity,
            label=datum.label,
            original_value=datum.original_value,
            original_unit=datum.original_unit,
            normalized_value=datum.normalized_value,
            normalized_unit=datum.normalized_unit,
            reference_range=datum.reference_range,
            flag=datum.flag,
            observed_on=datum.observed_on,
            body_system=datum.body_system,
            confidence=datum.confidence,
        )
        db.add(observation_item)
        db.flush()
        for prior in prior_active:
            prior.is_active = False
            prior.superseded_by_id = observation_item.id
        _add_references(
            db,
            account_id=job.account_id,
            part_by_ordinal=part_by_ordinal,
            references=datum.source_references,
            metric_observation_id=observation_item.id,
        )

    for datum in extraction.memory_candidates:
        if (datum.subtype, datum.label) in reviewed_memory_keys:
            continue
        memory_item = models.MemoryCandidate(
            account_id=job.account_id,
            ingestion_id=ingestion.id,
            record_id=record.id if record else None,
            profile_id=ingestion.resolved_profile_id,
            attempt_id=attempt.id,
            subtype=datum.subtype,
            label=datum.label,
            original_value=datum.value,
            exact_condition_text=datum.exact_condition_text,
            confidence=datum.confidence,
        )
        db.add(memory_item)
        db.flush()
        _add_references(
            db,
            account_id=job.account_id,
            part_by_ordinal=part_by_ordinal,
            references=datum.source_references,
            memory_candidate_id=memory_item.id,
        )


def _discard_unreviewed_prior_items(
    db: Session, *, ingestion: models.Ingestion, attempt_id: str
) -> tuple[set[str], set[tuple[str, str]]]:
    """Clear an earlier attempt's unreviewed items so a retry cannot duplicate them.

    Patient evidence is internal matching input, so only the newest attempt's evidence
    survives. Candidates the owner already decided on are kept, and this attempt skips
    re-proposing them, so a retry never replaces a review decision with a pending copy.
    """

    stale_evidence = (
        db.query(models.PatientEvidence)
        .filter(
            models.PatientEvidence.ingestion_id == ingestion.id,
            models.PatientEvidence.attempt_id != attempt_id,
        )
        .all()
    )
    prior_metadata = (
        db.query(models.DocumentMetadataCandidate)
        .filter(
            models.DocumentMetadataCandidate.ingestion_id == ingestion.id,
            models.DocumentMetadataCandidate.attempt_id != attempt_id,
        )
        .all()
    )
    prior_memory = (
        db.query(models.MemoryCandidate)
        .filter(
            models.MemoryCandidate.ingestion_id == ingestion.id,
            models.MemoryCandidate.attempt_id != attempt_id,
        )
        .all()
    )

    stale_metadata = [item for item in prior_metadata if item.review_status == "pending"]
    stale_memory = [item for item in prior_memory if item.review_status == "pending"]

    _delete_source_references(
        db,
        patient_evidence_ids=[item.id for item in stale_evidence],
        metadata_candidate_ids=[item.id for item in stale_metadata],
        memory_candidate_ids=[item.id for item in stale_memory],
    )
    for item in (*stale_evidence, *stale_metadata, *stale_memory):
        db.delete(item)
    db.flush()

    reviewed_metadata_types = {
        item.metadata_type for item in prior_metadata if item.review_status != "pending"
    }
    reviewed_memory_keys = {
        (item.subtype, item.label) for item in prior_memory if item.review_status != "pending"
    }
    return reviewed_metadata_types, reviewed_memory_keys


def _delete_source_references(
    db: Session,
    *,
    patient_evidence_ids: list[str],
    metadata_candidate_ids: list[str],
    memory_candidate_ids: list[str],
) -> None:
    for column, item_ids in (
        (models.SourceReference.patient_evidence_id, patient_evidence_ids),
        (models.SourceReference.metadata_candidate_id, metadata_candidate_ids),
        (models.SourceReference.memory_candidate_id, memory_candidate_ids),
    ):
        if not item_ids:
            continue
        for reference in db.query(models.SourceReference).filter(column.in_(item_ids)).all():
            db.delete(reference)


def _add_references(
    db: Session,
    *,
    account_id: str,
    part_by_ordinal: dict[int, models.IngestionPart],
    references: list[SourceReferenceData],
    patient_evidence_id: str | None = None,
    metadata_candidate_id: str | None = None,
    metric_observation_id: str | None = None,
    memory_candidate_id: str | None = None,
) -> None:
    for reference in references:
        part = part_by_ordinal.get(reference.part_ordinal)
        if part is None:
            raise ValueError("Extraction source reference points to an unavailable source part.")
        db.add(
            models.SourceReference(
                account_id=account_id,
                part_id=part.id,
                patient_evidence_id=patient_evidence_id,
                metadata_candidate_id=metadata_candidate_id,
                metric_observation_id=metric_observation_id,
                memory_candidate_id=memory_candidate_id,
                logical_page=reference.logical_page,
                native_word_ids=reference.native_word_ids,
                textract_block_ids=reference.textract_block_ids,
                text_span=reference.text_span,
                bounding_polygon=reference.bounding_polygon,
            )
        )
