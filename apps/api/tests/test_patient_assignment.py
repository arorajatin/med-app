from dataclasses import replace
from datetime import UTC, datetime

import pytest
from document_fixtures import pdf_bytes

from app import models
from app.ai.mock_provider import MockExtractor
from app.database import get_db
from app.services import extraction as extraction_service
from app.services.patient_matching import MATCH_VERSION, match_patient, normalize_patient_name

AUTH = {"Authorization": "Bearer owner"}


def profile(client, name="Asha Rao", *, user="owner"):
    response = client.post(
        "/profiles",
        headers={"Authorization": f"Bearer {user}"},
        json={"display_name": name, "relationship": "family"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def upload(client, selected, text="Lab report\nPatient: Asha Rao\nHemoglobin 13.2 g/dL", **context):
    response = client.post(
        "/ingestions/direct-file",
        headers=AUTH,
        files={"uploads": ("report.pdf", pdf_bytes(text.encode()), "application/pdf")},
        data={"provisional_profile_id": selected["id"], **context},
    )
    assert response.status_code == 201, response.text
    return response.json()


def details(client, result):
    response = client.get(f"/ingestions/{result['ingestion']['id']}/extraction", headers=AUTH)
    assert response.status_code == 200, response.text
    return response.json()


def assign(client, result, selected):
    return client.post(
        f"/ingestions/{result['ingestion']['id']}/assignment/{selected['id']}", headers=AUTH
    )


@pytest.mark.parametrize(
    "stored,extracted",
    [
        ("Ａｓｈａ Ｒａｏ", "asha rao"),
        (" Asha\u00a0 Rao ", "ASHA   RAO"),
        ("Straße Müller", "STRASSE MU\u0308LLER"),
    ],
)
def test_name_normalization_is_exact_unicode_case_and_whitespace(client, stored, extracted):
    expected = profile(client, stored)
    with next(get_db()) as db:
        owned = db.query(models.Profile).filter_by(id=expected["id"]).one()
        found, candidates = match_patient(db, account_id=owned.account_id, names=[extracted])
        assert found.id == owned.id
        assert candidates == [owned.id]
    assert normalize_patient_name(stored) == normalize_patient_name(extracted)


def test_exact_patient_replaces_provisional_selection_and_publishes_only_to_match(client):
    selected = profile(client, "Ravi Rao")
    patient = profile(client, "Ａｓｈａ Ｒａｏ")
    result = upload(client, selected)
    assert result["extraction_job"]["status"] == "ready"
    assert result["ingestion"]["provisional_profile_id"] == selected["id"]
    assert result["ingestion"]["resolved_profile_id"] == patient["id"]
    assert result["record"]["profile_id"] == patient["id"]
    extracted = details(client, result)
    assert extracted["observations"][0]["profile_id"] == patient["id"]
    assert extracted["observations"][0]["quality_state"] == "unreviewed_extracted"
    audit = extracted["assignment_history"][0]
    assert audit["method"] == "automatic" and audit["match_version"] == MATCH_VERSION
    assert audit["evidence_ids"] == [extracted["patient_evidence"][0]["id"]]
    assert client.get(f"/profiles/{selected['id']}/records", headers=AUTH).json() == []
    assert client.get(f"/profiles/{patient['id']}/memory", headers=AUTH).json()["facts"] == []


def test_explicit_aliases_are_owned_replaceable_and_idempotent(client):
    patient = profile(client, "Asha Sharma")
    path = f"/profiles/{patient['id']}/aliases"
    first = client.put(path, headers=AUTH, json={"aliases": [" Asha Rao "]})
    assert first.status_code == 200 and first.json()[0]["name"] == "Asha Rao"
    assert client.put(path, headers=AUTH, json={"aliases": ["Asha Rao"]}).json() == first.json()
    assert upload(client, patient)["ingestion"]["resolved_profile_id"] == patient["id"]
    assert client.put(path, headers=AUTH, json={"aliases": []}).json() == []
    assert upload(client, patient)["ingestion"]["assignment_state"] == "needs_assignment"
    assert client.get(path, headers={"Authorization": "Bearer foreign"}).status_code == 404
    assert (
        client.put(
            path, headers={"Authorization": "Bearer foreign"}, json={"aliases": []}
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "aliases",
    [
        [" "],
        ["Asha", "ASHA"],
        ["Ａｓｈａ", "Asha"],
        ["bad\nname"],
        ["x" * 161],
        [str(i) for i in range(21)],
    ],
)
def test_invalid_alias_lists_are_rejected_atomically(client, aliases):
    patient = profile(client)
    path = f"/profiles/{patient['id']}/aliases"
    assert client.put(path, headers=AUTH, json={"aliases": aliases}).status_code == 422
    assert client.get(path, headers=AUTH).json() == []


@pytest.mark.parametrize(
    "case",
    [
        "missing",
        "partial",
        "ambiguous",
        "alias_collision",
        "foreign_only",
        "conflicting",
        "unmatched_second",
        "context_only",
        "doctor",
    ],
)
def test_unsafe_matches_remain_staged_without_creating_profiles(client, case):
    selected = profile(client)
    name = "Asha Rao"
    text = f"Lab report\nPatient: {name}\nHemoglobin 13.2 g/dL"
    if case == "missing":
        text = "Lab report\nHemoglobin 13.2 g/dL"
    elif case == "partial":
        text = text.replace(name, "Asha")
    elif case == "ambiguous":
        profile(client)
    elif case == "alias_collision":
        other = profile(client, "Ravi Rao")
        client.put(f"/profiles/{other['id']}/aliases", headers=AUTH, json={"aliases": [name]})
    elif case == "foreign_only":
        selected = profile(client, "Local person")
        profile(client, "Foreign person", user="foreign")
        text = text.replace(name, "Foreign person")
    elif case == "conflicting":
        profile(client, "Ravi Rao")
        text += "\nPatient: Ravi Rao"
    elif case == "unmatched_second":
        text += "\nPatient: Unknown person"
    elif case == "context_only":
        text = "Lab report\nHemoglobin 13.2 g/dL"
    elif case == "doctor":
        text = text.replace("Patient:", "Doctor:")
    with next(get_db()) as db:
        count = db.query(models.Profile).count()
    result = upload(client, selected, text, user_context="Patient: Asha Rao")
    assert result["extraction_job"]["status"] == "ready", result
    assert result["ingestion"]["assignment_state"] == "needs_assignment"
    assert result["record"] is None
    extracted = details(client, result)
    assert all(item["profile_id"] is None for item in extracted["observations"])
    with next(get_db()) as db:
        assert db.query(models.Profile).count() == count
        assert db.query(models.MedicalRecord).count() == 0
        assert db.query(models.MemoryFact).count() == 0


def test_manual_resolution_waits_for_success_and_preserves_source_keys(make_client):
    client = make_client(EXTRACTION_RUN_INLINE="false")
    selected = profile(client)
    result = upload(client, selected, "Prescription\nTablet Metformin 500 mg")
    assert assign(client, result, selected).status_code == 409
    with next(get_db()) as db:
        keys = [part.object_key for part in db.query(models.IngestionPart).all()]
    assert (
        client.post(f"/extraction/jobs/{result['extraction_job']['id']}/run", headers=AUTH).json()[
            "status"
        ]
        == "ready"
    )
    first = assign(client, result, selected)
    assert first.status_code == 200, first.text
    assert assign(client, result, selected).json()["id"] == first.json()["id"]
    assert assign(client, result, profile(client, "Ravi Rao")).status_code == 409
    extracted = details(client, result)
    assert [event["method"] for event in extracted["assignment_history"]] == ["automatic", "manual"]
    assert extracted["memory_candidates"][0]["record_id"] == first.json()["id"]
    with next(get_db()) as db:
        assert [part.object_key for part in db.query(models.IngestionPart).all()] == keys
        assert db.query(models.MemoryFact).count() == 0
        ingestion = db.query(models.Ingestion).one()
        assert ingestion.resolved_by_identity_id == db.query(models.AuthIdentity).one().id
        ingestion.tombstoned_at = datetime.now(UTC)
        db.commit()
    assert assign(client, result, selected).status_code == 409


def test_retry_keeps_assignment_audit_without_duplicate_active_results(client):
    selected = profile(client)
    result = upload(client, selected)
    original = details(client, result)
    response = client.post(f"/extraction/jobs/{result['extraction_job']['id']}/retry", headers=AUTH)
    assert response.json()["status"] == "ready", response.text
    retried = details(client, result)
    assert retried["record"]["id"] == original["record"]["id"]
    assert len(retried["observations"]) == len(retried["patient_evidence"]) == 1
    assert len(retried["assignment_history"]) == 2
    assert retried["assignment_history"][0] == original["assignment_history"][0]
    with next(get_db()) as db:
        assert db.query(models.PatientEvidence).count() == 2
        assert db.query(models.MetricObservation).filter_by(is_active=True).count() == 1
    # Retained superseded evidence is audit history, not something this response cites.
    returned = {
        item["id"]
        for key in ("patient_evidence", "metadata_candidates", "observations", "memory_candidates")
        for item in retried[key]
    }
    assert retried["source_references"]
    for reference in retried["source_references"]:
        owners = [
            reference[key]
            for key in (
                "patient_evidence_id",
                "metadata_candidate_id",
                "metric_observation_id",
                "memory_candidate_id",
            )
            if reference[key] is not None
        ]
        assert owners and set(owners) <= returned


@pytest.mark.parametrize("manual", [False, True])
def test_retry_cannot_silently_change_a_resolved_patient(client, monkeypatch, manual):
    first = profile(client)
    other = profile(client, "Ravi Rao")
    original_extract = MockExtractor.extract_with_layout
    selected_evidence = [0]

    def choose_evidence(self, **kwargs):
        extraction = original_extract(self, **kwargs)
        return replace(
            extraction,
            patient_evidence=[extraction.patient_evidence[index] for index in selected_evidence],
        )

    monkeypatch.setattr(MockExtractor, "extract_with_layout", choose_evidence)
    if manual:
        selected_evidence[:] = [0, 1]
    result = upload(
        client, first, "Lab report\nPatient: Asha Rao\nPatient: Ravi Rao\nHemoglobin 13.2 g/dL"
    )
    if manual:
        assert assign(client, result, first).status_code == 200
    before = details(client, result)
    selected_evidence[:] = [1]
    response = client.post(f"/extraction/jobs/{result['extraction_job']['id']}/retry", headers=AUTH)
    assert response.json()["status"] == ("ready" if manual else "failed"), response.text
    if not manual:
        assert response.json()["failure_code"] == "assignment_conflict"
    after = details(client, result)
    assert after["ingestion"]["resolved_profile_id"] == first["id"]
    assert after["record"]["id"] == before["record"]["id"]
    # The rejected attempt does not withdraw the committed output the document still serves.
    assert after["ingestion"]["extraction_state"] == "ready"
    if not manual:
        assert after["observations"] == before["observations"]
    assert client.get(f"/profiles/{other['id']}/records", headers=AUTH).json() == []


@pytest.mark.parametrize("failure", ["reference", "persistence", "source_changed"])
def test_failed_attempt_preserves_committed_output_and_cleans_new_raw_files(
    client, tmp_path, monkeypatch, failure
):
    selected = profile(client)
    result = upload(client, selected)
    before = details(client, result)
    files = {path for path in (tmp_path / "storage").rglob("*") if path.is_file()}
    if failure == "reference":
        original = MockExtractor.extract_with_layout

        def corrupt_reference(self, **kwargs):
            extraction = original(self, **kwargs)
            observation = extraction.observations[0]
            reference = replace(observation.source_references[0], native_word_ids=["fabricated"])
            return replace(
                extraction, observations=[replace(observation, source_references=[reference])]
            )

        monkeypatch.setattr(MockExtractor, "extract_with_layout", corrupt_reference)
    elif failure == "persistence":
        original_persist = extraction_service._persist_result

        def fail_after_writes(*args, **kwargs):
            original_persist(*args, **kwargs)
            raise RuntimeError("private provider content must not escape")

        monkeypatch.setattr(extraction_service, "_persist_result", fail_after_writes)
    else:
        with next(get_db()) as db:
            part = db.query(models.IngestionPart).one()
            (tmp_path / "storage" / part.object_key).write_bytes(pdf_bytes(b"Different source"))

        def unexpected_provider(*args, **kwargs):
            pytest.fail("changed bytes must not reach the provider")

        monkeypatch.setattr(MockExtractor, "extract_with_layout", unexpected_provider)
    response = client.post(f"/extraction/jobs/{result['extraction_job']['id']}/retry", headers=AUTH)
    assert response.json()["status"] == "failed"
    assert (
        response.json()["failure_code"]
        == {
            "reference": "invalid_source_reference",
            "persistence": "extraction_failed",
            "source_changed": "invalid_document_input",
        }[failure]
    )
    after = details(client, result)
    assert after["observations"] == before["observations"]
    assert after["patient_evidence"] == before["patient_evidence"]
    assert after["assignment_history"] == before["assignment_history"]
    assert {path for path in (tmp_path / "storage").rglob("*") if path.is_file()} == files
    assert "private provider content" not in response.text
