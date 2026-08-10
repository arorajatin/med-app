## Why

Production authentication already verifies Supabase access tokens, but records still use SQLite and local files. The first-release design adds authenticated web-upload provenance, multi-part documents, extraction attempts, and deletion workflows. Sensitive medical data and processing identifiers need one India-resident, defense-in-depth boundary before any of those production paths can be enabled.

## What Changes

- Run production relational persistence on Supabase Postgres in `ap-south-1` (Mumbai) through versioned migrations, and fail closed when the configured project is missing or outside that region.
- Apply account-scoped row-level security to every private row, including web-upload ingestions, source parts, source provenance, extraction attempts and outputs, observations, memory candidates, and deletion state.
- Use transaction-scoped verified identity or trusted-worker context without granting normal request or worker roles an RLS-bypass capability.
- Store report objects in a private Supabase bucket under stable account/ingestion/part keys that never include a profile ID and therefore remain unchanged by assignment or reassignment.
- Issue only short-lived, owner-authorized signed access to private objects; never expose public object URLs or storage credentials.
- Constrain Textract staging/output and its related SNS/SQS resources to encrypted resources in AWS `ap-south-1`, with immediate cleanup and a 24-hour lifecycle backstop.
- Make deletion revoke access immediately, purge private content and extraction data idempotently, retain only the queue worker's bounded non-PHI job/idempotency tombstone where required to prevent delayed work resurrection, and expire safe failure envelopes after 30 days.
- Keep SQLite and filesystem adapters for local development and tests, backed by shared authorization, lifecycle, and storage contract tests.
- Gate production data and extraction paths on migrations, Mumbai-region attestations, RLS tests, key configuration, cleanup controls, and provider privacy checks.

This change does not add sharing, clinician access, public links, direct-to-storage client uploads, email/WhatsApp ingestion, or a general-purpose account-retention policy. V1 web uploads remain supported through authenticated `apps/api` endpoints that validate the request, stamp `direct_file` or `camera`, and write to private Storage on the client's behalf.

## Capabilities

### New Capabilities

- `production-data-boundary`: India-resident production Postgres, private object storage, protected transport metadata, and defense-in-depth account ownership.

### Modified Capabilities

None. Existing user-facing ownership and upload behavior remain compatible; the first-release change adds the new ingestion and download interfaces that use this boundary.

## Impact

Affected areas include database configuration, request and worker sessions, authenticated web-upload storage dependencies, object naming, private download delivery, extraction staging, deletion, migrations, deployment controls, and integration tests.

The archived `database-schema-management` capability supplies the migration mechanism. `define-first-release-family-health-experience` supplies the account, authenticated web-ingestion, provenance, extraction, and deletion schemas; `add-production-extraction-provider` supplies the Textract and Bedrock lifecycle; and `add-queue-backed-extraction-worker` supplies durable job and cleanup processing. Those changes must reuse this boundary rather than introduce profile-bearing object keys, direct-to-storage client writes, service-role request paths, cross-region storage, or parallel retention rules.
