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

## Sign-in

Google is the only sign-in method in the first release. With `DEV_AUTH_ENABLED=false` the API
verifies the Supabase access token, then reads the upstream sign-in method from the
provider-controlled `app_metadata` claim and answers 403 for anything but Google, before an account
is created or reconciled. That way an email and password identity created directly with the identity
provider cannot reach private data, even if the provider is configured to offer it.

## API contract

`contracts/openapi.json` is exported from this app and is the source clients generate from.
Regenerate it after changing a route or response model:

```bash
uv run --frozen --package med-app-backend python apps/api/scripts/export_openapi.py
```

`tests/test_api_contract.py` fails while the checked-in document is stale.

## Onboarding

`GET /account/onboarding` reports progress through `self_profile`, `health_context`,
`conditions`, and `medications`, and names the first step still outstanding so a returning account
manager resumes where they stopped. Status is derived from the rows each step leaves behind, so it
cannot drift from the data.

Creating an account authorizes the AI processing required by the product. The API does not store a
separate processing-consent record or repeat that choice on an ingestion or medical record.

`GET /profiles/{id}/health-context` returns the latest reported age and weight with their reported
dates, and marks age due for a non-blocking refresh after one calendar year and weight after six
calendar months. A stale value stays visible and is never re-derived or replaced.

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
