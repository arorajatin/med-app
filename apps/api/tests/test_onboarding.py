from fastapi.testclient import TestClient

from app import models
from app.database import get_db


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
