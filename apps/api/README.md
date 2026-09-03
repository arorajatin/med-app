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

## Feature flags

Each V1 slice ships behind its own setting, and every flag defaults to `false` so a deployment
enables only the behavior it has evidence for. Copy the values from [.env.example](../../.env.example)
for local development.

| Setting | Gates |
| --- | --- |
| `FEATURE_WEB_INGESTION_ENABLED` | Direct-file and camera upload, and ingestion assignment |
| `FEATURE_EXTRACTION_ENABLED` | Extraction job dispatch and the extraction job routes |
| `FEATURE_OBSERVATIONS_ENABLED` | Publication of extracted metric observations |
| `FEATURE_FEED_DRIVE_ENABLED` | Feed and Drive, which have no routes yet |
| `FEATURE_CHAT_ENABLED` | Chat, which has no routes yet |

A disabled slice answers `404`. Authentication still runs first, so an anonymous request is rejected
with `401` and never learns which slices a deployment runs.

## Onboarding

`GET /account/onboarding` reports progress through `consent`, `self_profile`, `health_context`,
`conditions`, and `medications`, and names the first step still outstanding so a returning account
manager resumes where they stopped. Status is derived from the rows each step leaves behind, so it
cannot drift from the data.

`PUT /account/onboarding/self-profile` creates the account's one `self` profile or updates the
existing one. `PUT /profiles/{id}/attested-conditions` and `PUT /profiles/{id}/attested-medications`
declare the complete current set; an empty list records that the account manager reported none.
Declared entries become trusted memory facts with `user_attested` provenance.

## Safety defaults

- Uploaded files are never exposed through public URLs.
- AI extraction remains untrusted until reviewed.
- Only confirmed or edited permitted fields enter the current baseline medical memory.
- A condition the account manager typed is trusted; a condition derived from a document is not, and
  stays hidden until literal source validation exists.
- The mock provider is restricted to development and tests by the future production-boundary work.
