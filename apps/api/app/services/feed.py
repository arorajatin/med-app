import base64
import binascii
import json
from datetime import UTC, date, datetime
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
        # The cursor carries the last item's sort keys, so later edits to that item
        # cannot move the page boundary. Its id must still be one of this account's
        # uploads, which keeps another account's cursor from being accepted.
        try:
            decoded = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
            if (
                not isinstance(decoded, list)
                or len(decoded) != 6
                or decoded[:3] != [3, order, profile_id]
                or not all(isinstance(value, str) for value in decoded[3:5])
                or not isinstance(decoded[5], str | None)
            ):
                raise ValueError
            previous_id = decoded[3]
            previous_completed_at = datetime.fromisoformat(decoded[4])
            previous_date = date.fromisoformat(decoded[5]) if decoded[5] else None
        except (ValueError, UnicodeDecodeError, binascii.Error) as exc:
            raise HTTPException(400, "Invalid Feed cursor. Refresh the Feed.") from exc
        owned = db.query(
            db.query(ingestion.id)
            .filter(ingestion.id == previous_id, ingestion.account_id == account_id)
            .exists()
        ).scalar()
        if not owned:
            raise HTTPException(400, "Invalid Feed cursor. Refresh the Feed.")
        after_upload = or_(
            ingestion.completed_at < previous_completed_at,
            and_(ingestion.completed_at == previous_completed_at, ingestion.id < previous_id),
        )
        if order == "report_date":
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
        last, last_report, _, _ = rows[limit - 1]
        last_date = last_report.record_date if last_report else None
        next_cursor = base64.urlsafe_b64encode(
            json.dumps(
                [
                    3,
                    order,
                    profile_id,
                    last.id,
                    last.completed_at.isoformat(),
                    last_date.isoformat() if last_date else None,
                ]
            ).encode()
        ).decode()
    return FeedRead(items=items, next_cursor=next_cursor)
