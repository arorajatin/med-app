import base64
import json
from datetime import UTC, date, datetime, timedelta

import pytest
from document_fixtures import image_bytes, pdf_bytes

from app import models
from app.database import get_db

AUTH = {"Authorization": "Bearer feed-owner"}
OTHER = {"Authorization": "Bearer other-owner"}


def upload(client, *, name="report.pdf", text=b"Lab report", headers=AUTH, camera=False):
    response = client.post(
        "/ingestions/camera" if camera else "/ingestions/direct-file",
        headers=headers,
        files=[("uploads", (name, image_bytes() if camera else pdf_bytes(text)))],
    )
    assert response.status_code == 201, response.text
    return response.json()


def feed(client, **params):
    response = client.get("/feed", headers=AUTH, params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_upload_appears_before_extraction_and_updates_after_assignment(make_client):
    client = make_client(EXTRACTION_RUN_INLINE="false")
    receipt = upload(client)
    item = feed(client)["items"][0]
    assert item["id"] == receipt["ingestion"]["id"]
    assert item["extraction_state"] == "queued"
    assert item["assignment_state"] == "provisional"
    assert item["profile"] is None
    assert item["record_id"] is None
    assert item["completed_at"].endswith("Z")
    job_id = receipt["extraction_job"]["id"]
    assert client.post(f"/extraction/jobs/{job_id}/run", headers=AUTH).status_code == 200
    item = feed(client)["items"][0]
    assert item["extraction_state"] == "ready"
    assert item["assignment_state"] == "needs_assignment"
    assert item["attention_required"] is True
    profile = client.post(
        "/profiles", headers=AUTH, json={"display_name": "Asha", "relationship": "self"}
    ).json()
    assigned = client.post(f"/ingestions/{item['id']}/assignment/{profile['id']}", headers=AUTH)
    assert assigned.status_code == 200
    item = feed(client)["items"][0]
    assert item["profile"]["id"] == profile["id"]
    assert item["record_id"] == assigned.json()["id"]
    assert item["assignment_state"] == "resolved"
    assert feed(client, profile_id=profile["id"])["items"] == [item]


def test_feed_aggregates_profiles_camera_and_unresolved_uploads(client):
    for name, relationship in [("Asha", "self"), ("Ravi", "father")]:
        client.post(
            "/profiles", headers=AUTH, json={"display_name": name, "relationship": relationship}
        )
        upload(client, name=f"{name}.pdf", text=f"Patient: {name}\nLab report".encode())
    camera = upload(client, name="page.png", camera=True)
    upload(client, name="foreign.pdf", headers=OTHER)
    items = feed(client)["items"]
    assert len(items) == 3
    assert {item["profile"]["display_name"] for item in items if item["profile"]} == {
        "Asha",
        "Ravi",
    }
    assert items[0]["id"] == camera["ingestion"]["id"]
    assert items[0]["source_channel"] == "camera"
    assert items[0]["source_label"] == "Camera capture"
    assert items[1]["source_channel"] == "direct_file"
    assert items[1]["source_label"] == "File upload"
    response = client.get("/feed", headers=AUTH)
    for private_field in (
        "account_id",
        "object_key",
        "storage_bucket",
        "authorization_basis",
        "sha256",
    ):
        assert private_field not in response.text


def test_member_view_uses_resolved_assignment_not_upload_hint(make_client):
    client = make_client(EXTRACTION_RUN_INLINE="false")
    profiles = [
        client.post(
            "/profiles", headers=AUTH, json={"display_name": name, "relationship": relationship}
        ).json()
        for name, relationship in (("Asha", "self"), ("Ravi", "father"))
    ]
    receipt = client.post(
        "/ingestions/direct-file",
        headers=AUTH,
        data={"provisional_profile_id": profiles[0]["id"]},
        files=[("uploads", ("Ravi.pdf", pdf_bytes(b"Patient: Ravi\nLab report")))],
    )
    assert receipt.status_code == 201, receipt.text
    assert len(feed(client)["items"]) == 1
    for profile in profiles:
        assert feed(client, profile_id=profile["id"])["items"] == []
    job_id = receipt.json()["extraction_job"]["id"]
    assert client.post(f"/extraction/jobs/{job_id}/run", headers=AUTH).status_code == 200
    assert feed(client, profile_id=profiles[0]["id"])["items"] == []
    items = feed(client, profile_id=profiles[1]["id"])["items"]
    assert [item["id"] for item in items] == [receipt.json()["ingestion"]["id"]]
    assert items[0]["assignment_state"] == "resolved"
    upload(client, name="pending.pdf")
    assert len(feed(client)["items"]) == 2
    assert feed(client, profile_id=profiles[1]["id"])["items"] == items


def test_unavailable_member_views_do_not_reveal_profiles(client):
    foreign = client.post("/profiles", headers=OTHER, json={"display_name": "Foreign"}).json()
    for profile_id in (foreign["id"], "missing"):
        response = client.get("/feed", headers=AUTH, params={"profile_id": profile_id})
        assert response.status_code == 404
        assert response.json() == {"detail": "Profile not found."}


@pytest.mark.parametrize("order", ["upload_date", "report_date"])
def test_member_pagination_is_bound_to_family_view(client, order):
    profiles = [
        client.post(
            "/profiles", headers=AUTH, json={"display_name": name, "relationship": relationship}
        ).json()
        for name, relationship in (("Asha", "self"), ("Ravi", "father"))
    ]
    for index in range(3):
        for name in ("Asha", "Ravi"):
            upload(client, name=f"{name}-{index}.pdf", text=f"Patient: {name}\nLab report".encode())
    profile_id = profiles[0]["id"]
    with next(get_db()) as db:
        for ingestion in db.query(models.Ingestion).all():
            ingestion.completed_at = datetime(2026, 9, 1, tzinfo=UTC)
        for record in db.query(models.MedicalRecord).all():
            if record.display_filename.endswith("0.pdf"):
                record.record_date = date(2026, 8, 1)
        db.commit()
    expected = feed(client, profile_id=profile_id, order=order)["items"]
    assert len(expected) == 3
    assert all(item["profile"]["id"] == profile_id for item in expected)
    page = feed(client, profile_id=profile_id, order=order, limit=1)
    cursor = page["next_cursor"]
    for scope in ({}, {"profile_id": profiles[1]["id"]}):
        assert (
            client.get(
                "/feed", headers=AUTH, params={"cursor": cursor, "order": order, **scope}
            ).status_code
            == 400
        )
    # Even an All Family cursor whose anchor belongs to this member cannot be reused.
    all_cursor = base64.urlsafe_b64encode(
        json.dumps([2, order, None, expected[0]["id"]]).encode()
    ).decode()
    assert (
        client.get(
            "/feed",
            headers=AUTH,
            params={"cursor": all_cursor, "order": order, "profile_id": profile_id},
        ).status_code
        == 400
    )
    actual = page["items"]
    while cursor:
        page = feed(client, profile_id=profile_id, order=order, limit=1, cursor=cursor)
        actual.extend(page["items"])
        cursor = page["next_cursor"]
    assert actual == expected


@pytest.mark.parametrize("state", ["queued", "extracting", "retrying", "failed", "ready"])
def test_all_processing_states_remain_visible(make_client, state):
    client = make_client(EXTRACTION_RUN_INLINE="false")
    upload(client)
    with next(get_db()) as db:
        db.query(models.Ingestion).one().extraction_state = state
        db.commit()
    assert feed(client)["items"][0]["extraction_state"] == state


@pytest.mark.parametrize("excluded", ["receiving", "failed", "missing_completion", "deleted"])
def test_unfinished_or_deleted_uploads_are_excluded(make_client, excluded):
    client = make_client(EXTRACTION_RUN_INLINE="false")
    upload(client)
    with next(get_db()) as db:
        ingestion = db.query(models.Ingestion).one()
        if excluded == "deleted":
            ingestion.tombstoned_at = datetime.now(UTC)
        elif excluded == "missing_completion":
            ingestion.completed_at = None
        else:
            ingestion.upload_state = excluded
        db.commit()
    assert feed(client) == {"items": [], "next_cursor": None}


def test_partial_upload_never_enters_feed(client):
    response = client.post(
        "/ingestions/direct-file",
        headers=AUTH,
        files=[("uploads", ("ok.png", image_bytes())), ("uploads", ("bad.png", b"bad"))],
    )
    assert response.status_code == 415
    assert feed(client)["items"] == []


@pytest.mark.parametrize("order", ["upload_date", "report_date"])
def test_stable_pagination_with_ties_undated_reports_and_new_uploads(make_client, order):
    client = make_client(EXTRACTION_RUN_INLINE="false")
    profile = client.post("/profiles", headers=AUTH, json={"display_name": "Asha"}).json()
    receipts = [upload(client) for _ in range(7)]
    with next(get_db()) as db:
        for index, receipt in enumerate(receipts):
            ingestion = db.get(models.Ingestion, receipt["ingestion"]["id"])
            ingestion.completed_at = datetime(2026, 9, 1, tzinfo=UTC) + timedelta(days=index // 2)
            if index < 4:
                db.add(
                    models.MedicalRecord(
                        account_id=ingestion.account_id,
                        profile_id=profile["id"],
                        ingestion_id=ingestion.id,
                        display_filename=f"Report {index}",
                        record_date=date(2026, 8, 1 + index // 2),
                    )
                )
        db.commit()
    expected = [
        receipt["ingestion"]["id"]
        for index, receipt in sorted(
            enumerate(receipts),
            key=lambda pair: (
                (
                    (pair[0] < 4, pair[0] // 2 if pair[0] < 4 else -1)
                    if order == "report_date"
                    else ()
                )
                + (pair[0] // 2, pair[1]["ingestion"]["id"])
            ),
            reverse=True,
        )
    ]
    assert [item["id"] for item in feed(client, order=order)["items"]] == expected
    first = feed(client, order=order, limit=2)
    upload(client, name="new arrival.pdf")
    actual = [item["id"] for item in first["items"]]
    cursor = first["next_cursor"]
    while cursor:
        page = feed(client, order=order, limit=2, cursor=cursor)
        actual.extend(item["id"] for item in page["items"])
        cursor = page["next_cursor"]
    # Newer uploads cannot shift a cursor as they would an offset.
    # In report-date mode a new undated upload belongs before existing undated items.
    assert [identifier for identifier in actual if identifier in expected] == expected
    assert len(actual) == len(set(actual))
    if order == "report_date":
        dated = {receipt["ingestion"]["id"] for receipt in receipts[:4]}
        assert set(expected[:4]) == dated
    else:
        assert actual == expected


def test_extracted_date_stays_undated_until_review_and_current_name_is_used(client):
    profile = client.post("/profiles", headers=AUTH, json={"display_name": "Asha"}).json()
    receipt = upload(client, text=b"Patient: Asha\nLab report\nDate: 2026-08-15")
    item = feed(client)["items"][0]
    assert item["report_date"] is None
    assert item["metadata_review_pending"] is True
    assert item["review_state"] == "not_required"
    extraction = client.get(f"/ingestions/{item['id']}/extraction", headers=AUTH).json()
    candidate = next(
        c for c in extraction["metadata_candidates"] if c["metadata_type"] == "record_date"
    )
    reviewed = client.patch(
        f"/records/{receipt['record']['id']}/review",
        headers=AUTH,
        json={
            "decisions": [
                {"candidate_type": "metadata", "candidate_id": candidate["id"], "action": "confirm"}
            ]
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    with next(get_db()) as db:
        db.get(models.MedicalRecord, receipt["record"]["id"]).display_filename = "Renamed report"
        db.commit()
    item = feed(client, order="report_date")["items"][0]
    assert item["report_date"] == "2026-08-15"
    assert item["display_filename"] == "Renamed report"
    assert item["profile"]["id"] == profile["id"]


def test_foreign_and_wrong_order_cursors_are_denied(make_client):
    client = make_client(EXTRACTION_RUN_INLINE="false")
    upload(client)
    upload(client)
    cursor = feed(client, limit=1)["next_cursor"]
    assert client.get("/feed", headers=OTHER, params={"cursor": cursor}).status_code == 400
    assert client.get("/feed", headers=OTHER).json()["items"] == []
    assert (
        client.get(
            "/feed", headers=AUTH, params={"cursor": cursor, "order": "report_date"}
        ).status_code
        == 400
    )
    assert client.get("/feed", headers=AUTH, params={"account_id": "other"}).status_code == 422


@pytest.mark.parametrize(
    "cursor",
    [
        "",
        "not-base64",
        "e30=",
        "W10=",
        base64.b64encode(json.dumps([1, "upload_date", "absent"]).encode()).decode(),
        base64.b64encode(json.dumps([2, "upload_date", None, "absent"]).encode()).decode(),
    ],
)
def test_malformed_or_unavailable_cursor_returns_safe_error(client, cursor):
    response = client.get("/feed", headers=AUTH, params={"cursor": cursor})
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Feed cursor. Refresh the Feed."}


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"order": "oldest"}])
def test_invalid_page_parameters_are_rejected(client, params):
    assert client.get("/feed", headers=AUTH, params=params).status_code == 422
