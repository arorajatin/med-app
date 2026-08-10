## 1. Persistence and Regional Infrastructure

- [ ] 1.1 Add immutable authenticated `direct_file`/`camera` logical-document manifest/version, governing account-level consent snapshot, and ordered source-part persistence, plus extraction job generation, numbered attempt, persisted internal phase, claim token/lease, provider callback, active-result, safe-failure, transactional outbox, and cleanup/tombstone state.
- [ ] 1.2 Add a migration that backfills each existing one-file record as a one-part manifest without dispatching duplicate work, and enforce uniqueness for outbox events, continuation events, successful attempt results, and the active job generation.
- [ ] 1.3 Provision customer-KMS-encrypted extraction and Textract-callback SQS Standard queues with four-day retention, 14-day dead-letter queues, an SNS callback topic, Mumbai staging/output buckets with a 24-hour lifecycle, restricted service roles, and aggregate CloudWatch dashboards/alerts, all in `ap-south-1`.
- [ ] 1.4 Add startup validation that fails production closed for any non-Mumbai queue, topic, worker, bucket, key, log group, database, replica/failover target, inline/fake dispatcher, mock provider, or invalid ZDR/provider configuration.

## 2. Durable Dispatch and Phase Execution

- [ ] 2.1 Finalize one immutable logical-document manifest only from an authenticated `direct_file` or `camera` web-upload route with accepted account-level consent before creating one queued job and transactional outbox event; reject other ingress, incomplete or mutated manifests, and dispatch no individual source part or repeated consent prompt.
- [ ] 2.2 Implement the outbox dispatcher with the fixed identifier-only message schema, idempotent publish recording, continuous recovery, a two-minute oldest-undelivered alert, and a runnable-job reconciler that creates a new dispatch generation after 10 minutes without a claim.
- [ ] 2.3 Implement conditional five-minute phase claims, 60-second claim/visibility renewal, state-aware redelivery, post-commit acknowledgement, and recovery that converts an expired synchronous claim into an interrupted retryable attempt.
- [ ] 2.4 Implement the persisted phase engine for inspection, native extraction, ordered image Textract processing, model extraction, normalization, and publication through the shared provider adapter.
- [ ] 2.5 Implement asynchronous PDF Textract submission using an attempt-derived client token, persisted submit intent/provider job mapping, SNS-to-SQS callback validation, claim-free waiting, idempotent continuation, collection, and 30-minute warning/60-minute reconciliation.
- [ ] 2.6 Implement three total automatic attempts with a persisted uniform `[0.8, 1.2]` jitter factor: 24-36 seconds before attempt 2 and 96-144 seconds before attempt 3; classify the specified transient and terminal failures, expose only public `retrying`, keep scheduling/claim/delivery details internal, and prohibit automatic attempt 4.
- [ ] 2.7 Implement explicit terminal retry as a linked successor job generation with a fresh budget while preserving the failed generation and immutable manifest audit.

## 3. Publication, Cancellation, and Cleanup

- [ ] 3.1 Stage raw and normalized output by attempt, validate the complete schema and every source reference, and atomically commit one successful result, active pointer, job status, and source lifecycle.
- [ ] 3.2 Implement conditional successor publication so a complete replacement supersedes the prior active result without duplicate observations, while a failed/cancelled replacement leaves prior successful and reviewed output unchanged.
- [ ] 3.3 Make report deletion synchronously block claims and cancel queued, active, retry-scheduled, and Textract-waiting attempts; make later dispatch/callback deliveries acknowledge without source reads, and leave consent revocation to its separate post-V1 change.
- [ ] 3.4 Add idempotent cleanup that immediately deletes Textract staging/output, deletes successful raw and derived output with the report, retains only a safe failed envelope and delivered outbox/log records for 30 days, and retains a non-PHI replay tombstone for 90 days.
- [ ] 3.5 Keep run-once/manual/callback/reconciliation adapters on the shared services, with an in-memory dispatcher, fake clock, deterministic jitter, and fake provider restricted to local/test environments.

## 4. Verification and Operations

- [ ] 4.1 Test authenticated `direct_file`/`camera` one-PDF, one-image, ordered-image, non-web-ingress, incomplete-part, reordered/mutated-part, accepted-consent-snapshot, no-repeat-prompt, and same-manifest successor cases to prove that one attempt always targets one immutable complete logical document.
- [ ] 4.2 Test outbox outage/recovery, lost/expired-message redispatch after 10 minutes, duplicate dispatch, concurrent claims, lease loss, crash before/after every durable transition, redelivery after success/failure/cancellation, and no duplicate provider publication.
- [ ] 4.3 Test native routing, ordered image Textract, PDF submit interruption/idempotent resubmit, callback success/duplicate/mismatch/lateness/loss, 30-minute warning, 60-minute reconciliation, and cancellation while waiting.
- [ ] 4.4 Test every transient and terminal failure class, exact three-attempt exhaustion, persisted jitter bounds using a fake clock, safe failure codes, explicit successor retry, successful supersession, and failed-replacement preservation.
- [ ] 4.5 Add serializer and log-capture tests proving messages, callbacks, telemetry, traces, exceptions, and dead-letter inspection expose no bytes, text/values, filenames, account-contact/account/profile/patient data, hashes, object paths/URLs, provider bodies, or credentials.
- [ ] 4.6 Test production startup rejection for every non-`ap-south-1` or local/mock dependency, and verify KMS encryption, queue/topic policies, retention, DLQ redrive, 24-hour staging lifecycle, 30-day safe metadata cleanup, report deletion, and 90-day tombstone expiry.
- [ ] 4.7 Add alerts for oldest outbox over two minutes, oldest runnable dispatch over five minutes, any DLQ message, Textract wait over 30 minutes, and at least five-percent failures over 15 minutes with 20 or more attempts.
- [ ] 4.8 Document regional worker deployment, scaling, pause/drain, callback and reconciler operation, DLQ inspection/redrive without PHI, deletion cleanup, outage recovery, and rollback that never enables production inline/mock or cross-region processing.
- [ ] 4.9 Run the backend test suite, migration/RLS checks, infrastructure policy checks, log/payload privacy tests, and `openspec validate add-queue-backed-extraction-worker --strict` plus `openspec validate --all --strict`.
- [ ] 4.10 Complete implementation review and finalize `review.md` with the reviewed commit, executed evidence, findings, dependency state, and exact resume point.
