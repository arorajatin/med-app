import json
import re

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app import models
from app.ai.base import (
    DocumentExtraction,
    DocumentMetadataDatum,
    Extractor,
    MemoryCandidateDatum,
    SourceReferenceData,
)
from app.api.deps import get_extractor
from app.api.routes import router
from app.config import get_settings
from app.database import Base, bootstrap_test_database, configure_database, get_db, get_engine
from app.main import create_app


@pytest.fixture()
def storage_root(tmp_path):
    return tmp_path / "storage"


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


def create_profile(client: TestClient, *, user: str = "user_1", name: str = "Self") -> dict:
    response = client.post(
        "/profiles",
        headers=auth(user),
        json={"display_name": name, "relationship": "self"},
    )
    assert response.status_code == 201
    return response.json()


def accept_consent(client: TestClient, *, user: str = "user_1") -> dict:
    response = client.post(
        "/account/consents",
        headers=auth(user),
        json={
            "policy_version": "2026-07-01",
            "accepted_scope": {"ai_processing": True},
        },
    )
    assert response.status_code == 201
    return response.json()


def upload_document(
    client: TestClient,
    *,
    content: bytes,
    profile_id: str,
    user: str = "user_1",
    filename: str = "report.pdf",
) -> dict:
    response = client.post(
        "/ingestions/direct-file",
        headers=auth(user),
        files={"uploads": (filename, content, "application/pdf")},
        data={"provisional_profile_id": profile_id},
    )
    assert response.status_code == 201, response.text
    return response.json()


def assign(client: TestClient, *, ingestion_id: str, profile_id: str, user: str = "user_1") -> dict:
    response = client.post(
        f"/ingestions/{ingestion_id}/assignment/{profile_id}",
        headers=auth(user),
    )
    assert response.status_code == 200, response.text
    return response.json()


def confirm_all(client: TestClient, *, record_id: str, extraction: dict, user: str = "user_1"):
    decisions = [
        {"candidate_type": "metadata", "candidate_id": candidate["id"], "action": "confirm"}
        for candidate in extraction["metadata_candidates"]
    ] + [
        {"candidate_type": "memory", "candidate_id": candidate["id"], "action": "confirm"}
        for candidate in extraction["memory_candidates"]
    ]
    return client.patch(
        f"/records/{record_id}/review",
        headers=auth(user),
        json={"decisions": decisions},
    )


def ingest_and_assign(client: TestClient, *, content: bytes, profile_id: str) -> tuple[dict, dict]:
    """Upload a consented document, run extraction inline, and resolve its patient."""

    upload = upload_document(client, content=content, profile_id=profile_id)
    record = assign(client, ingestion_id=upload["ingestion"]["id"], profile_id=profile_id)
    extraction = client.get(f"/records/{record['id']}/extraction", headers=auth()).json()
    return record, extraction


def test_upload_extract_review_and_memory_flow_does_not_infer_a_condition(client):
    profile = create_profile(client)
    accept_consent(client)

    upload = upload_document(
        client,
        content=b"Lab report 2026-06-01 creatinine 1.2 kidney follow up",
        profile_id=profile["id"],
    )
    assert upload["parts"][0]["original_filename"] == "report.pdf"
    assert upload["extraction_job"]["status"] == "ready"
    # Extraction alone never resolves the patient; assignment stays explicit.
    assert upload["record"] is None
    assert upload["ingestion"]["assignment_state"] == "needs_assignment"

    record = assign(client, ingestion_id=upload["ingestion"]["id"], profile_id=profile["id"])
    extraction = client.get(f"/records/{record['id']}/extraction", headers=auth()).json()
    assert extraction["ingestion"]["extraction_state"] == "ready"
    assert extraction["ingestion"]["assignment_state"] == "resolved"
    assert {candidate["metadata_type"] for candidate in extraction["metadata_candidates"]} == {
        "document_type",
        "record_date",
    }
    assert [observation["metric_identity"] for observation in extraction["observations"]] == [
        "creatinine"
    ]
    assert [candidate["subtype"] for candidate in extraction["memory_candidates"]] == [
        "prescription_instruction"
    ]
    assert all(
        candidate["exact_condition_text"] is None for candidate in extraction["memory_candidates"]
    )
    assert extraction["source_references"]

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert memory["facts"] == []

    reviewed = confirm_all(client, record_id=record["id"], extraction=extraction)
    assert reviewed.status_code == 200
    assert reviewed.json()["ingestion"]["review_state"] == "reviewed"

    updated_record = client.get(f"/records/{record['id']}", headers=auth()).json()
    assert updated_record["record_type"] == "lab_report"
    assert updated_record["record_date"] == "2026-06-01"

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    categories = {fact["category"] for fact in memory["facts"]}
    assert "condition" not in categories
    assert categories == {"follow_up"}
    assert all(fact["source_record_id"] == record["id"] for fact in memory["facts"])
    assert all(fact["provenance"] == "reviewed_candidate" for fact in memory["facts"])
    # Deterministic measurements stay outside reviewed memory.
    assert all("creatinine" not in fact["title"].casefold() for fact in memory["facts"])


