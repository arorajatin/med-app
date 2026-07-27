import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import Base, bootstrap_test_database, configure_database, get_engine
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


def test_upload_extract_review_and_memory_flow(client):
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

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert memory["facts"] == []

    decisions = [
        {"field_id": field["id"], "action": "confirm"}
        for field in extraction["fields"]
        if field["field_type"] in {"record_date", "condition", "test_result"}
    ]
    reviewed = client.patch(
        f"/records/{record['id']}/review",
        headers=auth(),
        json={"decisions": decisions},
    )
    assert reviewed.status_code == 200

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    categories = {fact["category"] for fact in memory["facts"]}
    assert "condition" in categories
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
    decisions = [
        {"field_id": field["id"], "action": "confirm"}
        for field in extraction["fields"]
        if field["field_type"] in {"condition", "test_result"}
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
    assert any("Creatinine" in question or "Kidney" in question for question in questions)
