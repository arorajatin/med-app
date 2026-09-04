## Context

The current data model persists extraction jobs, but upload can still run extraction inline and the run-once worker polls without an exclusive claim. The first-release report model now finalizes one logical document from one PDF, one image, or an ordered image set only through authenticated `direct_file` or `camera` web-upload routes. The selected production pipeline inspects a PDF for usable native text, otherwise uses Amazon Textract, then sends source-linked text and layout to Amazon Bedrock. PDF Textract analysis is asynchronous, so a durable worker must pause and resume an attempt across a provider callback without treating each source part or callback as a new job.

Production data residency is India-only. Queue delivery, callbacks, worker compute, temporary provider objects, encryption keys, logs, and metrics therefore have to remain in AWS `ap-south-1` alongside the Mumbai Supabase data boundary.

## Goals / Non-Goals

**Goals:**

- Dispatch one finalized logical document and its ordered source parts as one immutable extraction input.
- Provide durable dispatch, exclusive phase claims, asynchronous Textract continuation, bounded retries, recovery, and atomic publication.
- Make duplicate dispatch, callback, and acknowledgement delivery harmless.
- Keep all production orchestration resources in `ap-south-1` and all control-plane payloads and logs free of PHI.
- Preserve deterministic local and test execution through the same state machine.

**Non-Goals:**

- Redefine the native-text quality gate, Textract analysis configuration, Bedrock schema, normalized clinical classes, patient-matching rules, or review behavior owned by the provider and first-release changes.
- Add email, WhatsApp, or another external-connector intake path; user-facing priority; arbitrary cancellation; post-creation processing controls; or page-parallel extraction.
- Promise exactly-once queue or provider delivery; the system guarantees at-most-one active published result set through database idempotency.
- Provide cross-region production failover or production fallback to inline/mock processing.

## Decisions

### Snapshot one immutable logical document per attempt

Authenticated web-upload finalization creates a logical-document manifest containing the logical document identifier, immutable `direct_file` or `camera` provenance, manifest version and digest, and each source part's opaque identifier, ordinal, detected MIME type, byte count, and SHA-256. The manifest is immutable after upload completion. Every attempt references one manifest version and processes all parts in ordinal order; the queue never dispatches an individual page or source part.

An input change creates a new logical document rather than mutating or retrying the old manifest. A document has at most one active extraction job generation. Automatic attempts remain within that generation. An explicit retry after terminal failure or an intentional re-extraction creates a successor generation linked by `supersedes_job_id` and snapshots the same immutable manifest unless a new document was uploaded.

### Use regional SQS queues with a transactional outbox

Production uses these encrypted `ap-south-1` resources:

- an Amazon SQS Standard extraction-dispatch queue and dead-letter queue;
- an Amazon SNS Textract completion topic feeding a dedicated SQS callback queue and dead-letter queue;
- Mumbai worker compute, CloudWatch logs/metrics, KMS keys, and Textract staging/output buckets; and
- the Mumbai Supabase Postgres database as the job, attempt, claim, and outbox source of truth.

The upload transaction creates the queued job and outbox event only after the authenticated, account-owned logical document is complete. A dispatcher publishes due, undelivered outbox events and records the resulting message identifier. Queue publication is at-least-once; an outbox uniqueness key prevents one state transition from creating multiple logical events even when physical messages are duplicated. A runnable-job reconciler creates a new dispatch generation when a due, unclaimed phase has no delivery newer than 10 minutes, so an expired or lost physical message cannot strand the database job.

Startup validates every configured AWS resource ARN and provider region as `ap-south-1`. A mismatch disables production dispatch before any document is read. No cross-region queue, topic, worker, bucket, key, log group, replica, or failover target is allowed.

### Restrict messages and logs to non-PHI control data

An application-created queue message has only `schema_version`, `event_type`, opaque `job_id`, `attempt_id`, `outbox_event_id`, and `correlation_id`. A Textract callback additionally supplies its opaque provider job identifier, API, and terminal status. The callback consumer allowlists those fields and never logs the original SNS body.

Messages and logs never contain file bytes, extracted or normalized text, raw provider output, filenames, account contact data, account/profile/patient identifiers, logical-document metadata, object paths, document hashes, presigned URLs, provider error bodies, or credentials. Workers use the opaque attempt identifier to load authorized ownership, manifest, private object references, and state from the database. Metrics use enumerated phase, safe error class, provider, method, duration, and counts only.

