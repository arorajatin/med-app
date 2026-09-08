"""Authorization, validation, and two-account isolation across every account route.

The matrix below is checked against the routes the application actually
registers, so a new endpoint cannot be added without deciding how it behaves for
a caller who does not own the resource.
"""

import re
from datetime import UTC, datetime, timedelta

import pytest
from document_fixtures import pdf_bytes
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app import models
from app.api.routes import router
from app.database import get_db

OWNER = "owner"
INTRUDER = "intruder"
PUBLIC_ROUTES = {("GET", "/health")}

# Routes whose response is scoped to the caller's own account rather than to a
# resource named in the path. They cannot answer 404, so the isolation test
# below checks that they never return another account's data.
# The web-upload routes, checked against another account's profile.
UPLOAD_ROUTES = {
    ("POST", "/ingestions/direct-file"),
    ("POST", "/ingestions/camera"),
}

ACCOUNT_SCOPED_ROUTES = {
    ("GET", "/account"),
    ("GET", "/account/onboarding"),
    ("PUT", "/account/onboarding/self-profile"),
    ("GET", "/profiles"),
    ("POST", "/profiles"),
}


def auth(user_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}"}


@pytest.fixture()
def owner_world(client: TestClient) -> dict[str, str]:
    """One fully populated owner account: profile, document, record, and appointment."""

    profile = client.post(
        "/profiles",
        headers=auth(OWNER),
        json={"display_name": "Asha", "relationship": "self"},
    ).json()
    upload = client.post(
        "/ingestions/direct-file",
        headers=auth(OWNER),
        files={
            "uploads": (
                "report.pdf",
                pdf_bytes(b"Lab report for Asha\nHemoglobin 13.2 g/dL"),
                "application/pdf",
            )
        },
        data={"provisional_profile_id": profile["id"]},
    )
    assert upload.status_code == 201, upload.text
    ingestion = upload.json()["ingestion"]
    job = upload.json()["extraction_job"]
    record = client.post(
        f"/ingestions/{ingestion['id']}/assignment/{profile['id']}",
        headers=auth(OWNER),
    ).json()
    appointment = client.post(
        "/appointments",
        headers=auth(OWNER),
        json={
            "profile_id": profile["id"],
            "scheduled_for": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
        },
    ).json()
    return {
        "profile_id": profile["id"],
        "ingestion_id": ingestion["id"],
        "job_id": job["id"],
        "record_id": record["id"],
        "appointment_id": appointment["id"],
    }


def owned_resource_cases(world: dict[str, str]) -> list[tuple[str, str, str, dict | None]]:
    """Every route that names an owned resource, with a request the owner could make."""

    profile_id = world["profile_id"]
    reported_at = datetime.now(UTC).isoformat()
    return [
        ("GET", "/profiles/{profile_id}", f"/profiles/{profile_id}", None),
        (
            "GET",
            "/profiles/{profile_id}/health-context",
            f"/profiles/{profile_id}/health-context",
            None,
        ),
        (
            "POST",
            "/profiles/{profile_id}/health-context",
            f"/profiles/{profile_id}/health-context",
            {"reported_age": 30, "age_reported_at": reported_at},
        ),
        (
            "PUT",
            "/profiles/{profile_id}/attested-conditions",
            f"/profiles/{profile_id}/attested-conditions",
            {"entries": [{"title": "Asthma"}]},
        ),
        (
            "PUT",
            "/profiles/{profile_id}/attested-medications",
            f"/profiles/{profile_id}/attested-medications",
            {"entries": []},
        ),
        ("GET", "/profiles/{profile_id}/memory", f"/profiles/{profile_id}/memory", None),
        ("GET", "/profiles/{profile_id}/records", f"/profiles/{profile_id}/records", None),
        (
            "GET",
            "/profiles/{profile_id}/appointments",
            f"/profiles/{profile_id}/appointments",
            None,
        ),
        ("GET", "/records/{record_id}", f"/records/{world['record_id']}", None),
        (
            "GET",
            "/records/{record_id}/extraction",
            f"/records/{world['record_id']}/extraction",
            None,
        ),
        (
            "PATCH",
            "/records/{record_id}/review",
            f"/records/{world['record_id']}/review",
            {
                "decisions": [
                    {"candidate_type": "memory", "candidate_id": "any", "action": "confirm"}
                ]
            },
        ),
        (
            "GET",
            "/ingestions/{ingestion_id}/extraction",
            f"/ingestions/{world['ingestion_id']}/extraction",
            None,
        ),
        (
            "POST",
            "/ingestions/{ingestion_id}/assignment/{profile_id}",
            f"/ingestions/{world['ingestion_id']}/assignment/{profile_id}",
            None,
        ),
        ("GET", "/extraction/jobs/{job_id}", f"/extraction/jobs/{world['job_id']}", None),
        (
            "POST",
            "/extraction/jobs/{job_id}/run",
            f"/extraction/jobs/{world['job_id']}/run",
            None,
        ),
        (
            "POST",
            "/extraction/jobs/{job_id}/retry",
            f"/extraction/jobs/{world['job_id']}/retry",
            None,
        ),
        (
            "POST",
            "/appointments",
            "/appointments",
            {"profile_id": profile_id, "scheduled_for": reported_at},
        ),
        (
            "POST",
            "/appointments/{appointment_id}/checklist/generate",
            f"/appointments/{world['appointment_id']}/checklist/generate",
            None,
        ),
        (
            "GET",
            "/appointments/{appointment_id}/checklist",
            f"/appointments/{world['appointment_id']}/checklist",
            None,
        ),
        (
            "POST",
            "/appointments/{appointment_id}/review",
            f"/appointments/{world['appointment_id']}/review",
            {"stars": 5},
        ),
    ]


