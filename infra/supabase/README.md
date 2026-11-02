# Supabase upload and storage

The hosted path stores application rows in Supabase Postgres and source files in
the private `medical-records` bucket. The browser uploads through the API. A saved
upload appears immediately in All Family as `queued`. Family member views require
a resolved patient assignment; the upload's suggested member is not that assignment.
Production extraction and report deletion are still separate, unfinished milestones.

The selected target is verified in Singapore, and the Storage signing secret is
accepted. Provisioning is blocked on the database password in the protected
`.context/supabase/provision.env`. Use synthetic fixtures for the first hosted
checks. Local tests do not constitute hosted readiness evidence.

## Provision a fresh Singapore project

The sole Alembic baseline is still undeployed. This setup refuses an existing
application schema or existing workload roles. Do not drop data, stamp an old schema
as current, or downgrade a populated project to make it pass. Once deployed, freeze
this baseline and use forward migrations.

1. Choose a disposable project first, then the intended target, both in `ap-southeast-1`.
   Configure Google sign-in and an RS256/ES256 Auth signing key, as the API verifies
   Supabase user tokens through JWKS. Allow the local web origin in Auth redirect URLs.
2. Copy `infra/supabase/provision.env.example` to `.context/supabase/provision.env`,
   protect it with `chmod 600`, and fill the values locally. Do not paste credentials
   into chat or commit them. `SUPABASE_ACCESS_TOKEN` needs Management API project-read
   access. The migration URI needs the project's administrator credentials with
   `sslmode=verify-full`. Use the matching CA via `sslrootcert` if required; never
   disable certificate verification. The session pooler is supported with the
   `postgres.<project-ref>` username when direct IPv6 connectivity is unavailable.
3. Set `SUPABASE_STORAGE_JWT_SECRET` to an HS256 secret accepted by that project
   (the legacy JWT secret, while it remains accepted). This must coexist with the
   asymmetric Auth signing key. If legacy HS256 verification is disabled, stop:
   provisioning a different signing mechanism requires a reviewed change. Do not
   substitute a service-role key. Test acceptance on the disposable project.
4. Run the read-only setup check, review its result, then apply:

   ```bash
   uv run --frozen --package med-app-backend python apps/api/scripts/provision_supabase.py --env-file .context/supabase/provision.env
   uv run --frozen --package med-app-backend python apps/api/scripts/provision_supabase.py --env-file .context/supabase/provision.env --apply
   ```

The command verifies project/region through the Management API, applies the baseline
and `storage.sql`, stores the signing secret in the protected `med_app_private`
schema, and creates independent API and cleanup logins. It writes `runtime.env`,
`cleanup.env`, and an incomplete `attestation.json` with mode `0600` under
`.context/supabase/runtime`. It does **not** enable uploads or mark checks as passed.
If interrupted after migration, inspect the partial setup through the administrator
connection. If only the empty baseline exists, run the same command with `--resume`
for a read-only check, then `--resume --apply` to finish setup. Resume refuses data,
configured secrets, login-enabled workload roles, unexpected tables or revisions,
and existing output credentials. Never rerun the baseline over a populated project.

The API uses only `med_app_api`, switching to `med_app_request` with verified
transaction-local claims. Cleanup uses `med_app_cleanup` and persisted opaque work
IDs. Its `cleanup.env` contains only the cleanup database credential and shared
settings; do not mount `runtime.env` or pass API credentials to the cleanup process.
The cleanup command does not read the application's local `.env` file.
Storage requests use a single-object `med_app_storage` JWT that lasts at most
60 seconds. These roles cannot bypass RLS or read the signing secret. Administrator
and management credentials belong only in provisioning or audited incident recovery,
never the API, extraction worker, frontend, or routine cleanup environment.

## Verify before opening hosted uploads

`PRODUCTION_DATA_ENABLED` defaults to false. Admission requires a current schema,
expected roles/policies/private bucket, and an attestation for the exact project and
database host, verified within seven days. Keep evidence in restricted deployment
records; do not commit tokens, private object keys, filenames, or signed URLs.

Complete and record all checks in `attestation.json` before changing them to `pass`:

- `rls`: two verified accounts cannot read, create, change, or delete each other's
  rows, including private children and after pool reuse. Workload roles cannot read
  configuration or switch to privileged roles.