def test_metric_observations_never_become_memory_facts(client):
    profile = create_profile(client)
    accept_consent(client)

    record, extraction = ingest_and_assign(
        client,
        content=b"Lab report 2026-06-01 creatinine 1.2 hemoglobin 13.2",
        profile_id=profile["id"],
    )
    assert len(extraction["observations"]) == 2
    assert extraction["memory_candidates"] == []

    reviewed = confirm_all(client, record_id=record["id"], extraction=extraction)
    assert reviewed.status_code == 200

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert memory["facts"] == []


def test_retry_does_not_duplicate_candidates_or_active_observations(client):
    profile = create_profile(client)
    accept_consent(client)

    record, extraction = ingest_and_assign(
        client,
        content=b"Lab report 2026-06-01 creatinine 1.2 follow up",
        profile_id=profile["id"],
    )
    metadata_types = {candidate["metadata_type"] for candidate in extraction["metadata_candidates"]}
    assert len(extraction["memory_candidates"]) == 1
    assert len(extraction["observations"]) == 1

    retried = client.post(f"/extraction/jobs/{extraction['jobs'][0]['id']}/retry", headers=auth())
    assert retried.status_code == 200
    assert retried.json()["status"] == "ready"

    after = client.get(f"/records/{record['id']}/extraction", headers=auth()).json()
    assert len(after["attempts"]) == 2
    newest_attempt = after["attempts"][-1]["id"]

    # The retry replaces the prior attempt's unreviewed items instead of stacking new copies.
    assert {
        candidate["metadata_type"] for candidate in after["metadata_candidates"]
    } == metadata_types
    assert len(after["metadata_candidates"]) == len(metadata_types)
    assert len(after["memory_candidates"]) == 1
    assert len(after["observations"]) == 1
    assert all(
        candidate["attempt_id"] == newest_attempt
        for candidate in after["metadata_candidates"] + after["memory_candidates"]
    )
    assert after["observations"][0]["attempt_id"] == newest_attempt
    assert after["observations"][0]["is_active"] is True

    db = next(get_db())
    try:
        # The superseded observation is retained for audit and points at its replacement.
        observations = db.query(models.MetricObservation).all()
        superseded = [item for item in observations if not item.is_active]
        assert len(observations) == 2
        assert len(superseded) == 1
        assert superseded[0].superseded_by_id == after["observations"][0]["id"]
        # Stale candidates and their source references are gone, leaving no orphans.
        assert db.query(models.DocumentMetadataCandidate).count() == len(metadata_types)
        assert db.query(models.MemoryCandidate).count() == 1
        assert db.query(models.PatientEvidence).count() == 0
        live_candidate_ids = {
            candidate_id
            for (candidate_id,) in db.query(models.MemoryCandidate.id).union(
                db.query(models.DocumentMetadataCandidate.id)
            )
        }
        for reference in db.query(models.SourceReference).all():
            assert reference.patient_evidence_id is None
            if reference.memory_candidate_id or reference.metadata_candidate_id:
                assert (
                    reference.memory_candidate_id or reference.metadata_candidate_id
                ) in live_candidate_ids
    finally:
        db.close()


def test_retry_preserves_reviewed_decisions(client):
    profile = create_profile(client)
    accept_consent(client)

    record, extraction = ingest_and_assign(
        client,
        content=b"Prescription 2026-06-02 Tablet metformin 500 mg",
        profile_id=profile["id"],
    )
    reviewed_ids = sorted(
        candidate["id"]
        for candidate in extraction["metadata_candidates"] + extraction["memory_candidates"]
    )
    assert confirm_all(client, record_id=record["id"], extraction=extraction).status_code == 200

    memory_before = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert len(memory_before["facts"]) == 1

    retried = client.post(f"/extraction/jobs/{extraction['jobs'][0]['id']}/retry", headers=auth())
    assert retried.status_code == 200

    after = client.get(f"/records/{record['id']}/extraction", headers=auth()).json()
    # A retry never replaces a decision the owner already made with a pending copy.
    assert (
        sorted(
            candidate["id"]
            for candidate in after["metadata_candidates"] + after["memory_candidates"]
        )
        == reviewed_ids
    )
    assert all(
        candidate["review_status"] == "confirmed"
        for candidate in after["metadata_candidates"] + after["memory_candidates"]
    )
    assert after["ingestion"]["review_state"] == "reviewed"

    memory_after = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert [fact["id"] for fact in memory_after["facts"]] == [
        fact["id"] for fact in memory_before["facts"]
    ]

    updated_record = client.get(f"/records/{record['id']}", headers=auth()).json()
    assert updated_record["record_type"] == "prescription"
    assert updated_record["record_date"] == "2026-06-02"


