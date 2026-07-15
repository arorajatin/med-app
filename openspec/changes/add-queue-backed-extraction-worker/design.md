## Context

The data model already persists extraction jobs and their lifecycle. Upload can run extraction inline, and `python -m app.worker once` polls the first queued job. Neither path atomically claims work, distinguishes retryable failures, recovers abandoned execution, or coordinates queue delivery with the database commit.

## Goals / Non-Goals

**Goals:**

- Decouple production extraction latency from HTTP uploads.
- Provide durable dispatch, exclusive claims, retries, and recovery.
- Keep queue messages free of medical document contents.
- Retain simple deterministic local and test execution.

**Non-Goals:**

- Choose or implement the production extraction provider.
- Parallelize a single document across pages.
- Add user-facing cancellation or priority controls.
- Guarantee exactly-once delivery from the queue.

## Decisions

### Treat the database job as source of truth

Queue messages carry only a job ID and delivery metadata. The worker loads ownership, file location, consented record context, and status from the database. Queue state cannot override a terminal database state.

### Use atomic leased claims

Add attempt and claim metadata to the job or a related attempt table. A worker claims a runnable job with a conditional database update. The claim expires after a bounded lease so work can recover after termination.

### Design for at-least-once delivery

Assume messages can be duplicated or redelivered. Provider invocation and result publication are guarded by the database claim and attempt identity. A completed attempt is acknowledged without replaying side effects.

### Dispatch after a durable database write

Use a transactional outbox or an equivalent persistent dispatcher so a queue outage cannot lose a committed job. Direct best-effort enqueue from the upload route is insufficient because database and queue commits are not atomic.

### Classify failures

Timeouts, rate limits, and selected transport errors can retry with exponential backoff and jitter. Unsupported input, invalid configuration, and exhausted attempts become terminal failures. API failure messages remain safe and do not include provider response bodies.

### Preserve local execution

Refactor the core claim and execution logic so the queue consumer, manual API run, and local run-once command share it. Local tests can use a synchronous fake dispatcher without external infrastructure.

## Risks / Trade-offs

- A queue adds operational cost and deployment complexity -> select the simplest supported service after a focused spike.
- Provider calls may not be idempotent -> prevent duplicate claims and make result publication attempt-scoped.
- Leases can expire during legitimate long work -> heartbeat or extend claims with strict maximum duration.
- Outbox rows can accumulate if dispatch is down -> monitor oldest pending dispatch and retry continuously.

## Migration Plan

1. Add claim, attempt, and outbox persistence through a migration.
2. Refactor current execution behind the shared claim service.
3. Deploy the worker and dispatcher with queue consumption disabled.
4. Enable dispatch in staging, test interruption and redelivery, then enable production.
5. Disable inline production extraction after queue processing is healthy.

Rollback stops new dispatch and workers, then restores the prior application while leaving queued database jobs intact. It must not mark unprocessed jobs complete or delete reviewed fields.

## Open Questions

- Which managed queue and worker runtime fit the deployment platform and medical-data requirements?
- What attempt limit, timeout, and backoff values match the selected provider?
- Should manual retry create a new attempt on the same job or a new job linked to the original?
- What operational alert thresholds apply to queue age, failure rate, and abandoned claims?
