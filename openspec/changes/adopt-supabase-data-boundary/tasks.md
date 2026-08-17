## 1. Mumbai Production Boundary and Migrations

- [ ] 1.1 Provision disposable and target Supabase projects in `ap-south-1` with private Storage buckets, non-bypass workload roles, and recorded project/region attestations.
- [ ] 1.2 Add fail-closed production configuration checks that reject a missing, unverifiable, or non-Mumbai project and prohibit SQLite, filesystem, alternate-project, and alternate-region fallback.
- [ ] 1.3 Add reviewed forward migrations for account ownership, authenticated web-ingestion/source/provenance rows, extraction storage, object metadata, deletion jobs, failure envelopes, retention indexes, grants, and RLS policies.
- [ ] 1.4 Assign stable account/ingestion/part identifiers when each source is created and verify byte count and checksum before accepting its object reference.
- [ ] 1.5 Test fresh bootstrap, current-head startup, and feature-disable rollback with representative newly created private rows and objects; prove rollback preserves the Mumbai boundary, RLS, queue-owned idempotency state, and deletion work.

## 2. Request and Worker Row-Level Security

- [ ] 2.1 Implement request-scoped SQLAlchemy transactions that set verified transaction-local JWT claims and an authenticated RLS role before queries and clear identity before connection-pool reuse.
- [ ] 2.2 Add task-specific non-`BYPASSRLS` extraction and cleanup roles plus locked-down security-definer context functions that derive account ownership only from opaque persisted work IDs.
- [ ] 2.3 Apply account policies and constrained ownership foreign keys to every private account, profile, record, web-ingestion, source, extraction, observation, memory, conversation/citation, deletion, failure, and object-metadata table.
- [ ] 2.4 Remove service-role/database-owner credentials from normal API and worker paths and document their migration/provisioning and audited break-glass scope.
- [ ] 2.5 Add direct two-account read, insert, update, delete, forged-worker-ID, missing-context, and pooled-connection identity-switch tests for every policy family.

## 3. Stable Private Supabase Storage

- [ ] 3.1 Generalize the private-storage interface around opaque bucket/object references, idempotent deletion, stable `accounts/{account_id}/ingestions/{ingestion_id}/parts/{part_id}/{object_id}` source keys, and stable account/ingestion/attempt raw-output keys.
- [ ] 3.2 Provision non-public bucket and object policies that deny cross-account reads, signing, replacement, and deletion and never expose a public URL.
- [ ] 3.3 Implement backend-issued, owner-authorized, single-object signed reads with a maximum 60-second lifetime and log/trace/analytics/queue redaction.
- [ ] 3.4 Store filenames and file properties as protected relational metadata, and prove patient assignment/reassignment never copies, renames, or changes object keys.
- [ ] 3.5 Add shared local/Supabase adapter tests for key shape, server-mediated writes, signed access, metadata-write cleanup, cross-account denial, reassignment stability, and production fail-closed behavior.

## 4. API-Mediated Upload and Processing Boundaries

- [ ] 4.1 Keep V1 upload writes behind authenticated `apps/api` routes that map ownership, validate MIME/limits/completeness, stamp `direct_file` or `camera`, assign opaque keys, and write to private Storage on behalf of `apps/web`.
- [ ] 4.2 Add Storage policies and tests that deny normal clients direct bucket listing, arbitrary key choice, create/replace/delete, or signing operations while preserving API-mediated web uploads.
- [ ] 4.3 Add safe source projections and redaction tests so Feed/detail APIs expose only route-stamped channel and approved metadata while credentials, authorization details, internal object keys, provider request identifiers, and raw extraction output never leak.
- [ ] 4.4 Provision separate customer-KMS-encrypted Textract input/output, SNS, and SQS resources in AWS `ap-south-1`, with block-public-access, TLS, least-privilege policies, non-PHI queue payloads, and 24-hour S3 lifecycle backstops.
- [ ] 4.5 Implement immediate idempotent Textract staging deletion after rejection or durable persistence, plus orphan reconciliation, alerts, and tests proving transient objects never become the durable report copy.

## 5. Deletion and Retention

- [ ] 5.1 Make report deletion atomically revoke reads and new signed access, cancel dispatchable work, and persist an idempotent cleanup job before returning success.
- [ ] 5.2 Implement retryable cleanup for Supabase source objects, protected report metadata, raw/normalized extraction output, observations, report-derived memory, and known AWS transient objects.
- [ ] 5.3 Retain safe terminal upload/extraction failure envelopes for 30 days, defer the queue worker's bounded non-PHI job/idempotency tombstone to its own contract, and purge each record through indexed scheduled work.
- [ ] 5.4 Add deletion tests for immediate Feed/detail/download denial, partial provider failure, repeated cleanup, extraction supersession, cross-account attempts, delayed queue delivery during the job-idempotency window, and expiry without content resurrection.

## 6. Feature Gates and Rollout

- [ ] 6.1 Add an independent base data-boundary flag gated on current migrations, Mumbai Supabase attestation, RLS/storage suites, encryption keys, backup/restore evidence, and deletion reconciliation.
- [ ] 6.2 Gate production extraction additionally on Mumbai staging/queue controls, provider privacy approval, and Bedrock zero-data-retention eligibility, with no mock, cross-region, direct-to-storage, privileged, or alternate-provider fallback.
- [ ] 6.3 Document secrets, role grants, provisioning, backup/restore, migration, rollback, retention, cleanup reconciliation, incident response, and evidence required to enable each flag.
- [ ] 6.4 Run the backend, API-mediated upload, direct-to-storage denial, migration, shared storage/lifecycle, disposable Supabase, disposable AWS, RLS, deletion, and feature-gate suites plus strict OpenSpec validation.
- [ ] 6.5 Complete implementation review and finalize `review.md` with the reviewed commit, commands, evidence, findings, and exact resume state.
