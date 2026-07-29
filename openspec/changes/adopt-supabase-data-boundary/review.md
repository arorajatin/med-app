# Review Checkpoint

Status: In progress
Updated: 2026-07-29
Reviewer: Codex
Baseline commit: 91315b1e7ca56818d9f0c985884a632f9622f06a (implementation working tree)

## Reviewed Scope

- Implemented and self-checked production database tasks 1.1 through 1.5.
- Checked production configuration, SQLAlchemy transaction identity binding, application startup
  role validation, worker fail-closed behavior, and the PostgreSQL-only RLS migration.
- Checked forced RLS and owner policies for all nine user-owned tables against direct, unfiltered
  SQLAlchemy access with two isolated users.
- Private object storage and rollout tasks have not started.

## Resume From

- Begin an independent implementation review at `app/database.py`, focusing on the `after_begin`
  identity hook and production startup role checks.
- Then review migration `20260729_0002`, the Supabase integration tests, and the documented runtime
  role provisioning before starting task 2.1.

## Tests Run

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-07-29 | `uv run pytest -q` | Pass | 18 passed, 4 Supabase tests skipped before the disposable stack was supplied. |
| 2026-07-29 | `SUPABASE_TEST_DATABASE_URL=<local-test-url> uv run pytest tests/test_supabase_postgres.py -q` | Pass | 5 role, policy, startup, isolation, and missing-claim tests passed. |
| 2026-07-29 | `SUPABASE_TEST_DATABASE_URL=<local-test-url> uv run pytest -q` | Pass | 27 tests passed, including the live Supabase integration suite. |
| 2026-07-29 | `DATABASE_URL=<local-test-url> uv run alembic downgrade 20260721_0001` | Pass | RLS revision downgraded cleanly. |
| 2026-07-29 | `DATABASE_URL=<local-test-url> uv run alembic upgrade head` | Pass | RLS revision reapplied cleanly. |
| 2026-07-29 | `DATABASE_URL=<local-test-url> uv run alembic check` | Pass | No new upgrade operations detected. |
| 2026-07-29 | `npx --yes @fission-ai/openspec@1.6.0 validate adopt-supabase-data-boundary --strict` | Pass | Change artifacts are valid. |
| 2026-07-29 | `uvx ruff check <changed-python-files> --ignore B008,SIM117` | Pass | Changed Python files passed; FastAPI dependency defaults and one pre-existing nested context rule were excluded. |
| 2026-07-29 | `uv run python -m compileall -q app migrations tests` | Pass | Application, migrations, and tests compile. |
| 2026-07-29 | `git diff --check` | Pass | No whitespace errors. |

## Open Findings

- Medium, design follow-up: several child identifiers are not ownership-aware foreign keys. The
  owner policy prevents cross-user row access and owner spoofing, while the API retains parent
  ownership checks; composite owner constraints or parent-aware policies should be evaluated before
  any direct client database writes are introduced. Owner: future schema-hardening change.
- Accepted scope constraint: the unscoped run-once extraction worker is disabled in production.
  The queue-backed extraction change owns the audited cross-owner claim design.

## Session History

- 2026-07-29: Implemented tasks 1.1 through 1.5 on top of `91315b1`. Provisioned a
  database-only local Supabase stack, applied and reversed the RLS migration, and verified
  non-privileged request roles plus two-user CRUD isolation. Formal implementation review and the
  remaining storage/rollout tasks are pending.
