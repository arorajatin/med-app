import base64
import binascii
import json
from datetime import UTC
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app import models
from app.schemas import FeedItemRead, FeedRead
from app.services.common import require_profile

FeedOrder = Literal["upload_date", "report_date"]


def list_feed(
    db: Session,
    *,
    account_id: str,
    order: FeedOrder,
    cursor: str | None,
    limit: int,
    profile_id: str | None = None,
) -> FeedRead:
    if profile_id is not None:
        require_profile(db, account_id=account_id, profile_id=profile_id)
    ingestion = models.Ingestion
    record = models.MedicalRecord
    pending_metadata = (
        db.query(models.DocumentMetadataCandidate.id)
        .filter(
            models.DocumentMetadataCandidate.account_id == account_id,
            models.DocumentMetadataCandidate.ingestion_id == ingestion.id,
            models.DocumentMetadataCandidate.review_status == "pending",
        )
        .exists()
    )
    query = (
        db.query(ingestion, record, models.Profile, pending_metadata)
        .outerjoin(
            record,
            and_(record.ingestion_id == ingestion.id, record.account_id == account_id),
        )
        .outerjoin(
            models.Profile,
            and_(
                models.Profile.id == ingestion.resolved_profile_id,
                models.Profile.account_id == account_id,
            ),
        )
        .filter(
            ingestion.account_id == account_id,
            ingestion.upload_state == "complete",
            ingestion.completed_at.is_not(None),
            ingestion.tombstoned_at.is_(None),
            ingestion.source_channel.in_(("direct_file", "camera")),
        )
    )
    if profile_id is not None:
        query = query.filter(
            ingestion.assignment_state == "resolved",
            ingestion.resolved_profile_id == profile_id,
        )
    if cursor is not None:
        # The cursor is a position, never authorization. Resolve its anchor only
        # through the same owned, available upload query used for the results.
        try:
            decoded = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
            if (
                not isinstance(decoded, list)
                or len(decoded) != 4
                or decoded[:3] != [2, order, profile_id]
                or not isinstance(decoded[3], str)
            ):
                raise ValueError
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise HTTPException(400, "Invalid Feed cursor. Refresh the Feed.") from exc
        anchor = query.filter(ingestion.id == decoded[3]).one_or_none()
        if anchor is None:
            raise HTTPException(400, "Invalid Feed cursor. Refresh the Feed.")
        previous, previous_record, _, _ = anchor
        after_upload = or_(
            ingestion.completed_at < previous.completed_at,
            and_(ingestion.completed_at == previous.completed_at, ingestion.id < previous.id),
        )
        if order == "report_date":
            previous_date = previous_record.record_date if previous_record else None
            query = query.filter(
                or_(
                    record.record_date < previous_date,
                    record.record_date.is_(None),
                    and_(record.record_date == previous_date, after_upload),
                )
                if previous_date is not None
                else and_(record.record_date.is_(None), after_upload)
            )
        else:
            query = query.filter(after_upload)
    if order == "report_date":
        query = query.order_by(record.record_date.desc().nulls_last())
    rows = query.order_by(ingestion.completed_at.desc(), ingestion.id.desc()).limit(limit + 1).all()
    items = []
    for upload, report, profile, metadata_pending in rows[:limit]:
        items.append(
            FeedItemRead.model_validate(
                {
                    "id": upload.id,
                    "record_id": report.id if report else None,
                    "profile": profile if upload.assignment_state == "resolved" else None,
                    "display_filename": (
                        report.display_filename if report else upload.display_filename
                    )
                    or "Medical report",
                    "source_channel": upload.source_channel,
                    "source_label": (
                        "Camera capture" if upload.source_channel == "camera" else "File upload"
                    ),
                    "completed_at": (
                        upload.completed_at.replace(tzinfo=UTC)
                        if upload.completed_at.tzinfo is None
                        else upload.completed_at
                    ),
                    "report_date": report.record_date if report else None,
                    "assignment_state": upload.assignment_state,
                    "extraction_state": upload.extraction_state,
                    "review_state": upload.review_state,
                    "metadata_review_pending": metadata_pending,
                    "attention_required": (
                        upload.assignment_state == "needs_assignment"
                        or upload.extraction_state == "failed"
                        or upload.review_state == "pending"
                        or metadata_pending
                    ),
                }
            )
        )
    next_cursor = None
    if len(rows) > limit:
        next_cursor = base64.urlsafe_b64encode(
            json.dumps([2, order, profile_id, items[-1].id]).encode()
        ).decode()
    return FeedRead(items=items, next_cursor=next_cursor)
