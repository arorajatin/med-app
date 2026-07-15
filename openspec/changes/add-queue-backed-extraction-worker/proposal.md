## Why

Production extraction can be slow, rate-limited, or interrupted. Inline execution and a single polling command do not provide durable dispatch, safe concurrent workers, or controlled recovery after process failure.

## What Changes

- Dispatch consented extraction jobs to a durable queue after upload commits.
- Run production extraction in independently scalable worker processes.
- Claim jobs atomically so concurrent workers cannot publish duplicate results.
- Add bounded retries with backoff and terminal failure reporting.
- Recover jobs left in progress by worker interruption.
- Keep a deterministic local execution path for development and tests.

This change does not select the production extraction provider or change the human review contract.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `document-extraction`: Add durable dispatch, exclusive execution, retry policy, and interrupted-job recovery.

## Impact

Affected areas include upload transaction boundaries, extraction job metadata, worker deployment, queue infrastructure, retry semantics, idempotency, monitoring, and tests. Medical-data privacy is affected because queue payloads must not contain file bytes or extracted values.
