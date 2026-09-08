from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app import models
from app.database import get_db
from app.services.health_context import refresh_due


def auth(user_id: str = "user_1") -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}"}


def put_self_profile(client: TestClient, *, user: str = "user_1", name: str = "Asha") -> dict:
    response = client.put(
        "/account/onboarding/self-profile",
        headers=auth(user),
        json={"display_name": name},
    )
    assert response.status_code == 200, response.text
    return response.json()


def record_health_context(client: TestClient, profile_id: str, *, user: str = "user_1") -> None:
    for payload in (
        {"reported_age": 34, "age_reported_at": "2026-07-01T00:00:00Z"},
        {
            "entered_weight": "61.5",
            "weight_unit": "kg",
            "weight_reported_at": "2026-07-01T00:00:00Z",
        },
    ):
        response = client.post(
            f"/profiles/{profile_id}/health-context", headers=auth(user), json=payload
        )
        assert response.status_code == 201, response.text


def declare(
    client: TestClient,
    profile_id: str,
    *,
    category: str,
    titles: list[str],
    user: str = "user_1",
):
    return client.put(
        f"/profiles/{profile_id}/attested-{category}",
        headers=auth(user),
        json={"entries": [{"title": title} for title in titles]},
    )


def onboarding(client: TestClient, *, user: str = "user_1") -> dict:
    response = client.get("/account/onboarding", headers=auth(user))
    assert response.status_code == 200, response.text
    return response.json()


def test_onboarding_starts_at_the_self_profile(client):
    """Account creation authorizes processing, so onboarding starts with the self profile."""

    state = onboarding(client)
    assert state["status"] == "not_started"
    assert state["next_step"] == "self_profile"
    assert state["completed_steps"] == []
    assert state["self_profile"] is None


def test_onboarding_resumes_at_the_first_incomplete_step(client):
    """Each step reports the next outstanding one until onboarding completes."""

    profile = put_self_profile(client)
    assert onboarding(client)["next_step"] == "health_context"

    # Age alone is not enough; onboarding waits for the weight too.
    response = client.post(
        f"/profiles/{profile['id']}/health-context",
        headers=auth(),
        json={"reported_age": 34, "age_reported_at": "2026-07-01T00:00:00Z"},
    )
    assert response.status_code == 201
    assert onboarding(client)["next_step"] == "health_context"

    record_health_context(client, profile["id"])
    assert onboarding(client)["next_step"] == "conditions"

    assert (
        declare(client, profile["id"], category="conditions", titles=["Asthma"]).status_code == 200
    )
    state = onboarding(client)
    assert state["status"] == "in_progress"
    assert state["next_step"] == "medications"

    assert declare(client, profile["id"], category="medications", titles=[]).status_code == 200
    state = onboarding(client)
    assert state["status"] == "completed"
    assert state["next_step"] is None
    assert state["completed_steps"] == [
        "self_profile",
        "health_context",
        "conditions",
        "medications",
    ]
    assert client.get("/account", headers=auth()).json()["onboarding_status"] == "completed"


