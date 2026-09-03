from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models


def recalculate_review_state(db: Session, *, ingestion: models.Ingestion) -> None:
    """Derive review state from the candidate memory currently persisted for an ingestion."""

    statuses = [
        review_status
        for (review_status,) in db.query(models.MemoryCandidate.review_status).filter(
            models.MemoryCandidate.ingestion_id == ingestion.id
        )
    ]
    if not statuses:
        ingestion.review_state = "not_required"
    elif "pending" in statuses:
        ingestion.review_state = "pending"
    else:
        ingestion.review_state = "reviewed"


def require_profile(db: Session, *, account_id: str, profile_id: str) -> models.Profile:
    profile = (
        db.query(models.Profile)
        .filter(models.Profile.id == profile_id, models.Profile.account_id == account_id)
        .one_or_none()
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return profile


def require_record(db: Session, *, account_id: str, record_id: str) -> models.MedicalRecord:
    record = (
        db.query(models.MedicalRecord)
        .filter(models.MedicalRecord.id == record_id, models.MedicalRecord.account_id == account_id)
        .one_or_none()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    return record


def require_ingestion(db: Session, *, account_id: str, ingestion_id: str) -> models.Ingestion:
    ingestion = (
        db.query(models.Ingestion)
        .filter(models.Ingestion.id == ingestion_id, models.Ingestion.account_id == account_id)
        .one_or_none()
    )
    if ingestion is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ingestion not found.")
    return ingestion


def require_appointment(db: Session, *, account_id: str, appointment_id: str) -> models.Appointment:
    appointment = (
        db.query(models.Appointment)
        .filter(
            models.Appointment.id == appointment_id,
            models.Appointment.account_id == account_id,
        )
        .one_or_none()
    )
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    return appointment
