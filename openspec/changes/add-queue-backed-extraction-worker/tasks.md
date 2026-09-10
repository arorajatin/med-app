## 1. Persistence and Regional Infrastructure

- [ ] 1.1 Define models for the authenticated immutable manifest and ordered parts, job generations, numbered attempts/phases, claims, callbacks, active results, safe failures, outbox, and cleanup/tombstone state.
- [ ] 1.2 Persist the 1.1 models in the fresh schema and enforce uniqueness for outbox events, continuations, successful attempt results, and the active job generation.
- [ ] 1.3 Provision the [regional SQS/SNS infrastructure](design.md#use-regional-sqs-queues-with-a-transactional-outbox), KMS keys, staging/output buckets, restricted roles, and CloudWatch dashboards/alerts with the specified [retention policies](design.md#make-cancellation-retention-and-cleanup-idempotent).
- [ ] 1.4 Add production startup validation for every [regional resource](design.md#use-regional-sqs-queues-with-a-transactional-outbox), [local-adapter prohibition](design.md#preserve-a-production-safe-local-path), and provider/ZDR precondition.

## 2. Durable Dispatch and Phase Execution

- [ ] 2.1 Finalize one immutable logical-document manifest only from an authenticated, account-owned `direct_file` or `camera` web-upload route before creating one queued job and transactional outbox event; reject other ingress and incomplete or mutated manifests, and dispatch no individual source part.
- [ ] 2.2 Implement the outbox dispatcher, identifier-only serialization, idempotent delivery recording, and lost-dispatch reconciler under the [durable dispatch contract](specs/document-extraction/spec.md#requirement-keep-durable-orchestration-in-india); wire its alert in 4.7.
- [ ] 2.3 Implement [renewable phase claims](design.md#claim-each-executable-phase-with-a-renewable-lease), state-aware redelivery, post-commit acknowledgement, and interrupted-attempt recovery.
- [ ] 2.4 Implement the persisted phase engine for inspection, native extraction, ordered image Textract processing, model extraction, normalization, and publication through the shared provider adapter.
- [ ] 2.5 Implement asynchronous PDF submission, idempotent resubmission, validated callbacks, claim-free waiting, continuation, collection, and timeout reconciliation under the [resumable phase design](design.md#persist-an-explicit-resumable-phase-machine).
- [ ] 2.6 Implement the [fixed retry policy](design.md#apply-one-exact-automatic-retry-policy), including failure classification, persisted jitter, exhaustion, and separation of public status from internal scheduling.
- [ ] 2.7 Implement explicit terminal retry as a linked successor job generation with a fresh budget while preserving the failed generation and immutable manifest audit.

## 3. Publication, Cancellation, and Cleanup

- [ ] 3.1 Stage raw and normalized output by attempt, validate the complete schema and every source reference, and atomically commit one successful result, active pointer, job status, and source lifecycle.
- [ ] 3.2 Implement conditional successor publication so a complete replacement supersedes the prior active result without duplicate observations, while a failed/cancelled replacement leaves prior successful and reviewed output unchanged.
- [ ] 3.3 Make report deletion synchronously block claims and cancel queued, active, retry-scheduled, and Textract-waiting attempts; make later dispatch/callback deliveries acknowledge without source reads.
- [ ] 3.4 Implement idempotent staging/report cleanup and expiry of safe failure, outbox/log, and replay-tombstone records under the [retention contract](design.md#make-cancellation-retention-and-cleanup-idempotent).
- [ ] 3.5 Keep run-once/manual/callback/reconciliation adapters on the shared services, with an in-memory dispatcher, fake clock, deterministic jitter, and fake provider restricted to local/test environments.

## 4. Verification and Operations

- [ ] 4.1 Test authenticated `direct_file`/`camera` one-PDF, one-image, ordered-image, non-web-ingress, incomplete-part, reordered/mutated-part, account-ownership, and same-manifest successor cases to prove that one attempt always targets one immutable complete logical document.
- [ ] 4.2 Test outbox outage/recovery, lost/expired-message redispatch after 10 minutes, duplicate dispatch, concurrent claims, lease loss, crash before/after every durable transition, redelivery after success/failure/cancellation, and no duplicate provider publication.
- [ ] 4.3 Test native routing, ordered image Textract, PDF submit interruption/idempotent resubmit, callback success/duplicate/mismatch/lateness/loss, 30-minute warning, 60-minute reconciliation, and cancellation while waiting.
- [ ] 4.4 Test every transient and terminal failure class, exact three-attempt exhaustion, persisted jitter bounds using a fake clock, safe failure codes, explicit successor retry, successful supersession, and failed-replacement preservation.
- [ ] 4.5 Add serializer and log-capture tests for every [prohibited data category](design.md#restrict-messages-and-logs-to-non-phi-control-data) across messages, callbacks, telemetry, traces, exceptions, and dead-letter inspection.
- [ ] 4.6 Test every startup rejection in 1.4, KMS encryption, queue/topic policies, DLQ redrive, and every [cleanup and retention deadline](design.md#make-cancellation-retention-and-cleanup-idempotent), including report deletion and tombstone expiry.
- [ ] 4.7 Add alerts for oldest outbox over two minutes, oldest runnable dispatch over five minutes, any DLQ message, Textract wait over 30 minutes, and at least five-percent failures over 15 minutes with 20 or more attempts.
- [ ] 4.8 Document regional worker deployment, scaling, pause/drain, callback and reconciler operation, DLQ inspection/redrive without PHI, deletion cleanup, outage recovery, and rollback that never enables production inline/mock or cross-region processing.
- [ ] 4.9 Run the backend test suite, migration/RLS checks, infrastructure policy checks, log/payload privacy tests, and `openspec validate add-queue-backed-extraction-worker --strict` plus `openspec validate --all --strict`.
- [ ] 4.10 Complete implementation review and finalize `review.md` with the reviewed commit, executed evidence, findings, dependency state, and exact resume point.