def test_user_cannot_access_another_users_profile(client):
    profile = create_profile(client, user="owner", name="Owner")

    response = client.get(f"/profiles/{profile['id']}", headers=auth("other"))
    assert response.status_code == 404


def test_appointment_checklist_uses_confirmed_memory(client):
    profile = create_profile(client)
    accept_consent(client)

    record, extraction = ingest_and_assign(
        client,
        content=b"Prescription 2026-06-02 Tablet metformin 500 mg",
        profile_id=profile["id"],
    )
    assert [candidate["subtype"] for candidate in extraction["memory_candidates"]] == [
        "prescription_medication"
    ]
    assert confirm_all(client, record_id=record["id"], extraction=extraction).status_code == 200

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
    assert any("metformin" in question for question in questions)
    assert all(item["source_fact_id"] for item in checklist.json())


def test_untrusted_condition_memory_is_hidden_from_reads_and_appointments(client):
    profile = create_profile(client)
    account = client.get("/account", headers=auth()).json()

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
        untrusted_fact = models.MemoryFact(
            account_id=account["id"],
            profile_id=profile["id"],
            provenance="reviewed_candidate",
            category="condition",
            title="Untrusted inferred condition",
            details={"text": "Untrusted inferred condition"},
        )
        db.add(untrusted_fact)
        db.flush()
        db.add(
            models.AppointmentChecklistItem(
                account_id=account["id"],
                profile_id=profile["id"],
                appointment_id=appointment["id"],
                question="How should we interpret the untrusted inferred condition?",
                source_fact_id=untrusted_fact.id,
                is_generic=False,
            )
        )
        db.commit()
        untrusted_fact_id = untrusted_fact.id
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
        db.query(models.MemoryFact).filter(models.MemoryFact.id == untrusted_fact_id).delete()
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
    assert "Untrusted inferred condition" not in checklist[0]["question"]


def test_unsafe_provider_condition_output_never_reaches_persistence(client, storage_root):
    class UnsafeExtractor(Extractor):
        # A provider name alone must not grant access to the temporary mock-only path.
        provider_name = "mock"

        def extract_document(self, **kwargs):
            reference = SourceReferenceData(
                part_ordinal=0,
                logical_page=1,
                text_span="Inferred kidney disease",
                bounding_polygon=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
            )
            memory_candidates = [
                MemoryCandidateDatum(
                    subtype=subtype,
                    label=subtype,
                    value={"text": "Unvalidated output"},
                    confidence=0.99,
                    exact_condition_text="Inferred kidney disease",
                    source_references=[reference],
                )
                for subtype in (
                    "condition",
                    "documented_condition_candidate",
                    "diagnosis_candidate",
                    "clinical_impression",
                )
            ]
            memory_candidates.append(
                MemoryCandidateDatum(
                    subtype="prescription_medication",
                    label="Inferred kidney disease",
                    value={"medication_name": "Inferred kidney disease"},
                    confidence=0.9,
                    source_references=[reference],
                )
            )
            return DocumentExtraction(
                document_type="Inferred kidney disease",
                raw_output={
                    "item_count": len(memory_candidates),
                    "condition": {"text": "Inferred kidney disease"},
                },
                processing_method="native_text",
                routing_reason="unsafe_test_provider",
                metadata_candidates=[
                    DocumentMetadataDatum(
                        metadata_type="condition_summary",
                        value={"text": "Inferred kidney disease"},
                        confidence=0.9,
                        source_references=[reference],
                    )
                ],
                memory_candidates=memory_candidates,
            )

    profile = create_profile(client)
    accept_consent(client)

    client.app.dependency_overrides[get_extractor] = UnsafeExtractor
    try:
        upload = upload_document(
            client,
            content=b"Lab report creatinine 1.2",
            profile_id=profile["id"],
        )
    finally:
        client.app.dependency_overrides.pop(get_extractor, None)

    assert upload["extraction_job"]["status"] == "ready"
    record = assign(client, ingestion_id=upload["ingestion"]["id"], profile_id=profile["id"])
    extraction = client.get(f"/records/{record['id']}/extraction", headers=auth()).json()
    assert extraction["memory_candidates"] == []
    assert extraction["metadata_candidates"] == []
    assert extraction["observations"] == []
    assert extraction["patient_evidence"] == []
    assert extraction["source_references"] == []
    assert "kidney" not in json.dumps(extraction).casefold()

    db = next(get_db())
    try:
        attempt = db.query(models.ExtractionAttempt).one()
        raw_output_key = attempt.raw_output_object_key
        assert db.query(models.MemoryCandidate).count() == 0
        assert db.query(models.MemoryFact).count() == 0
    finally:
        db.close()

    raw_output = json.loads((storage_root / raw_output_key).read_bytes())
    assert raw_output["provider_item_count"] == 6
    assert raw_output["item_count"] == 0
    assert raw_output["document_type"] == "unknown"
    assert raw_output["condition_safety"]["omitted_item_count"] == 6
    assert raw_output["condition_safety"]["provider_output_persisted"] is False
    assert raw_output["condition_safety"]["baseline_item_output_enabled"] is False
    assert "condition" not in raw_output
    assert "kidney" not in json.dumps(raw_output).casefold()

    review = client.patch(
        f"/records/{record['id']}/review",
        headers=auth(),
        json={
            "decisions": [
                {
                    "candidate_type": "memory",
                    "candidate_id": "omitted-condition",
                    "action": "confirm",
                }
            ]
        },
    )
    assert review.status_code == 400


