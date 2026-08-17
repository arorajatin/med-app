## Context

The current service verifies Supabase JWTs but uses a process-wide SQLAlchemy session factory and `LocalPrivateStorage`. Application queries filter by `user_id`, which is necessary but does not protect against a missed filter or direct database access. The first-release plan adds account-owned authenticated web-upload, provenance, extraction, and deletion records plus transient AWS OCR objects. All of those paths need a single production boundary with an explicit India-residency and lifecycle contract.

## Goals / Non-Goals

**Goals:**

- Use Supabase Postgres and private Storage in `ap-south-1` (Mumbai) for all application-controlled production medical data.
- Enforce account ownership at both application and data layers for user requests and background work.
- Keep storage keys stable across patient assignment and reassignment.
- Protect authenticated web-upload ownership, workload credentials, provider identifiers, and signed object access.
- Bound AWS extraction staging to encrypted Mumbai resources with deterministic cleanup.
- Fail closed and retain the existing local developer experience.

**Non-Goals:**

- Add user-to-user sharing, clinician access, public links, or direct-to-storage client uploads that bypass the authenticated API.
- Add email, WhatsApp, or another external-connector ingestion path.
- Replace Supabase Auth token verification.
- Define retention for unrelated account data or backups beyond the ingestion, extraction, failure, and replay records covered here.

## Decisions

### Pin production data services to Mumbai

The production Supabase project and every private Storage bucket used by the application must be provisioned in `ap-south-1` (Mumbai). Deployment configuration records the expected project reference and region; startup and deployment preflight fail closed if either is missing, mismatched, or unverifiable. Production must not fall back to SQLite, local files, a different Supabase project, or another region.

Textract input/output, SNS topics, and SQS queues also reside in AWS `ap-south-1`. S3 buckets block public access, require TLS, use customer-managed KMS keys, and reject access outside named workload roles. SNS/SQS encryption uses customer-managed keys, and messages contain only opaque internal IDs and object references—never document bytes, extracted text, account contact data, or patient data.

### Build on versioned migrations

The archived `database-schema-management` capability makes Alembic the authoritative production schema mechanism. Supabase tables, ownership columns, foreign keys, RLS enablement, policies, grants, encrypted-value metadata, tombstones, and retention indexes are delivered through reviewed migrations rather than dashboard-only changes. Forward and rollback tests must prove that private data is neither exposed nor silently redirected to local adapters.

### Establish identity in every database transaction

Authenticated API sessions use a non-privileged database login. At transaction start the service validates the Supabase JWT, sets transaction-local `request.jwt.claims` containing the verified subject and authenticated role, and then sets the corresponding RLS-subject role before any application query. Policies resolve that subject to its owned account. The connection is returned to the pool only after transaction end, which clears the local claims.

Extraction and cleanup workers use separate least-privilege roles that do not have `BYPASSRLS`. A worker first loads an opaque ingestion, attempt, or cleanup identifier through a narrowly scoped security-definer context function. That function derives the owning account from persisted state, sets a transaction-local worker account context, and cannot accept a caller-supplied account ID. Worker policies require that context and restrict each role to its task-specific tables and operations.

Supabase service-role credentials and database-owner connections are prohibited from normal API and worker paths. They are limited to migrations, provisioning, and explicitly audited break-glass administration.

### Apply RLS to the complete account graph

Application ownership checks and not-found behavior remain mandatory. RLS adds defense in depth to accounts, profiles, records, web-upload ingestion aggregates and parts, source provenance, extraction jobs/attempts/raw outputs, extracted fields, observations, memory candidates, conversations/citations, deletion jobs, failure envelopes, and any private object metadata.

Rows reached through a report or ingestion inherit account ownership through enforced foreign keys; denormalized `account_id` columns are constrained against their parent rather than trusted independently. Direct SQL, RPC functions, and storage policies must all preserve the same account boundary. No user-facing query may select workload credentials, internal authorization details, provider request identifiers, or raw extraction output.

### Use stable ingestion-based object keys

Supabase report objects use opaque keys shaped as:

`accounts/{account_id}/ingestions/{ingestion_id}/parts/{part_id}/{object_id}`

The key contains no profile ID, account contact data, original filename, document issuer, or other clinical/display text. Assignment and reassignment update relational links only and never copy or rename the object. Object metadata retains detected MIME type, byte count, checksum, and part ordinal in protected rows; the original filename remains protected relational metadata rather than part of the key.

Retained raw extraction objects use the same stable account/ingestion boundary with an attempt-specific suffix:

`accounts/{account_id}/ingestions/{ingestion_id}/attempts/{attempt_id}/{object_id}`

Retry and supersession create new attempt identifiers without changing source-part keys.

The database stores only the bucket and opaque object key. All production buckets remain private. After an application ownership check, the backend may issue a single-object signed read URL valid for at most 60 seconds. Signed URLs are bearer secrets: they are never persisted, returned in list/feed payloads, or written to logs, traces, analytics, or queue messages. Uploads remain API-mediated: `apps/web` sends file or camera data to an authenticated `apps/api` route; the backend validates ownership, MIME type, product limits, and upload completeness, stamps `direct_file` or `camera`, and writes the object through its workload role. The client never chooses an object key or receives Storage write credentials.

