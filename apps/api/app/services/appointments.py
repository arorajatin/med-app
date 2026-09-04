from sqlalchemy.orm import Session

from app import models
from app.ai.condition_safety import is_permitted_memory_fact


def generate_checklist(
    db: Session, *, appointment: models.Appointment
) -> list[models.AppointmentChecklistItem]:
    (
        db.query(models.AppointmentChecklistItem)
        .filter(models.AppointmentChecklistItem.appointment_id == appointment.id)
        .delete()
    )

    candidate_facts = (
        db.query(models.MemoryFact)
        .filter(
            models.MemoryFact.account_id == appointment.account_id,
            models.MemoryFact.profile_id == appointment.profile_id,
            models.MemoryFact.is_active.is_(True),
        )
        .order_by(models.MemoryFact.created_at.desc())
        .all()
    )
    facts = [
        fact
        for fact in candidate_facts
        if is_permitted_memory_fact(category=fact.category, provenance=fact.provenance)
    ][:8]

    items: list[models.AppointmentChecklistItem] = []
    for fact in facts:
        question = _question_for_fact(fact)
        item = models.AppointmentChecklistItem(
            account_id=appointment.account_id,
            profile_id=appointment.profile_id,
            appointment_id=appointment.id,
            question=question,
            source_fact_id=fact.id,
            is_generic=False,
        )
        db.add(item)
        items.append(item)

    if not items:
        item = models.AppointmentChecklistItem(
            account_id=appointment.account_id,
            profile_id=appointment.profile_id,
            appointment_id=appointment.id,
            question="Are there any symptoms, medicines, or test reports I should keep tracking after this visit?",
            source_fact_id=None,
            is_generic=True,
        )
        db.add(item)
        items.append(item)

    db.commit()
    for item in items:
        db.refresh(item)
    return items


def _question_for_fact(fact: models.MemoryFact) -> str:
    if fact.category == "test_result":
        return f"Does the {fact.title} result need repeat testing or follow-up?"
    if fact.category == "medication":
        return f"Should I continue, stop, or adjust {fact.title}?"
    if fact.category == "condition":
        return f"How should we interpret the prior finding: {fact.title}?"
    if fact.category == "follow_up":
        return f"What follow-up is needed based on the earlier instruction: {fact.title}?"
    return f"What should I ask about {fact.title}?"