def test_provider_exception_text_is_not_persisted_or_returned(client):
    class RaisingExtractor(Extractor):
        provider_name = "unsafe-test"

        def extract_document(self, **kwargs):
            raise RuntimeError("Provider inferred kidney disease from creatinine")

    profile = create_profile(client)
    accept_consent(client)

    client.app.dependency_overrides[get_extractor] = RaisingExtractor
    try:
        upload = upload_document(
            client,
            content=b"Lab report creatinine 1.2",
            profile_id=profile["id"],
        )
    finally:
        client.app.dependency_overrides.pop(get_extractor, None)

    job = upload["extraction_job"]
    assert job["status"] == "failed"
    assert job["failure_code"] == "extraction_failed"
    assert upload["ingestion"]["extraction_state"] == "failed"
    assert "kidney" not in json.dumps(upload).casefold()

    db = next(get_db())
    try:
        stored_job = (
            db.query(models.ExtractionJob).filter(models.ExtractionJob.id == job["id"]).one()
        )
        attempt = db.query(models.ExtractionAttempt).one()
        assert stored_job.failure_code == "extraction_failed"
        assert attempt.failure_code == "extraction_failed"
        # No provider output survives a failed attempt.
        assert attempt.raw_output_object_key is None
        assert attempt.raw_output_bucket is None
    finally:
        db.close()


def test_hidden_unsupported_condition_does_not_block_review_completion(client):
    profile = create_profile(client)
    accept_consent(client)

    record, extraction = ingest_and_assign(
        client,
        content=(
            b"Prescription 2026-06-03 Diagnosis: seasonal allergic rhinitis Tablet cetirizine 10 mg"
        ),
        profile_id=profile["id"],
    )
    # The condition literally present in the document is never persisted as a candidate.
    assert "rhinitis" not in json.dumps(extraction).casefold()
    assert [candidate["subtype"] for candidate in extraction["memory_candidates"]] == [
        "prescription_medication"
    ]

    rejected = client.patch(
        f"/records/{record['id']}/review",
        headers=auth(),
        json={
            "decisions": [
                {
                    "candidate_type": "memory",
                    "candidate_id": "omitted-documented-condition",
                    "action": "confirm",
                }
            ]
        },
    )
    assert rejected.status_code == 400

    reviewed = confirm_all(client, record_id=record["id"], extraction=extraction)
    assert reviewed.status_code == 200
    assert reviewed.json()["ingestion"]["review_state"] == "reviewed"

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert {fact["category"] for fact in memory["facts"]} == {"medication"}


def test_ignored_candidate_leaves_no_trusted_memory(client):
    profile = create_profile(client)
    accept_consent(client)

    record, extraction = ingest_and_assign(
        client,
        content=b"Prescription 2026-06-04 Tablet amlodipine 5 mg",
        profile_id=profile["id"],
    )
    candidate = extraction["memory_candidates"][0]

    confirmed = client.patch(
        f"/records/{record['id']}/review",
        headers=auth(),
        json={
            "decisions": [
                {
                    "candidate_type": "memory",
                    "candidate_id": candidate["id"],
                    "action": "confirm",
                }
            ]
        },
    )
    assert confirmed.status_code == 200
    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert len(memory["facts"]) == 1

    ignored = client.patch(
        f"/records/{record['id']}/review",
        headers=auth(),
        json={
            "decisions": [
                {
                    "candidate_type": "memory",
                    "candidate_id": candidate["id"],
                    "action": "ignore",
                }
            ]
        },
    )
    assert ignored.status_code == 200

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert memory["facts"] == []


