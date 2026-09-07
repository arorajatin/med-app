"""Accounts and profiles exist only because someone signed in and onboarded.

The first release has no import path: a fresh database starts empty and fills up
through the authenticated onboarding routes alone.
"""

import re

from app import models
from app.database import get_db
from app.worker import run_once

IMPORT_SHAPED_PATH = re.compile(r"import|bulk|migrate|admin|seed", re.IGNORECASE)


def auth(user_id: str = "user_1") -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}"}


def test_a_fresh_database_starts_with_no_account_data(client):
    """Nothing is provisioned ahead of a real sign-in."""

    with next(get_db()) as db:
        assert db.query(models.Account).count() == 0
        assert db.query(models.AuthIdentity).count() == 0
        assert db.query(models.Profile).count() == 0
        assert db.query(models.ProfileHealthContext).count() == 0
        assert db.query(models.MemoryFact).count() == 0


def test_the_worker_creates_no_account_data(client):
    """Background processing never invents an account for work it finds."""

    assert run_once() == 0

    with next(get_db()) as db:
        assert db.query(models.Account).count() == 0
        assert db.query(models.Profile).count() == 0


def test_onboarding_is_the_only_way_account_data_appears(client):
    """One signed-in person produces exactly one account, identity, and self profile."""

    client.put("/account/onboarding/self-profile", headers=auth(), json={"display_name": "Asha"})
    client.post(
        "/profiles",
        headers=auth(),
        json={"display_name": "Ravi", "relationship": "father"},
    )

    with next(get_db()) as db:
        assert db.query(models.Account).count() == 1
        assert db.query(models.AuthIdentity).count() == 1
        profiles = db.query(models.Profile).all()
        assert {profile.relationship for profile in profiles} == {"self", "father"}
        account_id = db.query(models.Account).one().id
        assert all(profile.account_id == account_id for profile in profiles)


def test_the_api_exposes_no_import_or_administrative_path(client):
    """A historical-data import would need a route; there is none to call."""

    import_shaped = [
        path for path in client.app.openapi()["paths"] if IMPORT_SHAPED_PATH.search(path)
    ]

    assert import_shaped == []
