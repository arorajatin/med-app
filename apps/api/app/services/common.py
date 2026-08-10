from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import models


def require_profile(db: Session, *, user_id: str, profile_id: str) -> models.Profile:
    profile = (
        db.query(models.Profile)
        .filter(models.Profile.id == profile_id, models.Profile.user_id == user_id)
        .one_or_none()
    )
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return profile


def require_record(db: Session, *, user_id: str, record_id: str) -> models.MedicalRecord:
    record = (
        db.query(models.MedicalRecord)
        .filter(models.MedicalRecord.id == record_id, models.MedicalRecord.user_id == user_id)
        .one_or_none()
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    return record


def require_appointment(db: Session, *, user_id: str, appointment_id: str) -> models.Appointment:
    appointment = (
        db.query(models.Appointment)
        .filter(models.Appointment.id == appointment_id, models.Appointment.user_id == user_id)
        .one_or_none()
    )
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")
    return appointment

