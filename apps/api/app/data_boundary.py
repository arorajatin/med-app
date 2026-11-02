"""Fail-closed admission checks for the hosted data path."""

import base64
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from sqlalchemy import text
from sqlalchemy.engine import Engine, make_url

from app.config import Settings
from app.database import normalize_database_url

BOUNDARY_VERSION = "20260916_upload_storage_v1"
READINESS_CHECKS = {"rls", "storage", "cleanup", "backup_restore", "encryption"}
ALLOWED_DB_PARAMETERS = {"sslmode", "sslrootcert", "connect_timeout", "application_name"}


def validate_data_settings(
    settings: Settings,
    *,
    require_admission: bool = True,
    database_role: Literal["med_app_api", "med_app_cleanup"] = "med_app_api",
) -> None:
    if settings.data_backend not in {"local", "supabase"}:
        raise RuntimeError("DATA_BACKEND must be local or supabase.")
    if settings.data_backend == "local":
        if settings.environment not in {"local", "test", "ci"}:
            raise RuntimeError("Hosted environments require the Supabase data boundary.")
        return
    if settings.dev_auth_enabled:
        raise RuntimeError("Hosted data requires verified Supabase authentication.")
    if settings.extraction_run_inline or settings.extraction_provider != "disabled":
        raise RuntimeError(
            "Set EXTRACTION_PROVIDER=disabled and EXTRACTION_RUN_INLINE=false for hosted uploads."
        )
    project = settings.supabase_project_ref or ""
    if not re.fullmatch(r"[a-z]{20}", project):
        raise RuntimeError("Set the expected SUPABASE_PROJECT_REF.")
    if settings.supabase_region != "ap-southeast-1":
        raise RuntimeError("Supabase must be provisioned in ap-southeast-1 (Singapore).")
    if settings.supabase_url != f"https://{project}.supabase.co":
        raise RuntimeError("SUPABASE_URL must name the attested project.")
    if settings.supabase_jwks_url not in {
        None,
        f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
    }:
        raise RuntimeError("Use the attested project's authentication signing keys.")
    if settings.supabase_storage_bucket != "medical-records" or not settings.supabase_anon_key:
        raise RuntimeError("Configure the private medical-records bucket and publishable API key.")
    if settings.supabase_anon_key.startswith("sb_secret_"):
        raise RuntimeError("Runtime Storage access must not use a privileged API key.")
    if not settings.supabase_anon_key.startswith("sb_publishable_"):
        try:
            payload = settings.supabase_anon_key.split(".")[1]
            claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
            if claims.get("role") != "anon":
                raise ValueError
        except (ValueError, IndexError, AttributeError):
            raise RuntimeError(
                "Use a publishable or legacy anon API key, not a privileged key."
            ) from None
    database_url = (
        settings.supabase_cleanup_database_url
        if database_role == "med_app_cleanup"
        else settings.database_url
    )
    try:
        url = make_url(normalize_database_url(database_url or ""))
    except Exception:
        raise RuntimeError("Configure a valid Supabase workload database URL.") from None
    direct = url.host == f"db.{project}.supabase.co" and url.username == database_role
    pooled = (
        bool(re.fullmatch(r"aws-\d+-ap-southeast-1\.pooler\.supabase\.com", url.host or ""))
        and url.username == f"{database_role}.{project}"
    )
    if (
        url.drivername != "postgresql+psycopg"
        or not (direct or pooled)
        or url.database != "postgres"
        or not url.password
        or "YOUR-" in url.password
        or url.query.get("sslmode") != "verify-full"
        or set(url.query) - ALLOWED_DB_PARAMETERS
    ):
        raise RuntimeError(
            f"Use the attested Supabase {database_role} connection with sslmode=verify-full."
        )
    if not require_admission:
        return
    if not settings.production_data_enabled or not settings.supabase_attestation_path:
        raise RuntimeError("Hosted data is disabled until the deployment attestation passes.")
    try:
        evidence = json.loads(Path(settings.supabase_attestation_path).read_text())
        verified_at = datetime.fromisoformat(evidence["verified_at"])
        now = datetime.now(UTC)
        valid = (
            evidence["project_ref"] == project
            and evidence["region"] == "ap-southeast-1"
            and evidence["database_host"] == url.host
            and evidence["boundary_version"] == BOUNDARY_VERSION
            and evidence["schema_revision"] == "20260721_0001"
            and now - timedelta(days=7) <= verified_at <= now
            and all(evidence["checks"][check] == "pass" for check in READINESS_CHECKS)
        )
    except (OSError, ValueError, TypeError, KeyError):
        valid = False
    if not valid:
        raise RuntimeError("Supabase deployment attestation is missing, stale, or incomplete.")


def verify_database_boundary(engine: Engine, settings: Settings) -> None:
    if settings.data_backend != "supabase":
        return
    try:
        with engine.connect() as connection:
            status = connection.execute(
                text("SELECT med_app_private.boundary_status()")
            ).scalar_one()
        if not (
            status["login"] == "med_app_api"
            and status["roles_safe"]
            and status["rls_enabled"]
            and status["bucket_private"]
            and status["storage_policies"]
            and status["version"] == BOUNDARY_VERSION
            and status["project_ref"] == settings.supabase_project_ref
            and status["region"] == settings.supabase_region
        ):
            raise ValueError
    except Exception:
        raise RuntimeError(
            "Supabase database, roles, or private Storage policies failed preflight."
        ) from None
