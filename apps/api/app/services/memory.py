from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models
from app.schemas import RecordReviewRequest, ReviewCandidateDecision
from app.services.common import recalculate_review_state
from app.services.extraction import parse_iso_date

TRUSTED_STATUSES = {"confirmed", "edited"}


def apply_record_review(
    db: Session,
    *,
    account_id: str,
    reviewer_identity_id: str,
    record: models.MedicalRecord,
    review: RecordReviewRequest,
) -> models.MedicalRecord:
    metadata_decisions = {
        decision.candidate_id: decision
        for decision in review.decisions
        if decision.candidate_type == "metadata"
    }
    memory_decisions = {
        decision.candidate_id: decision
        for decision in review.decisions
        if decision.candidate_type == "memory"
    }
    metadata = _load_metadata_candidates(
        db, account_id=account_id, record_id=record.id, candidate_ids=set(metadata_decisions)
    )
    memory = _load_memory_candidates(
        db, account_id=account_id, record_id=record.id, candidate_ids=set(memory_decisions)
    )
    if len(metadata) != len(metadata_decisions) or len(memory) != len(memory_decisions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more review candidates do not belong to this record.",
        )

    reviewed_at = datetime.now(UTC)
    for metadata_candidate in metadata:
        _review_metadata_candidate(
            db,
            candidate=metadata_candidate,
            decision=metadata_decisions[metadata_candidate.id],
            reviewer_identity_id=reviewer_identity_id,
            reviewed_at=reviewed_at,
        )
    for memory_candidate in memory:
        _review_memory_candidate(
            db,
            candidate=memory_candidate,
            decision=memory_decisions[memory_candidate.id],
            reviewer_identity_id=reviewer_identity_id,
            reviewed_at=reviewed_at,
        )

    db.flush()
    _apply_record_metadata(db, record=record)
    _update_memory_review_state(db, record=record)
    db.commit()
    db.refresh(record)
    return record


def _load_metadata_candidates(
    db: Session, *, account_id: str, record_id: str, candidate_ids: set[str]
) -> list[models.DocumentMetadataCandidate]:
    if not candidate_ids:
        return []
    return (
        db.query(models.DocumentMetadataCandidate)
        .filter(
            models.DocumentMetadataCandidate.account_id == account_id,
            models.DocumentMetadataCandidate.record_id == record_id,
            models.DocumentMetadataCandidate.id.in_(candidate_ids),
        )
        .all()
    )


def _load_memory_candidates(
    db: Session, *, account_id: str, record_id: str, candidate_ids: set[str]
) -> list[models.MemoryCandidate]:
    if not candidate_ids:
        return []
    return (
        db.query(models.MemoryCandidate)
        .filter(
            models.MemoryCandidate.account_id == account_id,
            models.MemoryCandidate.record_id == record_id,
            models.MemoryCandidate.id.in_(candidate_ids),
        )
        .all()
    )


def _review_metadata_candidate(
    db: Session,
    *,
    candidate: models.DocumentMetadataCandidate,
    decision: ReviewCandidateDecision,
    reviewer_identity_id: str,
    reviewed_at: datetime,
) -> None:
    candidate.review_status = _review_status(decision)
    candidate.submitted_value = decision.value if decision.action == "edit" else None
    db.add(
        models.DocumentMetadataReview(
            account_id=candidate.account_id,
            candidate_id=candidate.id,
            reviewer_identity_id=reviewer_identity_id,
            action=decision.action,
            submitted_value=decision.value,
            reviewed_at=reviewed_at,
        )
    )


def _review_memory_candidate(
    db: Session,
    *,
    candidate: models.MemoryCandidate,
    decision: ReviewCandidateDecision,
    reviewer_identity_id: str,
    reviewed_at: datetime,
) -> None:
    candidate.review_status = _review_status(decision)
    candidate.submitted_value = decision.value if decision.action == "edit" else None
    db.add(
        models.MemoryCandidateReview(
            account_id=candidate.account_id,
            candidate_id=candidate.id,
            reviewer_identity_id=reviewer_identity_id,
            action=decision.action,
            submitted_value=decision.value,
            reviewed_at=reviewed_at,
        )
    )

    prior_facts = (
        db.query(models.MemoryFact)
        .filter(
            models.MemoryFact.source_candidate_id == candidate.id,
            models.MemoryFact.is_active.is_(True),
        )
        .all()
    )
    if decision.action == "ignore":
        for fact in prior_facts:
            fact.is_active = False
            fact.superseded_at = reviewed_at
        return

    category = _memory_category(candidate.subtype)
    if category is None or candidate.profile_id is None or candidate.record_id is None:
        return
    value = decision.value if decision.action == "edit" else candidate.original_value
    source_reference = (
        db.query(models.SourceReference)
        .filter(models.SourceReference.memory_candidate_id == candidate.id)
        .order_by(models.SourceReference.id.asc())
        .first()
    )
    new_fact = models.MemoryFact(
        account_id=candidate.account_id,
        profile_id=candidate.profile_id,
        source_record_id=candidate.record_id,
        source_candidate_id=candidate.id,
        source_reference_id=source_reference.id if source_reference else None,
        provenance="reviewed_candidate",
        category=category,
        title=candidate.label,
        details=value,
    )
    db.add(new_fact)
    db.flush()
    for fact in prior_facts:
        fact.is_active = False
        fact.superseded_by_id = new_fact.id
        fact.superseded_at = reviewed_at


def _review_status(decision: ReviewCandidateDecision) -> str:
    return {"confirm": "confirmed", "edit": "edited", "ignore": "ignored"}[decision.action]


def _memory_category(subtype: str) -> str | None:
    if subtype == "prescription_medication":
        return "medication"
    if subtype == "prescription_instruction":
        return "follow_up"
    if subtype == "documented_condition_candidate":
        return "condition"
    return None


def _apply_record_metadata(db: Session, *, record: models.MedicalRecord) -> None:
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == record.ingestion_id).one()
    trusted = (
        db.query(models.DocumentMetadataCandidate)
        .filter(
            models.DocumentMetadataCandidate.record_id == record.id,
            models.DocumentMetadataCandidate.review_status.in_(TRUSTED_STATUSES),
        )
        .all()
    )
    for candidate in trusted:
        value = candidate.submitted_value or candidate.original_value
        if candidate.metadata_type == "document_type":
            record.record_type = value.get("text")
        elif candidate.metadata_type == "record_date":
            record.record_date = parse_iso_date(value)
        elif candidate.metadata_type == "issuer":
            record.issuer_name = value.get("text")
        elif candidate.metadata_type == "display_filename" and not ingestion.user_renamed:
            display_filename = value.get("text")
            if isinstance(display_filename, str) and display_filename:
                record.display_filename = display_filename
                ingestion.display_filename = display_filename


def _update_memory_review_state(db: Session, *, record: models.MedicalRecord) -> None:
    ingestion = db.query(models.Ingestion).filter(models.Ingestion.id == record.ingestion_id).one()
    recalculate_review_state(db, ingestion=ingestion)
