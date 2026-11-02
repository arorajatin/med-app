import importlib.util
import json
import stat
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

spec = importlib.util.spec_from_file_location(
    "provision_supabase", Path(__file__).resolve().parents[1] / "scripts/provision_supabase.py"
)
provisioning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provisioning)
PROJECT = "abcdefghijklmnopqrst"


@pytest.mark.parametrize(
    "change",
    [
        {"region": "us-east-1"},
        {"region": "ap-south-1"},
        {"ref": "anotherproject"},
        {"status": "INACTIVE"},
        {"database": {"host": "foreign.supabase.co"}},
    ],
)
def test_provisioning_rejects_unattested_target_before_any_writes(monkeypatch, change):
    evidence = {
        "ref": PROJECT,
        "region": "ap-southeast-1",
        "status": "ACTIVE_HEALTHY",
        "database": {"host": f"db.{PROJECT}.supabase.co"},
    }
    monkeypatch.setattr(
        provisioning,
        "build_opener",
        lambda *args: SimpleNamespace(
            open=lambda *args, **kwargs: BytesIO(json.dumps({**evidence, **change}).encode())
        ),
    )
    with pytest.raises(RuntimeError, match="verify"):
        provisioning.project_attestation(PROJECT, "synthetic-token")


def test_provisioning_files_are_private_and_never_overwrite_existing_credentials(tmp_path):
    target = tmp_path / "runtime.env"
    provisioning.write_private(target, "synthetic-secret")
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        provisioning.write_private(target, "replacement")
    assert target.read_text() == "synthetic-secret"
    link = tmp_path / "symlink.env"
    link.symlink_to(target)
    with pytest.raises(FileExistsError):
        provisioning.write_private(link, "replacement")
    assert target.read_text() == "synthetic-secret"


@pytest.mark.parametrize("pooled", [False, True])
def test_provisioning_separates_api_and_cleanup_credentials(tmp_path, monkeypatch, pooled):
    host = "aws-0-ap-southeast-1.pooler.supabase.com" if pooled else f"db.{PROJECT}.supabase.co"
    suffix = f".{PROJECT}" if pooled else ""
    values = {
        "SUPABASE_PROJECT_REF": PROJECT,
        "SUPABASE_ACCESS_TOKEN": "synthetic-management-token",
        "MIGRATION_DATABASE_URL": (
            f"postgresql://postgres{suffix}:synthetic-admin-password@{host}"
            "/postgres?sslmode=verify-full"
        ),
        "SUPABASE_ANON_KEY": "sb_publishable_synthetic",
        "SUPABASE_STORAGE_JWT_SECRET": "synthetic-signing-secret-at-least-32-characters",
    }
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one.return_value = True
    connection.execute.return_value.first.return_value = None
    monkeypatch.setattr(provisioning, "create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        provisioning, "inspect", lambda connection: SimpleNamespace(get_table_names=lambda **kw: [])
    )
    monkeypatch.setattr(provisioning.command, "upgrade", lambda *args: None)
    monkeypatch.setattr(
        provisioning,
        "project_attestation",
        lambda *args: {"project_ref": PROJECT, "region": "ap-southeast-1"},
    )

    provisioning.provision(values, tmp_path, apply=True)

    runtime = dotenv_values(tmp_path / "runtime.env")
    cleanup = dotenv_values(tmp_path / "cleanup.env")
    runtime_text = (tmp_path / "runtime.env").read_text()
    cleanup_text = (tmp_path / "cleanup.env").read_text()
    assert "DATABASE_URL" not in cleanup
    assert "SUPABASE_CLEANUP_DATABASE_URL" not in runtime
    api_url = make_url(runtime["DATABASE_URL"])
    cleanup_url = make_url(cleanup["SUPABASE_CLEANUP_DATABASE_URL"])
    assert api_url.username == f"med_app_api{suffix}"
    assert cleanup_url.username == f"med_app_cleanup{suffix}"
    assert api_url.password not in cleanup_text
    assert cleanup_url.password not in runtime_text
    for key in ("SUPABASE_ACCESS_TOKEN", "MIGRATION_DATABASE_URL", "SUPABASE_STORAGE_JWT_SECRET"):
        assert values[key] not in runtime_text + cleanup_text


@pytest.mark.parametrize(
    "unsafe", ["tables", "revision", "rows", "configured", "roles", "boundary", None]
)
def test_resume_only_finishes_an_empty_unconfigured_baseline(tmp_path, monkeypatch, unsafe):
    from app import models  # noqa: F401
    from app.database import Base

    values = {
        "SUPABASE_PROJECT_REF": PROJECT,
        "SUPABASE_ACCESS_TOKEN": "synthetic-management-token",
        "MIGRATION_DATABASE_URL": (
            f"postgresql://postgres:synthetic-password@db.{PROJECT}.supabase.co"
            "/postgres?sslmode=verify-full"
        ),
        "SUPABASE_ANON_KEY": "sb_publishable_synthetic",
        "SUPABASE_STORAGE_JWT_SECRET": "synthetic-signing-secret-at-least-32-characters",
    }
    engine = MagicMock()
    connection = engine.connect.return_value.__enter__.return_value
    tables = [table.name for table in Base.metadata.sorted_tables] + ["alembic_version"]
    monkeypatch.setattr(provisioning, "create_engine", lambda *args, **kwargs: engine)
    monkeypatch.setattr(
        provisioning,
        "inspect",
        lambda connection: SimpleNamespace(
            get_table_names=lambda **kwargs: tables + (["unexpected"] if unsafe == "tables" else [])
        ),
    )
    monkeypatch.setattr(
        provisioning,
        "project_attestation",
        lambda *args: {"project_ref": PROJECT, "region": "ap-southeast-1"},
    )
    migrate = MagicMock()
    monkeypatch.setattr(provisioning.command, "upgrade", migrate)

    def execute(statement, *args, **kwargs):
        sql = str(statement)
        result = MagicMock()
        result.first.return_value = None
        result.scalar_one.return_value = True
        if "SELECT version_num" in sql:
            result.scalars.return_value.all.return_value = [
                "wrong" if unsafe == "revision" else "20260721_0001"
            ]
        elif "SELECT rolname, rolcanlogin" in sql:
            result.all.return_value = [
                (role, unsafe == "roles")
                for role in ("med_app_api", "med_app_request", "med_app_storage", "med_app_cleanup")
            ]
        elif "boundary_status()" in sql:
            result.scalar_one.return_value = {
                "roles_safe": unsafe != "boundary",
                "rls_enabled": True,
            }
        elif "med_app_private.configuration" in sql:
            result.first.return_value = (1,) if unsafe == "configured" else None
        elif "LIMIT" in sql and unsafe == "rows":
            result.first.return_value = ("existing private row",)
        return result

    connection.execute.side_effect = execute
    if unsafe:
        with pytest.raises(RuntimeError, match="Resume"):
            provisioning.provision(values, tmp_path, apply=True, resume=True)
        engine.begin.assert_not_called()
        assert not (tmp_path / "runtime.env").exists()
    else:
        provisioning.provision(values, tmp_path, apply=True, resume=True)
        assert (tmp_path / "runtime.env").exists()
    migrate.assert_not_called()