SQS, SNS, and their dead-letter queues use customer-managed KMS encryption and policies limited to the regional dispatcher, worker, Textract service role, and callback subscription. The Textract role may publish only to the configured callback topic; the callback queue accepts only that topic.

### Persist an explicit resumable phase machine

The public job lifecycle is `queued`, `extracting`, `retrying`, `ready`, `failed`, `cancelled`, or `superseded`. Internal scheduling fields such as `retry_scheduled`, `next_attempt_at`, jitter, claim state, and queue delivery are worker implementation details and are not part of the client contract. Each numbered attempt records these ordered internal phases:

1. `queued` then `inspecting` validates authenticated ownership and the immutable manifest and selects the provider-owned processing method.
2. A native PDF uses `native_extracting`. A JPEG/PNG source or ordered image set uses `textract_extracting` in source-part order.
3. A PDF routed to OCR uses `textract_submitting`, then `textract_waiting` without an active worker claim. The `StartDocumentAnalysis` request uses a client token derived from the attempt identity, an opaque job tag, the regional completion topic, and customer-controlled regional output storage.
4. A successful callback or reconciliation event conditionally advances the same attempt to `textract_collecting`; duplicate, late, or mismatched callbacks are acknowledged without changing state.
5. Both processing branches converge on `model_extracting`, `normalizing`, and `publishing`, followed by `succeeded`.
6. Any active phase may finish as `retryable_failed`, `terminal_failed`, or `cancelled`.

The Textract submit intent is committed before the provider call. If the worker stops between submission and persistence of the returned provider job identifier, resubmitting with the same client token resolves to the same Textract job. No worker holds or heartbeats a database claim while an attempt is in `textract_waiting`.

Textract publishes to SNS, SNS durably delivers to the callback SQS queue, and the callback consumer creates a unique continuation outbox event keyed by attempt and provider job. A reconciler examines attempts still waiting after 60 minutes, checks the stored provider job once, and creates the same continuation if complete; an unavailable or still-in-progress job becomes a retryable provider timeout. Waiting attempts emit a warning metric after 30 minutes.

### Claim each executable phase with a renewable lease

A consumer conditionally claims only a runnable, due, non-terminal attempt whose source has not been deleted and remains owned by the job's account. The database returns a unique claim token. The claim lease and SQS visibility timeout are five minutes and renew every 60 seconds while synchronous work continues. Every phase transition, provider-submission record, and result commit compares the attempt identity and current claim token.

Losing the claim makes the current worker ineligible to commit. Expired synchronous claims are marked as an interrupted retryable failure and consume the current numbered attempt. Redelivery after a committed phase loads the database state and either resumes the next phase or acknowledges a terminal state. A worker acknowledges its SQS delivery only after the applicable transition, continuation event, retry schedule, or terminal result commits.

### Apply one exact automatic retry policy

Each job generation has three total numbered attempts, including the initial attempt. After attempt 1 fails transiently, attempt 2 is scheduled with a nominal 30-second delay; after attempt 2 fails transiently, attempt 3 uses a nominal two-minute delay. Each nominal delay is multiplied once by a uniformly sampled factor in `[0.8, 1.2]` and persisted, yielding 24-36 seconds and 96-144 seconds respectively. There is no automatic attempt 4.

Retryable failures are provider/network timeouts, throttling, HTTP 429, provider or AWS 5xx/unavailability, transient S3/SQS/SNS/KMS transport errors, an interrupted claim, a retryable Textract failure, or the 60-minute Textract callback timeout. Authentication, authorization/access denial, missing keys, invalid roles, and other configuration or policy failures are terminal and never retry automatically.

Terminal failures are unsupported, corrupt, encrypted, oversized, or over-part-limit input; region, ZDR, authentication, authorization, credential, key, role, policy, or provider configuration failure; invalid extraction schema; unresolved/fabricated source references; and any deterministic normalization error. Report deletion cancels work instead of recording a provider failure. Exhausting attempt 3 produces terminal `retry_exhausted` while retaining the last safe retry class. Client APIs expose only the public `retrying` state and stable safe failure codes, never internal scheduling fields, exception messages, or provider bodies.

An account-manager or authorized operator action after a terminal failure creates a new linked job generation with a fresh three-attempt budget. It never resets attempt counters or destroys the failed audit history in place.

### Publish and supersede result sets atomically

