## ADDED Requirements

### Requirement: Durable production dispatch
Production uploads with AI-processing consent SHALL dispatch the committed extraction job to a durable queue and SHALL NOT wait for extraction to finish in the HTTP request.

#### Scenario: Upload and dispatch
- **WHEN** a consented file and its queued job commit successfully
- **THEN** the service SHALL enqueue the job identifier for background processing
- **AND** the upload response SHALL return without waiting for provider completion

#### Scenario: Queue is temporarily unavailable
- **WHEN** the job commits but immediate queue dispatch fails
- **THEN** the queued job SHALL remain discoverable for later dispatch
- **AND** the service SHALL expose enough status for operators to detect the delay

#### Scenario: Protect queue payloads
- **WHEN** a job is dispatched
- **THEN** the queue payload SHALL contain identifiers and control metadata only
- **AND** it SHALL NOT contain file bytes, raw provider output, or extracted medical values

### Requirement: Exclusive and idempotent execution
The worker system SHALL prevent concurrent deliveries from publishing more than one successful result set for the same extraction attempt.

#### Scenario: Two workers receive the same job
- **WHEN** duplicate queue delivery or concurrent polling occurs
- **THEN** only one worker SHALL claim the runnable job
- **AND** other workers SHALL exit without invoking the provider for that claim

#### Scenario: Completion is delivered again
- **WHEN** a completed job message is redelivered
- **THEN** the worker SHALL acknowledge it without creating duplicate fields or changing reviewed output

### Requirement: Bounded retry policy
The worker SHALL retry transient extraction failures with bounded attempts and backoff while preserving a terminal failure state for non-transient or exhausted errors.

#### Scenario: Transient failure
- **WHEN** a claimed job fails with a retryable provider, network, or rate-limit error and attempts remain
- **THEN** the worker SHALL schedule another attempt after backoff
- **AND** the API SHALL continue to expose the job as pending retry

#### Scenario: Permanent or exhausted failure
- **WHEN** an error is non-retryable or the attempt limit is exhausted
- **THEN** the job SHALL move to terminal `failed` status with a safe failure reason
- **AND** no automatic retry SHALL occur without an explicit user or operator action

### Requirement: Interrupted-job recovery
The worker system SHALL detect and safely recover claims abandoned by worker termination.

#### Scenario: Worker stops during extraction
- **WHEN** a worker terminates after claiming a job but before committing completion
- **THEN** the claim SHALL become eligible for recovery after its lease or visibility timeout
- **AND** a later worker SHALL be able to retry without duplicating a committed result

#### Scenario: Worker completes successfully
- **WHEN** a worker commits extraction results and ready status
- **THEN** it SHALL acknowledge the queue delivery only after that commit succeeds

### Requirement: Local execution path
Local development and tests SHALL be able to execute queued extraction deterministically without production queue infrastructure.

#### Scenario: Run locally
- **WHEN** queue-backed production processing is disabled in an allowed local or test environment
- **THEN** the existing inline or run-once path MAY process a queued job through the same claim and execution service