def test_upload_without_consent_is_stored_without_extraction(client):
    profile = create_profile(client)

    upload = upload_document(
        client,
        content=b"Lab report 2026-06-01 creatinine 1.2",
        profile_id=profile["id"],
    )

    assert upload["extraction_job"] is None
    assert upload["ingestion"]["extraction_state"] == "not_requested"
    assert upload["ingestion"]["assignment_state"] == "resolved"
    assert upload["record"] is not None

    extraction = client.get(f"/records/{upload['record']['id']}/extraction", headers=auth()).json()
    assert extraction["jobs"] == []
    assert extraction["observations"] == []
    assert extraction["memory_candidates"] == []


def test_another_account_cannot_read_an_owned_ingestion(client):
    profile = create_profile(client)
    accept_consent(client)
    upload = upload_document(
        client,
        content=b"Lab report 2026-06-01 creatinine 1.2",
        profile_id=profile["id"],
    )
    record = assign(client, ingestion_id=upload["ingestion"]["id"], profile_id=profile["id"])

    assert client.get(f"/records/{record['id']}", headers=auth("intruder")).status_code == 404
    assert (
        client.get(
            f"/ingestions/{upload['ingestion']['id']}/extraction", headers=auth("intruder")
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/extraction/jobs/{upload['extraction_job']['id']}", headers=auth("intruder")
        ).status_code
        == 404
    )


def test_appointment_review_records_feedback_and_rejects_invalid_ratings(client):
    profile = create_profile(client)
    appointment = client.post(
        "/appointments",
        headers=auth(),
        json={"profile_id": profile["id"], "scheduled_for": "2026-06-20T10:00:00Z"},
    ).json()

    accepted = client.post(
        f"/appointments/{appointment['id']}/review",
        headers=auth(),
        json={"stars": 4},
    )
    assert accepted.status_code == 201
    assert accepted.json()["stars"] == 4

    appointments = client.get(f"/profiles/{profile['id']}/appointments", headers=auth()).json()
    assert appointments[0]["status"] == "reviewed"

    rejected = client.post(
        f"/appointments/{appointment['id']}/review",
        headers=auth(),
        json={"stars": 9},
    )
    assert rejected.status_code == 422


PUBLIC_ROUTES = {("GET", "/health")}


def routed_endpoints(app) -> list[tuple[str, str]]:
    """Every method and path the application serves, taken from its OpenAPI schema."""

    endpoints = sorted(
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    )
    declared = sorted(
        (method, route.path)
        for route in router.routes
        if isinstance(route, APIRoute)
        for method in route.methods - {"HEAD", "OPTIONS"}
    )
    # Guard against the enumeration silently going empty or missing a route that is
    # registered but hidden from the schema, which would make the check below vacuous.
    assert endpoints == declared
    return endpoints


def test_health_is_the_only_unauthenticated_endpoint(client):
    endpoints = routed_endpoints(client.app)
    assert PUBLIC_ROUTES <= set(endpoints)
    assert client.get("/health").status_code == 200

    unguarded = []
    for method, path in endpoints:
        if (method, path) in PUBLIC_ROUTES:
            continue
        request_path = re.sub(r"\{[^}]+\}", "placeholder-id", path)
        status_code = client.request(method, request_path).status_code
        if status_code != 401:
            unguarded.append(f"{method} {path} -> {status_code}")

    assert not unguarded, "Endpoints reachable without authentication: " + ", ".join(unguarded)


def test_unauthenticated_request_creates_no_account(client):
    """Account provisioning is a side effect of authentication, so it must not run for anonymous callers."""

    assert client.get("/account").status_code == 401
    assert client.post("/profiles", json={"display_name": "Self"}).status_code == 401

    with next(get_db()) as db:
        assert db.query(models.Account).count() == 0
        assert db.query(models.AuthIdentity).count() == 0

    # The same query must see a row once a credential is supplied, otherwise the
    # assertions above would hold against the wrong database.
    create_profile(client)
    with next(get_db()) as db:
        assert db.query(models.Account).count() == 1
        assert db.query(models.AuthIdentity).count() == 1