- `storage`: API-mediated PDF/JPEG/PNG uploads preserve size/hash and survive an API
  restart. Normal browser tokens cannot list, write, replace, delete, read, or sign
  this bucket directly. Verify private reads and signed-link expiry against the
  deployed Storage service. An upload never returns success after a failed remote
  write or verification. Check Feed state and account isolation.
- `cleanup`: simulate a failed metadata save and a failed Storage delete. Run the
  reconciler, prove retry/idempotency, and verify that a committed source is kept.
  Monitor due intents and alert when the oldest is more than two hours overdue.
- `backup_restore`: record an actual restore drill for protected DB rows **and source
  objects**, including grants, policies, configuration, object counts and checksums.
  A database backup alone is insufficient evidence for file recovery.
- `encryption`: record the project's region and provider encryption/key controls,
  TLS verification, restricted backups, signing-key acceptance/rotation procedure,
  and access to the protected signing configuration.

Refresh the Management API region proof before updating `verified_at`. The file is
an operator attestation, not an automatic test result. Do not treat these upload
checks as approval for the unfinished report-deletion/retention and extraction
release gates in `adopt-supabase-data-boundary`.

Once the upload checks pass, set `PRODUCTION_DATA_ENABLED=true` in `runtime.env` and
run the local UI against hosted data:

```bash
uv run --frozen --package med-app-backend python scripts/dev.py --hosted-data --env-file .context/supabase/runtime/runtime.env
```

This command forces verified auth and disables extraction, preflights the hosted
database, and does not migrate it. A fully hosted web/API deployment still needs a
chosen host and HTTPS routing; no hosting provider is configured in this repository.
The default `scripts/dev.py` command continues to use workspace-local data.

## Cleanup and rollback

Schedule the following every five minutes in an independent process, using the
generated cleanup environment and a read-only mount of the attestation:

```bash
uv run --frozen --package med-app-backend --env-file .context/supabase/runtime/cleanup.env python -m app.storage_cleanup
```

A committed intent precedes every remote write. The upload atomically removes its
intent when metadata commits. After one hour an abandoned intent can be claimed;
the claim prevents a stalled upload from later reporting success. Failed deletion
retries after five minutes. Claims derive the bucket, account and exact key from
the stored work ID. The cleanup role cannot query private report rows.

For rollback, stop new API requests and set `PRODUCTION_DATA_ENABLED=false`; keep
cleanup scheduled. Deploy a compatible application version against the same Singapore
DB/Storage. Never switch to SQLite, local disk, another region or a privileged login,
and never run `alembic downgrade` on private production data. Retain queued jobs for
the future worker. This reconciler handles abandoned uploads only; it is not the
unfinished report-deletion or retention service.

For a suspected credential exposure, disable admission, revoke the affected login,
rotate credentials through the provisioning/incident identity, preserve protected
audit evidence, test the new boundary, and reattest before reopening. Signing-key
rotation must be coordinated between Supabase verification and protected DB
configuration; existing short-lived tokens/links must expire before retiring a key.

## Local verification

`test_postgres_boundary.py` creates and destroys its own database on a disposable
loopback PostgreSQL server and uses actual non-bypass connections. It refuses hosted
addresses. It tests all current private tables, Storage RLS (including an unrelated
broad policy), pool reuse, ownership foreign keys, cleanup IDs, and API upload/Feed
transactions. The regular adapter suite covers provider failures and checksum checks.

```bash
uv run --frozen --package med-app-backend pytest apps/api/tests/test_supabase_storage.py apps/api/tests/test_data_boundary.py
BOUNDARY_TEST_ADMIN_URL='<disposable-loopback-admin-uri>' uv run --frozen --package med-app-backend pytest apps/api/tests/test_postgres_boundary.py
```

References: [Storage RLS](https://supabase.com/docs/guides/storage/security/access-control),
[Storage custom roles](https://supabase.com/docs/guides/storage/schema/custom-roles),
[JWT signing keys](https://supabase.com/docs/guides/auth/signing-keys),
[project attestation API](https://supabase.com/docs/reference/api/v1-get-project),
[database connections](https://supabase.com/docs/guides/database/connecting-to-postgres).