An attempt writes native/Textract output, Bedrock output, normalized items, and source-reference validation into an attempt-scoped staging result. `publishing` commits the complete result set, job/source lifecycle, and active-result pointer in one database transaction. A uniqueness constraint permits one successful result set per attempt, and a conditional active pointer permits only the current job generation to publish.

Duplicate delivery after success acknowledges without invoking a provider or republishing fields. A successful successor generation atomically activates its result and marks the prior result set superseded according to the first-release observation/review rules. A failed or cancelled successor leaves the prior successful result active and unchanged. The worker never deletes reviewed output as a precondition for retry.

### Make cancellation, retention, and cleanup idempotent

Report deletion synchronously prevents new claims and marks queued, active, retry-scheduled, or waiting attempts `cancelled`. Later dispatches and callbacks acknowledge against that state without fetching source data or publishing output. An idempotent cleanup outbox event removes regional staging/output objects, successful raw native/Textract and Bedrock output, normalized derivatives, and private source objects according to the report-deletion contract.

Textract input/output staging objects are deleted immediately after durable result persistence or any attempt failure/cancellation, with a 24-hour bucket lifecycle as a backstop. Successful encrypted raw extraction output remains in restricted primary storage until report deletion. Failed attempts retain only their safe, non-PHI status envelope for 30 days. Delivered outbox control rows and privacy-safe logs are retained for 30 days; extraction and callback queues retain messages for four days and their dead-letter queues for 14 days. A non-PHI job/idempotency tombstone remains for 90 days after report deletion so delayed delivery cannot resurrect work.

### Preserve a production-safe local path

The queue consumer, callback consumer, reconciliation command, manual API action, and run-once command call the same claim, transition, retry, and publication services. Local and test environments may substitute an in-memory synchronous dispatcher, fake clock, deterministic jitter source, and fake provider. Production configuration rejects the fake dispatcher, inline execution, mock provider, and non-Mumbai resources.

### Operate from measurable safety signals

Alert when the oldest undelivered outbox row exceeds two minutes, the oldest runnable dispatch exceeds five minutes, any message reaches a dead-letter queue, a Textract wait exceeds 30 minutes, or the 15-minute extraction failure rate exceeds five percent with at least 20 attempts. Dashboards report only aggregate phase counts, queue/outbox age, retries, lease recoveries, callback delay, safe failure class, and duration. Operations documentation covers worker pause, drain, replay, DLQ redrive, regional dependency failure, deletion cleanup, and rollback without inspecting document content.

## Risks / Trade-offs

- SQS, SNS, outbox, and callback infrastructure add operational complexity -> use one regional queue per event class, fixed state transitions, aggregate alerts, and a deterministic local adapter.
- At-least-once delivery can repeat provider calls after interruption -> use conditional claims, Textract client tokens, attempt-scoped results, and conditional publication; accept that an interrupted non-idempotent model call may incur duplicate cost but cannot publish twice.
- A short lease can expire during valid work -> heartbeat every minute and split the asynchronous Textract wait from claimed synchronous phases.
- Strict India-only configuration reduces failover options -> fail closed and recover within Mumbai instead of silently moving medical data to another region.
- Retaining successful raw output until report deletion increases stored PHI -> encrypt it separately, deny routine application access, audit operational access, and delete it through the report cleanup workflow.

## Migration Plan

1. Add immutable manifest/version, job-generation, attempt/phase, claim, active-result, callback, outbox, and safe-failure persistence. Every new upload creates its ordered manifest directly.
2. Provision the regional encrypted dispatch/callback queues, dead-letter queues, SNS topic, KMS keys, staging/output buckets, policies, retention rules, dashboards, and alerts with consumers disabled.
3. Deploy the dispatcher, worker, callback consumer, reconciler, and cleanup handlers to staging; verify startup region checks and non-PHI serialization before production deployment.
4. Enable staging dispatch, then test duplicate delivery, interruption in every phase, callback loss/redelivery, three-attempt exhaustion, supersession, deletion, and DLQ recovery.
5. Enable production queue dispatch and disable inline production extraction after queue health and provider privacy gates pass.

Rollback pauses the outbox dispatcher, callback consumer, reconciler, and workers, then returns to the prior release while preserving queued jobs, attempts, outbox rows, and active successful results. It never falls back to inline/mock production extraction, moves work to another region, marks unprocessed jobs complete, or deletes reviewed output.
