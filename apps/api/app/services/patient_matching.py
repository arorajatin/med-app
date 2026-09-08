"""Exact account-local matching. Model-supplied normalized names are never trusted."""

import unicodedata

from sqlalchemy.orm import Session

from app import models

MATCH_VERSION = "nfkc-casefold-whitespace-v1"


def normalize_patient_name(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def match_patient(
    db: Session, *, account_id: str, names: list[str]
) -> tuple[models.Profile | None, list[str]]:
    profiles = db.query(models.Profile).filter(models.Profile.account_id == account_id).all()
    aliases = (
        db.query(models.ProfileAlias).filter(models.ProfileAlias.account_id == account_id).all()
    )
    names_by_profile = {
        profile.id: {normalize_patient_name(profile.display_name)} for profile in profiles
    }
    for alias in aliases:
        if alias.profile_id in names_by_profile:
            names_by_profile[alias.profile_id].add(normalize_patient_name(alias.name))
    matches = [
        {
            profile_id
            for profile_id, allowed in names_by_profile.items()
            if normalize_patient_name(name) in allowed
        }
        for name in names
    ]
    candidates = set().union(*matches)
    # Conflicting patients, even one unmatched name beside an exact match, need a person.
    if not matches or any(len(match) != 1 for match in matches) or len(candidates) != 1:
        return None, sorted(candidates)
    return next(profile for profile in profiles if profile.id in candidates), sorted(candidates)