def protected_routes(app) -> set[tuple[str, str]]:
    """Every served method and path except the public ones, taken from the schema."""

    served = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }
    declared = {
        (method, route.path)
        for route in router.routes
        if isinstance(route, APIRoute)
        for method in (route.methods or set()) - {"HEAD", "OPTIONS"}
    }
    # A route hidden from the schema would make every check below vacuous.
    assert served == declared
    return served - PUBLIC_ROUTES


def test_every_protected_route_has_an_isolation_case(client, owner_world):
    """A new endpoint must decide how it answers a caller who does not own the data."""

    covered = (
        {(method, template) for method, template, _, _ in owned_resource_cases(owner_world)}
        | UPLOAD_ROUTES
        | ACCOUNT_SCOPED_ROUTES
    )

    assert protected_routes(client.app) == covered


def test_owned_resources_are_not_found_for_another_account(client, owner_world):
    """A second account reads another account's resources as though they do not exist."""

    # Give the intruder a real account so the denial is ownership, not a missing account.
    client.post(
        "/profiles",
        headers=auth(INTRUDER),
        json={"display_name": "Ravi", "relationship": "self"},
    )

    denied = []
    for method, template, path, body in owned_resource_cases(owner_world):
        response = client.request(method, path, headers=auth(INTRUDER), json=body)
        if response.status_code != 404:
            denied.append(f"{method} {template} -> {response.status_code}")

    assert not denied, "Routes that did not answer 404 for another account: " + ", ".join(denied)


def test_cross_account_upload_cannot_target_another_accounts_profile(client, owner_world):
    """An upload naming another account's profile is refused and stores nothing."""

    for method, path in sorted(UPLOAD_ROUTES):
        response = client.request(
            method,
            path,
            headers=auth(INTRUDER),
            files={"uploads": ("scan.jpg", b"jpeg-bytes", "image/jpeg")},
            data={"provisional_profile_id": owner_world["profile_id"]},
        )
        assert response.status_code == 404, f"{method} {path} -> {response.text}"

    with next(get_db()) as db:
        owner_account_id = (
            db.query(models.Ingestion)
            .filter(models.Ingestion.id == owner_world["ingestion_id"])
            .one()
            .account_id
        )
        assert (
            db.query(models.Ingestion)
            .filter(models.Ingestion.account_id != owner_account_id)
            .count()
            == 0
        )


def test_upload_provenance_is_route_controlled(client, owner_world):
    """A caller cannot claim a different source channel or owning account."""

    response = client.post(
        "/ingestions/direct-file",
        headers=auth(OWNER),
        files={"uploads": ("report.pdf", pdf_bytes(b"Lab report"), "application/pdf")},
        data={
            "provisional_profile_id": owner_world["profile_id"],
            "source_channel": "email",
            "account_id": "some-other-account",
        },
    )

    assert response.status_code == 422, response.text


def test_account_scoped_routes_return_only_the_callers_own_data(client, owner_world):
    """The routes that cannot answer 404 answer with the caller's own account instead."""

    intruder_profile = client.post(
        "/profiles",
        headers=auth(INTRUDER),
        json={"display_name": "Ravi", "relationship": "self"},
    ).json()

    listed = client.get("/profiles", headers=auth(INTRUDER)).json()
    assert [profile["id"] for profile in listed] == [intruder_profile["id"]]

    onboarding = client.get("/account/onboarding", headers=auth(INTRUDER)).json()
    assert onboarding["self_profile"]["id"] == intruder_profile["id"]

    owner_account = client.get("/account", headers=auth(OWNER)).json()
    intruder_account = client.get("/account", headers=auth(INTRUDER)).json()
    assert owner_account["id"] != intruder_account["id"]

    # Renaming the intruder's own `self` profile leaves the owner's profile alone.
    client.put(
        "/account/onboarding/self-profile",
        headers=auth(INTRUDER),
        json={"display_name": "Ravi Kumar"},
    )
    owner_profile = client.get(f"/profiles/{owner_world['profile_id']}", headers=auth(OWNER)).json()
    assert owner_profile["display_name"] == "Asha"