def test_repeated_onboarding_reuses_the_one_self_profile(client):
    """Resuming onboarding corrects the existing self profile instead of adding another."""

    first = put_self_profile(client, name="Asha")
    second = put_self_profile(client, name="Asha Rao")
    assert second["id"] == first["id"]
    assert second["display_name"] == "Asha Rao"
    assert len(client.get("/profiles", headers=auth()).json()) == 1

    duplicate = client.post(
        "/profiles", headers=auth(), json={"display_name": "Someone", "relationship": "self"}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"] == "This account already has a self profile."

    # Another relationship is still allowed under the same account.
    family = client.post(
        "/profiles", headers=auth(), json={"display_name": "Ravi", "relationship": "father"}
    )
    assert family.status_code == 201


def test_attested_entries_become_trusted_memory(client):
    """Typed conditions and medications are trusted without an extraction review."""

    profile = put_self_profile(client)
    conditions = declare(client, profile["id"], category="conditions", titles=["Asthma"])
    assert conditions.status_code == 200
    body = conditions.json()
    assert body["category"] == "condition"
    assert body["declared_at"] is not None
    assert [fact["title"] for fact in body["facts"]] == ["Asthma"]

    medications = declare(client, profile["id"], category="medications", titles=["Salbutamol"])
    assert medications.status_code == 200

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert {(fact["category"], fact["title"]) for fact in memory["facts"]} == {
        ("condition", "Asthma"),
        ("medication", "Salbutamol"),
    }
    assert {fact["provenance"] for fact in memory["facts"]} == {"user_attested"}

    with next(get_db()) as db:
        stored = db.query(models.MemoryFact).filter(models.MemoryFact.is_active.is_(True)).all()
        assert all(fact.attested_by_identity_id is not None for fact in stored)
        assert all(fact.source_record_id is None for fact in stored)


def test_declaring_no_conditions_records_the_answer(client):
    """An empty list is an answer, not a skipped step."""

    profile = put_self_profile(client)
    response = declare(client, profile["id"], category="conditions", titles=[])

    assert response.status_code == 200
    assert response.json()["facts"] == []
    assert response.json()["declared_at"] is not None
    assert "conditions" in onboarding(client)["completed_steps"]


def test_redeclaring_replaces_the_previous_attested_set(client):
    """The latest declaration is the current truth; earlier facts are superseded."""

    profile = put_self_profile(client)
    declare(client, profile["id"], category="conditions", titles=["Asthma", "Migraine"])
    latest = declare(client, profile["id"], category="conditions", titles=["Migraine"])

    assert [fact["title"] for fact in latest.json()["facts"]] == ["Migraine"]
    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert [fact["title"] for fact in memory["facts"]] == ["Migraine"]

    with next(get_db()) as db:
        superseded = (
            db.query(models.MemoryFact).filter(models.MemoryFact.is_active.is_(False)).all()
        )
        assert {fact.title for fact in superseded} == {"Asthma", "Migraine"}
        assert all(fact.superseded_at is not None for fact in superseded)


def test_attested_memory_rejects_another_accounts_profile(client):
    """One account's declaration cannot touch another account's profile."""

    profile = put_self_profile(client, user="user_1")
    put_self_profile(client, user="user_2", name="Other")

    response = declare(
        client, profile["id"], category="conditions", titles=["Asthma"], user="user_2"
    )

    assert response.status_code == 404
    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert memory["facts"] == []


def test_document_derived_condition_stays_hidden_while_attested_conditions_show(client):
    """Provenance decides: a person may assert a condition, an extractor may not."""

    profile = put_self_profile(client)
    declare(client, profile["id"], category="conditions", titles=["Asthma"])

    with next(get_db()) as db:
        account_id = db.query(models.Account).one().id
        db.add(
            models.MemoryFact(
                account_id=account_id,
                profile_id=profile["id"],
                provenance="reviewed_candidate",
                category="condition",
                title="Chronic kidney disease",
                details={"text": "Chronic kidney disease"},
            )
        )
        db.commit()

    memory = client.get(f"/profiles/{profile['id']}/memory", headers=auth()).json()
    assert [fact["title"] for fact in memory["facts"]] == ["Asthma"]


def report_health_context(client: TestClient, profile_id: str, payload: dict, *, user="user_1"):
    response = client.post(
        f"/profiles/{profile_id}/health-context", headers=auth(user), json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


def days_ago(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


def test_health_context_read_is_empty_before_anything_is_reported(client):
    """A profile with no reported values has nothing to show and nothing to refresh."""

    profile = put_self_profile(client)

    summary = client.get(f"/profiles/{profile['id']}/health-context", headers=auth()).json()

    assert summary["reported_age"] is None
    assert summary["entered_weight"] is None
    assert summary["age_refresh_due"] is False
    assert summary["weight_refresh_due"] is False


def test_health_context_read_returns_the_latest_reported_value_of_each_kind(client):
    """Age and weight can arrive in separate rows, and the newest of each is shown."""

    profile = put_self_profile(client)
    report_health_context(
        client, profile["id"], {"reported_age": 34, "age_reported_at": days_ago(400)}
    )
    report_health_context(
        client, profile["id"], {"reported_age": 35, "age_reported_at": days_ago(10)}
    )
    report_health_context(
        client,
        profile["id"],
        {
            "entered_weight": "150",
            "weight_unit": "lb",
            "weight_reported_at": days_ago(5),
        },
    )

    summary = client.get(f"/profiles/{profile['id']}/health-context", headers=auth()).json()

    assert summary["reported_age"] == 35
    assert summary["age_reported_at"] is not None
    assert summary["entered_weight"] == "150.00000000"
    assert summary["weight_unit"] == "lb"
    # The exact decimal product of the entered value and 0.45359237.
    assert summary["normalized_weight_kg"] == "68.03885550"
    assert summary["age_refresh_due"] is False
    assert summary["weight_refresh_due"] is False


def test_health_context_read_flags_a_stale_value_without_hiding_it(client):
    """Age is due after one calendar year and weight after six calendar months."""

    profile = put_self_profile(client)
    report_health_context(
        client, profile["id"], {"reported_age": 34, "age_reported_at": days_ago(400)}
    )
    report_health_context(
        client,
        profile["id"],
        {"entered_weight": "61.5", "weight_unit": "kg", "weight_reported_at": days_ago(200)},
    )

    summary = client.get(f"/profiles/{profile['id']}/health-context", headers=auth()).json()

    assert summary["reported_age"] == 34
    assert summary["entered_weight"] == "61.50000000"
    assert summary["age_refresh_due"] is True
    assert summary["weight_refresh_due"] is True


def test_health_context_read_rejects_another_accounts_profile(client):
    """The summary is private to the owning account, like the profile itself."""

    profile = put_self_profile(client, user="user_1")
    put_self_profile(client, user="user_2", name="Other")

    response = client.get(f"/profiles/{profile['id']}/health-context", headers=auth("user_2"))

    assert response.status_code == 404


@pytest.mark.parametrize(
    ("reported_at", "months", "now", "expected"),
    [
        # The day the refresh becomes due, and the day before it.
        (datetime(2026, 3, 1, tzinfo=UTC), 12, datetime(2027, 3, 1, tzinfo=UTC), True),
        (datetime(2026, 3, 1, tzinfo=UTC), 12, datetime(2027, 2, 28, tzinfo=UTC), False),
        # A short target month clamps to its last day rather than overflowing.
        (datetime(2026, 8, 31, tzinfo=UTC), 6, datetime(2027, 2, 28, tzinfo=UTC), True),
        (datetime(2026, 8, 31, tzinfo=UTC), 6, datetime(2027, 2, 27, tzinfo=UTC), False),
    ],
)
def test_refresh_due_uses_calendar_months(reported_at, months, now, expected):
    assert refresh_due(reported_at, months=months, now=now) is expected


def test_concurrent_account_creation_reuses_the_winning_identity(client, monkeypatch):
    """A stale initial lookup must not fail a second first-login request."""
    from app.services.accounts import resolve_account_context

    with next(get_db()) as db:
        first = resolve_account_context(db, provider="development", provider_subject="race-user")
        account_id = first.account.id
        original_query = db.query
        missed_identity = original_query(models.AuthIdentity)
        monkeypatch.setattr(missed_identity, "filter", lambda *args: missed_identity)
        monkeypatch.setattr(missed_identity, "one_or_none", lambda: None)
        missed = False

        def query(*entities):
            nonlocal missed
            if entities == (models.AuthIdentity,) and not missed:
                missed = True
                return missed_identity
            return original_query(*entities)

        monkeypatch.setattr(db, "query", query)
        second = resolve_account_context(db, provider="development", provider_subject="race-user")
        assert second.account.id == account_id
        assert original_query(models.Account).count() == 1
        assert original_query(models.AuthIdentity).count() == 1
