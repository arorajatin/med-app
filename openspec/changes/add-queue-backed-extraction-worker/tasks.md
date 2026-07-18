## 1. Queue and Claim Design

- [ ] 1.1 Evaluate supported queue services and record the selected service and rejected alternatives.
- [ ] 1.2 Define retryable errors, attempt limits, backoff, lease duration, and recovery semantics.
- [ ] 1.3 Add migration-backed claim, attempt, and transactional outbox data.

## 2. Dispatch and Worker

- [ ] 2.1 Refactor extraction behind an atomic shared claim and execution service.
- [ ] 2.2 Publish committed job identifiers through the durable outbox dispatcher.
- [ ] 2.3 Implement the queue consumer with claim renewal, result commit, and post-commit acknowledgement.
- [ ] 2.4 Add bounded retry scheduling and terminal failure handling.
- [ ] 2.5 Keep inline and run-once adapters for allowed local and test environments.

## 3. Verification and Operations

- [ ] 3.1 Test duplicate delivery, concurrent claims, queue outage, retry exhaustion, and worker interruption.
- [ ] 3.2 Verify queue messages and logs contain no file bytes or extracted medical values.
- [ ] 3.3 Add metrics and alerts for dispatch age, queue age, abandoned claims, retries, and failures.
- [ ] 3.4 Document worker deployment, scaling, pause, drain, recovery, and rollback.
- [ ] 3.5 Run the backend test suite and strict OpenSpec validation.
- [ ] 3.6 Complete implementation review and finalize `review.md` with the reviewed commit, test evidence, findings, and resume state.