def test_repeated_activation_reuses_one_account_per_identity(client):
    """Account creation is a side effect of authentication, so it must be idempotent."""

    for _ in range(3):
        assert client.get("/account", headers=auth(OWNER)).status_code == 200
    assert client.get("/account/onboarding", headers=auth(OWNER)).status_code == 200
    assert client.get("/account", headers=auth(INTRUDER)).status_code == 200

    with next(get_db()) as db:
        assert db.query(models.Account).count() == 2
        assert db.query(models.AuthIdentity).count() == 2
        subjects = {identity.provider_subject for identity in db.query(models.AuthIdentity).all()}
        assert subjects == {OWNER, INTRUDER}


def test_unauthenticated_calls_reach_no_protected_route(client, owner_world):
    """Every protected route answers 401 without a credential."""

    unguarded = []
    for method, path in sorted(protected_routes(client.app)):
        request_path = re.sub(r"\{[^}]+\}", "placeholder-id", path)
        status_code = client.request(method, request_path).status_code
        if status_code != 401:
            unguarded.append(f"{method} {path} -> {status_code}")

    assert not unguarded, "Routes reachable without a credential: " + ", ".join(unguarded)


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({}, "no value at all"),
        ({"reported_age": 34}, "age without its reported time"),
        ({"reported_age": -1, "age_reported_at": "2026-07-01T00:00:00Z"}, "age below zero"),
        ({"reported_age": 131, "age_reported_at": "2026-07-01T00:00:00Z"}, "age above 130"),
        ({"reported_age": 34.5, "age_reported_at": "2026-07-01T00:00:00Z"}, "fractional age"),
        ({"entered_weight": "61.5", "weight_unit": "kg"}, "weight without its reported time"),
        (
            {
                "entered_weight": "61.5",
                "weight_unit": "st",
                "weight_reported_at": "2026-07-01T00:00:00Z",
            },
            "an unsupported unit",
        ),
        (
            {
                "entered_weight": "0.49",
                "weight_unit": "kg",
                "weight_reported_at": "2026-07-01T00:00:00Z",
            },
            "weight below 0.5 kg",
        ),
        (
            {
                "entered_weight": "500.01",
                "weight_unit": "kg",
                "weight_reported_at": "2026-07-01T00:00:00Z",
            },
            "weight above 500 kg",
        ),
        (
            {
                "entered_weight": "1",
                "weight_unit": "lb",
                "weight_reported_at": "2026-07-01T00:00:00Z",
            },
            "pounds that normalize below 0.5 kg",
        ),
        (
            {
                "entered_weight": "1200",
                "weight_unit": "lb",
                "weight_reported_at": "2026-07-01T00:00:00Z",
            },
            "pounds that normalize above 500 kg",
        ),
    ],
)
def test_health_context_rejects_invalid_input(client, owner_world, payload, reason):
    response = client.post(
        f"/profiles/{owner_world['profile_id']}/health-context",
        headers=auth(OWNER),
        json=payload,
    )

    assert response.status_code == 422, f"Accepted {reason}: {response.text}"


@pytest.mark.parametrize(
    ("payload", "expected_normalized"),
    [
        ({"reported_age": 0, "age_reported_at": "2026-07-01T00:00:00Z"}, None),
        ({"reported_age": 130, "age_reported_at": "2026-07-01T00:00:00Z"}, None),
        (
            {
                "entered_weight": "0.5",
                "weight_unit": "kg",
                "weight_reported_at": "2026-07-01T00:00:00Z",
            },
            "0.50000000",
        ),
        (
            {
                "entered_weight": "500",
                "weight_unit": "kg",
                "weight_reported_at": "2026-07-01T00:00:00Z",
            },
            "500.00000000",
        ),
    ],
)
def test_health_context_accepts_the_boundary_values(
    client, owner_world, payload, expected_normalized
):
    response = client.post(
        f"/profiles/{owner_world['profile_id']}/health-context",
        headers=auth(OWNER),
        json=payload,
    )

    assert response.status_code == 201, response.text
    if expected_normalized is not None:
        assert response.json()["normalized_weight_kg"] == expected_normalized


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({"display_name": "", "relationship": "self"}, "an empty display name"),
        ({"display_name": "A" * 161, "relationship": "self"}, "an over-long display name"),
        ({"relationship": "self"}, "no display name"),
        ({"display_name": "Ravi", "relationship": ""}, "an empty relationship"),
    ],
)
def test_profile_creation_rejects_invalid_input(client, payload, reason):
    response = client.post("/profiles", headers=auth(OWNER), json=payload)

    assert response.status_code == 422, f"Accepted {reason}: {response.text}"


def test_attested_declarations_reject_an_over_long_list(client, owner_world):
    """The declared set is bounded so one request cannot store an unbounded list."""

    response = client.put(
        f"/profiles/{owner_world['profile_id']}/attested-conditions",
        headers=auth(OWNER),
        json={"entries": [{"title": f"Condition {index}"} for index in range(101)]},
    )

    assert response.status_code == 422
