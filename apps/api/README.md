# Medical Records API

Python/FastAPI backend for the family health application. It currently implements the baseline
profile, private upload, mock extraction, reviewed-memory, and appointment flows. Proposed V1 work
is tracked under the repository-level `openspec/changes/` directory.

## Contents

```text
app/          API, services, persistence models, local adapters, and worker entrypoint
migrations/   Alembic revisions
tests/        Backend tests
alembic.ini   Migration configuration
pyproject.toml Backend package and tool configuration
```

The existing internal Python package is intentionally unchanged during the monorepo move. Its
capability-level split will be performed separately so filesystem movement and application-boundary
changes can be tested independently.

## Commands

Run these from the repository root:

```bash
uv sync --package med-app-backend --extra dev
uv run --package med-app-backend alembic -c apps/api/alembic.ini upgrade head
uv run --package med-app-backend uvicorn app.main:app --reload
uv run --package med-app-backend --extra dev pytest -c apps/api/pyproject.toml
uv run --package med-app-backend python -m app.worker once
```

API and worker startup verify the current Alembic revision but never create or upgrade runtime
tables. Test-only metadata bootstrapping remains guarded by `ENVIRONMENT=test`.

## Fresh-schema policy

Revision `20260721_0001` is the only schema revision in this release. Create an empty database and
run `alembic upgrade head` before starting the API or worker. Databases created by prototype builds
are outside the supported contract; provision a new database instead of importing or transforming
prototype rows.

## Safety defaults

- Uploaded files are never exposed through public URLs.
- AI extraction remains untrusted until reviewed.
- Only confirmed or edited permitted fields enter the current baseline medical memory.
- The mock provider is restricted to development and tests by the future production-boundary work.
