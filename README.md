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

Production relational persistence uses Supabase Postgres with database-enforced ownership. Private
Supabase Storage remains a separate checkpoint; do not enable production uploads until that adapter
is configured.

## Production Supabase Postgres

Use separate database credentials for schema migrations and application traffic. The runtime login
must not be a superuser, own application tables, or have `BYPASSRLS`. Provision it with a generated
secret through an administrative connection:

```sql
CREATE ROLE med_app_api
    WITH LOGIN PASSWORD '<generated-runtime-secret>'
    NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT authenticated TO med_app_api;
```

Apply migrations with the administrative URL, then run the API with the dedicated login:

```bash
ENVIRONMENT=production \
DEV_AUTH_ENABLED=false \
SUPABASE_URL=https://<project-ref>.supabase.co \
DATABASE_URL='postgresql+psycopg://med_app_api:<encoded-password>@<host>:5432/postgres' \
MIGRATION_DATABASE_URL='postgresql+psycopg://postgres:<encoded-password>@<host>:5432/postgres' \
uv run alembic upgrade head

ENVIRONMENT=production \
DEV_AUTH_ENABLED=false \
SUPABASE_URL=https://<project-ref>.supabase.co \
DATABASE_URL='postgresql+psycopg://med_app_api:<encoded-password>@<host>:5432/postgres' \
uv run uvicorn app.main:app
```

Production connections require TLS. Prefer Supabase's direct connection for a persistent backend,
or its session pooler when direct IPv6 connectivity is unavailable. The application fails startup
if the runtime URL is not PostgreSQL, uses a privileged role, cannot assume `authenticated`, cannot
resolve `auth.uid()`, lacks forced RLS, or is behind the checked-in Alembic head.

Each authenticated request binds the verified Supabase user ID to every SQLAlchemy transaction.
Application-level `user_id` filters remain in place; RLS is the defense-in-depth boundary if one is
omitted. The legacy run-once extraction worker is intentionally disabled in production until the
queue-backed worker defines an audited, owner-scoped claim path.

### Disposable Supabase database tests

The repository's local Supabase project runs database-only on port `55322`, avoiding the CLI's
default ports:

```bash
supabase start -x gotrue,realtime,storage-api,imgproxy,kong,inbucket,postgrest,postgres-meta,studio,edge-runtime,logflare,vector,supavisor

SUPABASE_TEST_DATABASE_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:55322/postgres' \
uv run pytest tests/test_supabase_postgres.py -q

supabase stop
```

These tests apply the Alembic schema, create a temporary non-privileged runtime login, verify every
user-owned table's policies, and prove two-user read/insert/update/delete isolation through a reused
connection pool.

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