### Keep web uploads behind the authenticated API

The V1 client never writes directly to a Supabase Storage endpoint. `apps/api` maps the verified Supabase subject to the owning account, validates the staged logical document, assigns opaque account/ingestion/part identifiers, and performs the private object write. Storage policies deny normal client roles the ability to list buckets or create, replace, sign, or delete arbitrary objects. This keeps route-stamped provenance, validation, and account ownership under one server-enforced contract while still allowing users to upload through `apps/web`.

### Separate durable storage from transient AWS processing

Textract input and customer-controlled output use dedicated staging prefixes or buckets separate from durable Supabase report storage. Workers delete Textract input and output immediately after the successful result is durably persisted or an attempt ends terminally. Every transient bucket also has a 24-hour lifecycle expiration as a backstop, and reconciliation alerts on objects that survive their expected cleanup window. No transient object may be used as the durable report copy.

Successful native/Textract and Bedrock raw output is encrypted in the application-controlled private boundary and retained only until its report is deleted. Routine API and support roles cannot read it; audited operational access requires a dedicated role. Bedrock dispatch remains separately gated on Mumbai in-region inference and zero-data-retention eligibility.

### Make deletion immediate at the authorization boundary

Report deletion synchronously marks the report unavailable, revokes new signed access, cancels dispatchable work, and records an idempotent cleanup job in the same database transaction. Cleanup removes source objects, transient AWS objects, raw and normalized extraction output, extracted fields, observations, report-derived memory, and other report derivatives. Repeated cleanup is safe, and failures remain retryable without restoring read access.

After purge, the queue worker may retain only its bounded non-PHI job/idempotency tombstone needed to prevent a delayed dispatch from recreating deleted work; it contains no clinical values, account contact data, filenames, content hashes, or object keys. Safe upload or extraction failure envelopes contain only enumerated status/failure codes, route channel, timestamps, and opaque internal IDs and expire after 30 days.

### Gate rollout by capability

Production persistence/private storage and production extraction use independent feature flags. The base data flag cannot enable until migrations are current, the Supabase region/project attestation passes, RLS and storage isolation tests pass, encryption keys are configured, and backup/restore and deletion reconciliation are verified. Extraction additionally requires Mumbai staging/queues, provider privacy approval, and Bedrock zero-data-retention eligibility. A failed preflight disables the affected capability rather than routing to a local, mock, cross-region, direct-to-storage, or privileged fallback.

## Risks / Trade-offs

- Incorrect transaction claims could deny valid traffic or leak pooled identity -> use transaction-local claims, force rollback/commit before pool return, and test identity switching on reused connections.
- Worker context functions are security-sensitive -> accept only opaque persisted work IDs, derive account ownership internally, lock `search_path`, restrict execution grants, and test forged identifiers.
- Storage and database writes are not one transaction -> record an outbox cleanup action, delete on metadata failure, and reconcile orphaned objects.
- Signed URLs are temporary bearer credentials -> keep their lifetime at 60 seconds, scope them to one object, and prohibit persistence or logging.
- Direct-to-storage client writes would bypass route provenance and server validation -> deny client Storage writes and keep V1 upload writes behind authenticated `apps/api` routes.
- Cross-service deletion can partially fail -> revoke synchronously, make cleanup idempotent, and alert until durable and transient copies are purged.
- Local and production adapters can drift -> run shared storage/lifecycle contracts plus disposable Supabase and AWS integration suites.

## Migration Plan

1. Provision disposable and production Supabase projects in Mumbai plus private buckets, non-bypass roles, KMS keys, and Mumbai Textract staging resources.
2. Apply reviewed forward migrations for account ownership, web-ingestion/provenance tables, RLS policies, stable object metadata, deletion jobs, and retention indexes.
3. Create every source with account and ingestion identifiers; write files to stable keys and verify byte counts and checksums before storing references.
4. Exercise two-account request and worker access, authenticated API-mediated uploads, signed reads, forward/rollback migrations, provider staging, and deletion reconciliation in non-production.
5. Enable the base data boundary, then extraction after its additional gates pass.
6. Enable each capability only after its schema, isolation, storage, and deletion gates pass.

Rollback disables new entry points and provider dispatch but preserves the Mumbai Supabase data boundary and continues deletion cleanup. Once production data exists in Supabase, rollback must not return to SQLite/local files, relax RLS, reuse profile-bearing keys, or restore purged content.

## Resolved Questions

- Direct SQLAlchemy sessions use transaction-local verified claims and an RLS-subject role; workers use task-specific non-bypass roles and account context derived from opaque persisted work IDs.
- Owned downloads use backend-issued, single-object signed URLs valid for at most 60 seconds.
- Successful raw extraction output lives until report deletion; safe failure envelopes live 30 days; the queue worker owns any bounded non-PHI job/idempotency tombstone; AWS transient objects are deleted immediately with a 24-hour lifecycle backstop.
