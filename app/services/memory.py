from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app import models
from app.schemas import RecordReviewRequest
from app.services.extraction import parse_iso_date

MEMORY_FIELD_TYPES = {"condition", "medication", "test_result", "follow_up"}
TRUSTED_STATUSES = {"confirmed", "edited"}


def apply_record_review(
    db: Session,
    *,
    user_id: str,
    record: models.MedicalRecord,
    review: RecordReviewRequest,
) -> models.MedicalRecord:
    decision_by_id = {decision.field_id: decision for decision in review.decisions}
    fields = (
        db.query(models.ExtractedField)
        .filter(
            models.ExtractedField.record_id == record.id,
            models.ExtractedField.user_id == user_id,
            models.ExtractedField.id.in_(decision_by_id.keys()),
        )
        .all()
    )

    now = datetime.now(UTC)
    for field in fields:
        decision = decision_by_id[field.id]
        if decision.action == "confirm":
            field.confirmation_status = "confirmed"
        elif decision.action == "edit":
            field.confirmation_status = "edited"
            if decision.value is not None:
                field.value = decision.value
                field.normalized_value = decision.value
        elif decision.action == "ignore":
            field.confirmation_status = "ignored"
        elif decision.action == "incorrect":
            field.confirmation_status = "incorrect"
        field.reviewed_at = now

    db.flush()
    _apply_record_metadata(record, db)
    _rebuild_memory_for_record(db, record=record)

    pending_count = (
        db.query(models.ExtractedField)
        .filter(
            models.ExtractedField.record_id == record.id,
            models.ExtractedField.confirmation_status == "pending",
        )
        .count()
    )
    if pending_count == 0:
        record.status = "reviewed"

    db.commit()
    db.refresh(record)
    return record


def _apply_record_metadata(record: models.MedicalRecord, db: Session) -> None:
    trusted_fields = (
        db.query(models.ExtractedField)
        .filter(
            models.ExtractedField.record_id == record.id,
            models.ExtractedField.confirmation_status.in_(TRUSTED_STATUSES),
        )
        .all()
    )
    for field in trusted_fields:
        value = field.normalized_value or field.value
        if field.field_type == "document_type":
            record.record_type = value.get("text")
        elif field.field_type == "record_date":
            record.record_date = parse_iso_date(value)


def _rebuild_memory_for_record(db: Session, *, record: models.MedicalRecord) -> None:
    (
        db.query(models.MemoryFact)
        .filter(models.MemoryFact.source_record_id == record.id, models.MemoryFact.user_id == record.user_id)
        .delete()
    )

    trusted_fields = (
        db.query(models.ExtractedField)
        .filter(
            models.ExtractedField.record_id == record.id,
            models.ExtractedField.field_type.in_(MEMORY_FIELD_TYPES),
            models.ExtractedField.confirmation_status.in_(TRUSTED_STATUSES),
        )
        .all()
    )
    for field in trusted_fields:
        details = field.normalized_value or field.value
        db.add(
            models.MemoryFact(
                user_id=record.user_id,
                profile_id=record.profile_id,
                source_record_id=record.id,
                source_field_id=field.id,
                category=field.field_type,
                title=field.label,
                details=details,
                body_system=details.get("body_system"),
                occurred_on=record.record_date,
            )
        )

