"""Provision a fresh Singapore project; never run this inside the API or worker."""

import argparse
import json
import os
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import Request, build_opener

from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.config import Settings
from app.data_boundary import BOUNDARY_VERSION, READINESS_CHECKS, validate_data_settings
from app.database import normalize_database_url
from app.supabase_storage import NoRedirects

ROOT = Path(__file__).resolve().parents[3]


def project_attestation(project: str, access_token: str) -> dict:
    request = Request(
        f"https://api.supabase.com/v1/projects/{project}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with build_opener(NoRedirects()).open(request, timeout=30) as response:
            evidence = json.load(response)
        if (
            evidence.get("ref", evidence.get("id")) != project
            or evidence["region"] != "ap-southeast-1"
            or evidence["status"] != "ACTIVE_HEALTHY"
            or evidence["database"]["host"] != f"db.{project}.supabase.co"
        ):
            raise ValueError
    except Exception:
        raise RuntimeError(
            "Cannot verify the expected healthy Singapore project through the Management API."
        ) from None
    return {"project_ref": project, "region": evidence["region"]}


def write_private(path: Path, value: str) -> None:
    # Do not overwrite existing credentials or follow a pre-existing symlink.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(value)


def provision(values: dict, output: Path, *, apply: bool, resume: bool = False) -> None:
    project = values.get("SUPABASE_PROJECT_REF", "")
    if not re.fullmatch(r"[a-z]{20}", project):
        raise RuntimeError("Set SUPABASE_PROJECT_REF in the provisioning environment.")
    required = (
        "SUPABASE_ACCESS_TOKEN",
        "MIGRATION_DATABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_STORAGE_JWT_SECRET",
    )
    if any(not values.get(key) for key in required):
        raise RuntimeError(
            "Set the four provisioning credentials listed in infra/supabase/README.md."
        )
    if len(values["SUPABASE_STORAGE_JWT_SECRET"]) < 32:
        raise RuntimeError("Configure the project's accepted HS256 Storage signing secret.")
    admin_url = make_url(normalize_database_url(values["MIGRATION_DATABASE_URL"]))
    suffix = f".{project}" if ".pooler." in (admin_url.host or "") else ""
    if admin_url.username != f"postgres{suffix}":
        raise RuntimeError("Only provisioning uses the project's postgres migration connection.")
    api_url = admin_url.set(username=f"med_app_api{suffix}", password=secrets.token_urlsafe(36))
    cleanup_url = admin_url.set(
        username=f"med_app_cleanup{suffix}", password=secrets.token_urlsafe(36)
    )
    runtime = Settings(  # type: ignore[call-arg]
        _env_file=None,
        data_backend="supabase",
        environment="production",
        dev_auth_enabled=False,
        database_url=api_url.render_as_string(hide_password=False),
        supabase_url=f"https://{project}.supabase.co",
        supabase_project_ref=project,
        supabase_region="ap-southeast-1",
        supabase_anon_key=values["SUPABASE_ANON_KEY"],
        extraction_provider="disabled",
        extraction_run_inline=False,
    )
    validate_data_settings(runtime, require_admission=False)
    if not admin_url.password or "YOUR-" in admin_url.password:
        raise RuntimeError("Replace the migration connection's password placeholder locally.")
    evidence = project_attestation(project, values["SUPABASE_ACCESS_TOKEN"])
    engine = create_engine(
        admin_url, hide_parameters=True, connect_args={"prepare_threshold": None}
    )
    try:
        with engine.connect() as connection:
            tables = inspect(connection).get_table_names(schema="public")
            if resume:
                from app import models  # noqa: F401
                from app.database import Base

                expected = {table.name for table in Base.metadata.sorted_tables}
                if set(tables) != expected | {"alembic_version"}:
                    raise RuntimeError("Resume requires exactly the empty application baseline.")
                if connection.execute(
                    text("SELECT version_num FROM public.alembic_version")
                ).scalars().all() != ["20260721_0001"]:
                    raise RuntimeError(
                        "Resume requires the deployed application baseline revision."
                    )
                for table in Base.metadata.sorted_tables:
                    if connection.execute(table.select().limit(1)).first():
                        raise RuntimeError("Resume refuses existing application data.")
                if connection.execute(
                    text("SELECT 1 FROM med_app_private.configuration LIMIT 1")
                ).first():
                    raise RuntimeError("Resume refuses an already configured deployment.")
                roles = connection.execute(
                    text("SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname LIKE 'med_app_%'")
                ).all()
                if set(roles) != {
                    (name, False)
                    for name in (
                        "med_app_api",
                        "med_app_request",
                        "med_app_storage",
                        "med_app_cleanup",
                    )
                }:
                    raise RuntimeError("Resume requires the original non-login workload roles.")
                boundary = connection.execute(
                    text("SELECT med_app_private.boundary_status()")
                ).scalar_one()
                if not boundary["roles_safe"] or not boundary["rls_enabled"]:
                    raise RuntimeError("Resume requires the restricted database boundary.")
            elif tables:
                raise RuntimeError(
                    "This baseline only provisions an empty public schema; existing data needs a reviewed forward migration."
                )
            if not connection.execute(text("SELECT to_regclass('storage.objects')")).scalar_one():
                raise RuntimeError("The target project's Storage schema is missing.")
            # Reusing a pre-existing privileged or unexpectedly granted role is unsafe.
            existing = connection.execute(
                text("SELECT rolname FROM pg_roles WHERE rolname LIKE 'med_app_%'")
            ).first()
            if existing and not resume:
                raise RuntimeError(
                    "Workload roles already exist. Review the previous provisioning attempt before continuing."
                )
        print("Verified healthy Singapore project, TLS connection, and empty application schema.")
        if not apply:
            print(
                "Plan: apply baseline, private bucket policies, protected signing configuration, and API/cleanup logins. Re-run with --apply to provision."
            )
            return
        output.mkdir(parents=True, mode=0o700, exist_ok=True)
        if any(
            (output / name).exists() for name in ("runtime.env", "cleanup.env", "attestation.json")
        ):
            raise RuntimeError(
                "Choose a new output directory; existing credentials will not be replaced."
            )
        config = Config(str(ROOT / "apps/api/alembic.ini"))
        config.attributes["database_url"] = admin_url.render_as_string(hide_password=False)
        if not resume:
            command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(text((ROOT / "infra/supabase/storage.sql").read_text()))
            connection.execute(
                text("INSERT INTO med_app_private.configuration(key, value) VALUES (:key, :value)"),
                [
                    {"key": "project_ref", "value": project},
                    {"key": "region", "value": evidence["region"]},
                    {"key": "supabase_url", "value": runtime.supabase_url},
                    {"key": "storage_jwt_secret", "value": values["SUPABASE_STORAGE_JWT_SECRET"]},
                ],
            )
            for role, url in (("med_app_api", api_url), ("med_app_cleanup", cleanup_url)):
                # Passwords are parameters, never SQL literals, command arguments, or logs.
                connection.execute(
                    text(
                        "SELECT set_config('med_app.setup_role', :role, true), set_config('med_app.setup_password', :password, true)"
                    ),
                    {"role": role, "password": url.password},
                )
                connection.execute(
                    text("""DO $setup$ BEGIN
                    EXECUTE format('ALTER ROLE %I LOGIN PASSWORD %L', current_setting('med_app.setup_role'), current_setting('med_app.setup_password'));
                END $setup$""")
                )
        evidence.update(
            {
                "database_host": api_url.host,
                "boundary_version": BOUNDARY_VERSION,
                "schema_revision": "20260721_0001",
                "verified_at": datetime.now(UTC).isoformat(),
                "checks": dict.fromkeys(READINESS_CHECKS, "pending"),
            }
        )
        runtime_values = {
            "ENVIRONMENT": "production",
            "DATA_BACKEND": "supabase",
            "DEV_AUTH_ENABLED": "false",
            "DATABASE_URL": runtime.database_url,
            "SUPABASE_URL": runtime.supabase_url,
            "SUPABASE_PROJECT_REF": project,
            "SUPABASE_REGION": "ap-southeast-1",
            "SUPABASE_ANON_KEY": runtime.supabase_anon_key,
            "SUPABASE_STORAGE_BUCKET": "medical-records",
            "EXTRACTION_PROVIDER": "disabled",
            "EXTRACTION_RUN_INLINE": "false",
            "PRODUCTION_DATA_ENABLED": "false",
            "SUPABASE_ATTESTATION_PATH": str((output / "attestation.json").resolve()),
        }
        # JSON quoting is supported by python-dotenv and protects URI delimiters.
        env = "".join(f"{key}={json.dumps(value)}\n" for key, value in runtime_values.items())
        write_private(output / "runtime.env", env)
        cleanup_values = {
            key: value for key, value in runtime_values.items() if key != "DATABASE_URL"
        }
        cleanup_values["SUPABASE_CLEANUP_DATABASE_URL"] = cleanup_url.render_as_string(
            hide_password=False
        )
        write_private(
            output / "cleanup.env",
            "".join(f"{key}={json.dumps(value)}\n" for key, value in cleanup_values.items()),
        )
        write_private(output / "attestation.json", json.dumps(evidence, indent=2) + "\n")
        print(
            "Provisioned. Restricted runtime files were written to the selected directory. Upload admission remains disabled until the documented hosted checks pass."
        )
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".context/supabase/runtime")
    parser.add_argument(
        "--apply", action="store_true", help="apply the reviewed fresh-project setup"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="finish setup only after an empty baseline was applied",
    )
    args = parser.parse_args()
    values = {**dotenv_values(args.env_file), **os.environ}
    try:
        provision(values, args.output_dir, apply=args.apply, resume=args.resume)
    except RuntimeError as exc:
        print(str(exc))
        return 1
    except Exception:
        # Driver/provider exceptions can contain credentials or private statements.
        print(
            "Provisioning failed. Check local credentials, project connectivity, and setup state; no secrets were printed."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
