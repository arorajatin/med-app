import pytest
from fastapi.testclient import TestClient

from app import models
from app.ai.base import DocumentExtraction, ExtractedDatum, Extractor
from app.api.deps import get_extractor
from app.config import get_settings
from app.database import Base, bootstrap_test_database, configure_database, get_db, get_engine
from app.main import create_app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    get_settings.cache_clear()
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("LOCAL_STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("DEV_AUTH_ENABLED", "true")
    monkeypatch.setenv("EXTRACTION_RUN_INLINE", "true")
    configure_database(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.drop_all(bind=get_engine())
    bootstrap_test_database()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


def auth(user_id: str = "user_1") -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}"}


def test_upload_extract_review_and_memory_flow_does_not_infer_a_condition(client):
    profile = client.post(
        "/profiles",
        headers=auth(),
        json={"display_name": "Self", "relationship": "self"},
    ).json()

    record = client.post(
        "/records",
        headers=auth(),
        json={
            "profile_id": profile["id"],
            "title": "June lab report",
            "ai_processing_consent": True,
        },
    ).json()

    upload = client.post(
        f"/records/{record['id']}/files",
        headers=auth(),
        files={
            "upload": (
                "lab.txt",
                b"Lab report 2026-06-01 creatinine 1.2 kidney follow up",
                "text/plain",
            )
        },
    )
    assert upload.status_code == 201
    payload = upload.json()
    assert payload["file"]["filename"] == "lab.txt"
    assert payload["extraction_job"]["status"] == "ready"

    extraction = client.get(f"/records/{record['id']}/extraction", headers=auth()).json()
    assert extraction["record"]["status"] == "extraction_ready"
    assert extraction["fields"]
    assert all(field["field_type"] != "condition" for field in extraction["fields"])

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert memory["facts"] == []

    decisions = [
        {"field_id": field["id"], "action": "confirm"}
        for field in extraction["fields"]
        if field["field_type"] in {"record_date", "test_result"}
    ]
    reviewed = client.patch(
        f"/records/{record['id']}/review",
        headers=auth(),
        json={"decisions": decisions},
    )
    assert reviewed.status_code == 200

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    categories = {fact["category"] for fact in memory["facts"]}
    assert "condition" not in categories
    assert "test_result" in categories
    assert all(fact["source_record_id"] == record["id"] for fact in memory["facts"])


def test_user_cannot_access_another_users_profile(client):
    profile = client.post(
        "/profiles",
        headers=auth("owner"),
        json={"display_name": "Owner", "relationship": "self"},
    ).json()

    response = client.get(f"/profiles/{profile['id']}", headers=auth("other"))
    assert response.status_code == 404


def test_appointment_checklist_uses_confirmed_memory(client):
    profile = client.post(
        "/profiles",
        headers=auth(),
        json={"display_name": "Self", "relationship": "self"},
    ).json()
    record = client.post(
        "/records",
        headers=auth(),
        json={"profile_id": profile["id"], "title": "Kidney lab", "ai_processing_consent": True},
    ).json()
    client.post(
        f"/records/{record['id']}/files",
        headers=auth(),
        files={
            "upload": (
                "lab.txt",
                b"Lab report 2026-06-01 creatinine 1.2 kidney",
                "text/plain",
            )
        },
    )
    extraction = client.get(f"/records/{record['id']}/extraction", headers=auth()).json()
    assert all(field["field_type"] != "condition" for field in extraction["fields"])
    decisions = [
        {"field_id": field["id"], "action": "confirm"}
        for field in extraction["fields"]
        if field["field_type"] == "test_result"
    ]
    client.patch(f"/records/{record['id']}/review", headers=auth(), json={"decisions": decisions})

    appointment = client.post(
        "/appointments",
        headers=auth(),
        json={
            "profile_id": profile["id"],
            "scheduled_for": "2026-06-20T10:00:00Z",
            "reason": "Follow-up",
        },
    ).json()
    checklist = client.post(
        f"/appointments/{appointment['id']}/checklist/generate",
        headers=auth(),
    )
    assert checklist.status_code == 200
    questions = [item["question"] for item in checklist.json()]
    assert any("Creatinine" in question for question in questions)
    assert all("Kidney" not in question for question in questions)


def test_legacy_condition_memory_is_hidden_from_reads_and_appointments(client):
    profile = client.post(
        "/profiles",
        headers=auth(),
        json={"display_name": "Self", "relationship": "self"},
    ).json()

    appointment = client.post(
        "/appointments",
        headers=auth(),
        json={
            "profile_id": profile["id"],
            "scheduled_for": "2026-06-20T10:00:00Z",
            "reason": "Follow-up",
        },
    ).json()

    db = next(get_db())
    try:
        legacy_fact = models.MemoryFact(
            user_id="user_1",
            profile_id=profile["id"],
            source_record_id="legacy-record",
            source_field_id="legacy-inferred-condition",
            category="condition",
            title="Legacy inferred condition",
            details={"text": "Legacy inferred condition"},
        )
        db.add(legacy_fact)
        db.flush()
        db.add(
            models.AppointmentChecklistItem(
                user_id="user_1",
                profile_id=profile["id"],
                appointment_id=appointment["id"],
                question="How should we interpret the legacy inferred condition?",
                source_fact_id=legacy_fact.id,
                is_generic=False,
            )
        )
        db.commit()
        legacy_fact_id = legacy_fact.id
    finally:
        db.close()

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert memory["facts"] == []

    existing_checklist = client.get(
        f"/appointments/{appointment['id']}/checklist",
        headers=auth(),
    ).json()
    assert existing_checklist == []

    db = next(get_db())
    try:
        db.query(models.MemoryFact).filter(models.MemoryFact.id == legacy_fact_id).delete()
        db.commit()
    finally:
        db.close()

    orphaned_checklist = client.get(
        f"/appointments/{appointment['id']}/checklist",
        headers=auth(),
    ).json()
    assert orphaned_checklist == []

    checklist = client.post(
        f"/appointments/{appointment['id']}/checklist/generate",
        headers=auth(),
    ).json()

    assert len(checklist) == 1
    assert checklist[0]["is_generic"] is True
    assert "Legacy inferred condition" not in checklist[0]["question"]


def test_unsafe_provider_condition_output_never_reaches_persistence(client):
    class UnsafeExtractor(Extractor):
        # A provider name alone must not grant access to the temporary mock-only path.
        provider_name = "mock"

        def extract_document(self, **kwargs):
            fields = [
                ExtractedDatum(
                    field_type=field_type,
                    label=field_type,
                    value={"text": "Unvalidated output"},
                    confidence=0.99,
                    source_reference="unresolved:reference",
                )
                for field_type in (
                    "condition",
                    "documented_condition_candidate",
                    "diagnosis_candidate",
                    "clinical_impression",
                )
            ]
            fields.append(
                ExtractedDatum(
                    field_type="test_result",
                    label="Inferred kidney disease",
                    value={"text": "Inferred kidney disease"},
                    confidence=0.9,
                    source_reference="test:result",
                )
            )
            return DocumentExtraction(
                document_type="Inferred kidney disease",
                raw_output={
                    "field_count": len(fields),
                    "condition": {"text": "Inferred kidney disease"},
                },
                fields=fields,
            )

    profile = client.post(
        "/profiles",
        headers=auth(),
        json={"display_name": "Self", "relationship": "self"},
    ).json()
    record = client.post(
        "/records",
        headers=auth(),
        json={"profile_id": profile["id"], "title": "Unsafe provider test"},
    ).json()

    client.app.dependency_overrides[get_extractor] = UnsafeExtractor
    try:
        upload = client.post(
            f"/records/{record['id']}/files",
            headers=auth(),
            files={"upload": ("lab.txt", b"Lab report creatinine 1.2", "text/plain")},
        )
    finally:
        client.app.dependency_overrides.pop(get_extractor, None)

    assert upload.status_code == 201
    extraction = client.get(f"/records/{record['id']}/extraction", headers=auth()).json()
    assert extraction["fields"] == []

    db = next(get_db())
    try:
        stored_types = {
            field.field_type
            for field in db.query(models.ExtractedField)
            .filter(models.ExtractedField.record_id == record["id"])
            .all()
        }
        job = (
            db.query(models.ExtractionJob)
            .filter(models.ExtractionJob.record_id == record["id"])
            .one()
        )
    finally:
        db.close()

    assert stored_types == set()
    assert job.raw_output["provider_field_count"] == 5
    assert job.raw_output["field_count"] == 0
    assert job.raw_output["document_type"] == "unknown"
    assert job.raw_output["condition_safety"]["omitted_field_count"] == 5
    assert job.raw_output["condition_safety"]["provider_output_persisted"] is False
    assert "condition" not in job.raw_output

    review = client.patch(
        f"/records/{record['id']}/review",
        headers=auth(),
        json={"decisions": [{"field_id": "omitted-condition", "action": "confirm"}]},
    )
    assert review.status_code == 400


def test_provider_exception_text_is_not_persisted_or_returned(client):
    class RaisingExtractor(Extractor):
        provider_name = "unsafe-test"

        def extract_document(self, **kwargs):
            raise RuntimeError("Provider inferred kidney disease from creatinine")

    profile = client.post(
        "/profiles",
        headers=auth(),
        json={"display_name": "Self", "relationship": "self"},
    ).json()
    record = client.post(
        "/records",
        headers=auth(),
        json={"profile_id": profile["id"], "title": "Provider failure test"},
    ).json()

    client.app.dependency_overrides[get_extractor] = RaisingExtractor
    try:
        upload = client.post(
            f"/records/{record['id']}/files",
            headers=auth(),
            files={"upload": ("lab.txt", b"Lab report creatinine 1.2", "text/plain")},
        )
    finally:
        client.app.dependency_overrides.pop(get_extractor, None)

    assert upload.status_code == 201
    job = upload.json()["extraction_job"]
    assert job["status"] == "failed"
    assert job["failure_reason"] == "extraction_failed"
    assert "kidney" not in str(job).casefold()

    db = next(get_db())
    try:
        stored_job = db.query(models.ExtractionJob).filter(models.ExtractionJob.id == job["id"]).one()
        assert stored_job.failure_reason == "extraction_failed"
        assert stored_job.raw_output is None
    finally:
        db.close()


def test_hidden_legacy_condition_does_not_block_review_completion(client):
    profile = client.post(
        "/profiles",
        headers=auth(),
        json={"display_name": "Self", "relationship": "self"},
    ).json()
    record = client.post(
        "/records",
        headers=auth(),
        json={"profile_id": profile["id"], "title": "Legacy review test"},
    ).json()
    client.post(
        f"/records/{record['id']}/files",
        headers=auth(),
        files={"upload": ("lab.txt", b"Lab report 2026-06-01", "text/plain")},
    )

    db = next(get_db())
    try:
        job = (
            db.query(models.ExtractionJob)
            .filter(models.ExtractionJob.record_id == record["id"])
            .one()
        )
        legacy_field = models.ExtractedField(
            user_id="user_1",
            profile_id=profile["id"],
            record_id=record["id"],
            job_id=job.id,
            field_type="condition",
            label="Legacy inferred condition",
            value={"text": "Legacy inferred condition"},
            confidence=0.99,
            source_reference="legacy:inference",
            confirmation_status="pending",
        )
        db.add(legacy_field)
        db.commit()
        legacy_field_id = legacy_field.id
    finally:
        db.close()

    extraction = client.get(f"/records/{record['id']}/extraction", headers=auth()).json()
    assert all(field["id"] != legacy_field_id for field in extraction["fields"])

    rejected = client.patch(
        f"/records/{record['id']}/review",
        headers=auth(),
        json={"decisions": [{"field_id": legacy_field_id, "action": "confirm"}]},
    )
    assert rejected.status_code == 400

    visible_decisions = [
        {"field_id": field["id"], "action": "confirm"}
        for field in extraction["fields"]
    ]
    reviewed = client.patch(
        f"/records/{record['id']}/review",
        headers=auth(),
        json={"decisions": visible_decisions},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["record"]["status"] == "reviewed"
