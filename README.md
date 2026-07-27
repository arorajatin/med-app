# Medical Records Backend

Python/FastAPI backend for the medical records MVP. The first build focuses on:

- family profiles
- private record/file storage
- upload-to-extraction jobs
- review/confirmation of AI output
- living memory built only from confirmed facts
- appointment checklist generation from confirmed history

## Specifications And Roadmap

This repository uses [OpenSpec](openspec/README.md) as the source of truth for product behavior and planned changes:

- `openspec/specs/` describes capabilities implemented today.
- `openspec/changes/` contains proposed future work with specs, designs, and task checklists.
- `openspec/changes/archive/` preserves completed change history and architectural rationale.
- `openspec/config.yaml` supplies project context and safety rules to planning agents.

Repository-local Codex workflow skills are generated under `.codex/skills/`. OpenSpec's CLI requires Node.js 20.19 or newer:

```bash
npm install -g @fission-ai/openspec@latest
openspec list
openspec validate --all --strict
```

Review a change's `proposal.md`, delta specs, `design.md`, and `tasks.md` before implementation. Archive it only after its tasks are complete and its delta specs have been merged into the living specs.

## Local Setup

```bash
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Local development defaults to SQLite, local private file storage, a dev auth header, and a mock AI extraction provider.
Application and worker startup verify the Alembic revision but never create or upgrade tables.

Use either header for local auth:

```http
Authorization: Bearer user_123
X-User-Id: user_123
```

For production auth, set `DEV_AUTH_ENABLED=false` and `SUPABASE_URL=https://<project-ref>.supabase.co`. The backend will verify Supabase access tokens from:

```http
Authorization: Bearer <supabase-access-token>
```

This first Supabase checkpoint only adds JWT verification. Supabase Postgres, private Storage, and RLS policy setup are separate follow-up checkpoints.

## Database Migrations

Alembic migrations are the authoritative schema mechanism for local and production databases.
Run migrations explicitly before starting either the API or worker:

```bash
uv run alembic upgrade head
uv run alembic current
```

Deployment must apply `upgrade head` before starting code that depends on the new schema. The
service fails fast when the database is unversioned or behind the checked-in head. Tests may use
the guarded metadata bootstrap by setting `ENVIRONMENT=test`; runtime environments cannot.

Only downgrade a revision after confirming that its checked-in `downgrade()` is reversible and
that a current backup exists:

```bash
uv run alembic downgrade -1
uv run alembic current
```

### Existing Local SQLite Databases

For disposable local data, use the safest path: stop the API and worker, preserve the old file,
and migrate a fresh database.

```bash
mv med_app.db med_app.pre-alembic.db
DATABASE_URL=sqlite:///./med_app.db uv run alembic upgrade head
```

Do not stamp an unknown, shared, or production database. To preserve known local data, stop all
writers and validate a copy before stamping the original:

```bash
cp med_app.db med_app.schema-check.db
DATABASE_URL=sqlite:///./med_app.schema-check.db uv run alembic stamp head
DATABASE_URL=sqlite:///./med_app.schema-check.db uv run alembic check
cp med_app.db med_app.pre-alembic.db
DATABASE_URL=sqlite:///./med_app.db uv run alembic stamp head
DATABASE_URL=sqlite:///./med_app.db uv run alembic current
```

Proceed only when `alembic check` reports no new upgrade operations. If it reports drift, keep the
backup and recreate or migrate the data deliberately; do not stamp the original.

## Important Safety Defaults

- Uploaded files are never exposed through public URLs.
- AI extraction is assistive and untrusted until reviewed.
- Only confirmed fields are written to the living medical memory.
- The mock provider exists for development and tests; production providers must implement the same internal extraction contract.

## Useful Commands

```bash
uv run pytest
uv run alembic check
uv run python -m app.worker once
```
