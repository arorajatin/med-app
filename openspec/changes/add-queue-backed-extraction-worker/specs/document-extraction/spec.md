## ADDED Requirements

### Requirement: Dispatch one immutable logical document
The extraction system SHALL create one job only for an upload-complete logical document created through an authenticated, account-owned `direct_file` or `camera` web-upload route, and SHALL make every attempt in that job generation reference the same immutable ordered source-part manifest.

#### Scenario: Dispatch a finalized report
- **WHEN** every source part has committed and the authenticated, account-owned logical document is finalized
- **THEN** the service SHALL persist one queued job and one dispatch outbox event in the finalization transaction
- **AND** each attempt SHALL process every source part in its stored ordinal order

#### Scenario: Reject another ingestion source
- **WHEN** a logical document does not carry immutable `direct_file` or `camera` provenance stamped by an authenticated web-upload route
- **THEN** the service SHALL NOT create or dispatch an extraction job

#### Scenario: Source parts are incomplete
- **WHEN** any source part is missing, failed, or not finalized
- **THEN** the service SHALL NOT create or dispatch an extraction job

#### Scenario: Input changes after finalization
- **WHEN** a caller attempts to add, remove, reorder, or replace a part in a finalized manifest
- **THEN** the service SHALL reject the mutation
- **AND** changed input SHALL require a new logical document rather than an in-place retry

### Requirement: Keep durable orchestration in India
Production extraction dispatch and continuation SHALL use encrypted Amazon SQS, Amazon SNS, worker, KMS, temporary object, log, and metric resources located only in AWS `ap-south-1` and SHALL use the Mumbai database as orchestration source of truth.

#### Scenario: Publish a committed job
- **WHEN** the outbox dispatcher observes an undelivered job event
- **THEN** it SHALL publish the opaque job and attempt identifiers to the regional extraction queue
- **AND** it SHALL record delivery idempotently without changing the committed job's input

#### Scenario: Queue publication is unavailable
- **WHEN** a job commits but SQS publication fails
- **THEN** the outbox event SHALL remain due for later delivery
- **AND** operators SHALL be alerted when the oldest undelivered event exceeds two minutes

#### Scenario: A physical dispatch is lost or expires
- **WHEN** a due, non-terminal phase remains unclaimed for 10 minutes after its latest recorded dispatch
- **THEN** a reconciler SHALL create a new idempotent dispatch generation for the same attempt and phase
- **AND** conditional claiming SHALL make duplicate physical delivery harmless

#### Scenario: A resource is configured outside Mumbai
- **WHEN** production startup detects a queue, topic, worker, key, bucket, log group, database, or failover target outside `ap-south-1`
- **THEN** extraction dispatch SHALL fail closed before reading or transmitting a medical document

### Requirement: Keep queue messages and telemetry free of PHI
Application queue messages, Textract continuation messages, metrics, traces, and logs SHALL contain only opaque identifiers, enumerated control state, safe error classes, and timing/count data.

#### Scenario: Dispatch application work
- **WHEN** the service creates an extraction or continuation message
- **THEN** the serialized application payload SHALL be limited to schema/event version, opaque job, attempt, outbox, provider-job, and correlation identifiers, plus enumerated provider status when applicable
- **AND** the worker SHALL load ownership, manifest, and private object references from the database after claiming the attempt

#### Scenario: Record telemetry or an error
- **WHEN** the dispatcher, worker, provider callback, reconciler, or cleanup process emits telemetry
- **THEN** it SHALL NOT include file bytes, document or extracted text, normalized values, filenames, account contact data, account/profile/patient identifiers, document metadata or hashes, object paths, URLs, provider response bodies, or credentials

### Requirement: Execute attempts through resumable provider phases
Each numbered attempt SHALL move conditionally through persisted inspection, native-text or Textract, model extraction, normalization, and publication phases so asynchronous provider work can resume without creating a second attempt.

#### Scenario: Use native PDF text
- **WHEN** the provider adapter selects `native_text` for the complete PDF
- **THEN** the attempt SHALL record the method and routing reason
- **AND** it SHALL move through `native_extracting`, `model_extracting`, `normalizing`, and `publishing` before success

#### Scenario: Use Textract for images
- **WHEN** the logical document is one JPEG/PNG or an ordered image set
- **THEN** the attempt SHALL process the source parts through `textract_extracting` in manifest order
- **AND** it SHALL converge on the same model, normalization, and publication phases as native extraction

#### Scenario: Submit a PDF to asynchronous Textract
- **WHEN** the provider adapter selects `textract_ocr` for a PDF
- **THEN** the worker SHALL persist `textract_submitting` before invoking Textract with an attempt-derived idempotency token and the regional callback topic
- **AND** after persisting the provider job identifier it SHALL enter `textract_waiting` and release its worker claim

#### Scenario: Receive a successful Textract callback
- **WHEN** the authorized regional callback queue delivers a terminal success for the provider job mapped to a waiting attempt
- **THEN** the callback consumer SHALL create one idempotent continuation event
- **AND** a worker SHALL claim that event and continue through `textract_collecting`, model extraction, normalization, and publication on the same attempt

#### Scenario: Callback is duplicate, late, or mismatched
- **WHEN** a callback has already been applied, targets a cancelled or terminal attempt, or does not match the stored provider job
- **THEN** the consumer SHALL acknowledge it without fetching source data, invoking another provider, or changing published output

#### Scenario: Callback does not arrive
- **WHEN** an attempt has remained in `textract_waiting` for 60 minutes
- **THEN** a reconciler SHALL check the stored provider job once and create the same idempotent continuation if it completed
- **AND** an unavailable or still-in-progress job SHALL become a retryable provider timeout

### Requirement: Claim executable phases exclusively
The worker system SHALL use a five-minute conditional database claim, renewed every 60 seconds with the queue visibility timeout, and SHALL require the current claim token for every phase transition and result commit.

#### Scenario: Two workers receive the same attempt
- **WHEN** duplicate delivery or concurrent polling occurs
- **THEN** only one worker SHALL obtain the runnable phase claim
- **AND** every non-claiming worker SHALL acknowledge or release its delivery without invoking the provider

#### Scenario: A worker loses its claim
- **WHEN** the claim expires or a heartbeat conditional update fails during synchronous processing
- **THEN** that worker SHALL become ineligible to transition or publish
- **AND** recovery SHALL record an interrupted retryable failure for the numbered attempt

#### Scenario: Completion is delivered again
- **WHEN** a message for a succeeded, failed, cancelled, or superseded attempt is redelivered
- **THEN** the worker SHALL acknowledge it without re-invoking a provider or republishing output

### Requirement: Apply the fixed bounded retry policy
Each job generation SHALL receive at most three total automatic attempts, including the initial attempt, and SHALL persist its randomized next-attempt time before acknowledging a retryable failure.

#### Scenario: Attempt 1 fails transiently
- **WHEN** attempt 1 ends with a timeout, throttle, HTTP 429, provider/AWS 5xx or unavailability, transient regional transport failure, interrupted claim, retryable Textract failure, or callback timeout
- **THEN** attempt 2 SHALL be scheduled after 30 seconds multiplied by one uniform random factor in `[0.8, 1.2]`
- **AND** the persisted delay SHALL be between 24 and 36 seconds

#### Scenario: Attempt 2 fails transiently
- **WHEN** attempt 2 ends with a retryable failure
- **THEN** attempt 3 SHALL be scheduled after two minutes multiplied by one uniform random factor in `[0.8, 1.2]`
- **AND** the persisted delay SHALL be between 96 and 144 seconds

#### Scenario: Report a scheduled retry to a client
- **WHEN** another numbered attempt has been scheduled but is not yet due
- **THEN** the public job status SHALL be `retrying`
- **AND** internal phase names, exact due time, jitter factor, claim state, and queue-delivery state SHALL NOT become part of the client contract

#### Scenario: Failure is deterministic
- **WHEN** an attempt fails because input is unsupported, corrupt, encrypted, oversized, or over the part limit; region/ZDR/authentication/authorization/credentials/keys/roles/policies/provider configuration is invalid; output violates the schema; a source reference is unresolved or fabricated; or normalization deterministically fails
- **THEN** the job SHALL enter terminal `failed` with a stable safe failure code
- **AND** no automatic retry SHALL be scheduled

#### Scenario: Attempt 3 fails transiently
- **WHEN** the third attempt fails with an otherwise retryable error
- **THEN** the job SHALL enter terminal `failed` with `retry_exhausted` and the last safe retry class
- **AND** the system SHALL NOT create an automatic fourth attempt

#### Scenario: Explicitly retry a terminal job
- **WHEN** an account manager or authorized operator explicitly retries an owned terminal job
- **THEN** the service SHALL create a successor job generation linked to the failed generation with a fresh three-attempt budget
- **AND** it SHALL preserve the failed generation's audit history

### Requirement: Publish and supersede results idempotently
An extraction attempt SHALL publish either one complete validated result set or no new result set, and a successor generation SHALL replace an active result only after its own complete result commits.

#### Scenario: An attempt fails after partial provider work
- **WHEN** native/Textract collection, model extraction, schema or source-reference validation, normalization, or result commit fails
- **THEN** no staged output from that attempt SHALL become active or profile-visible
- **AND** a prior successful result and reviewed decisions SHALL remain unchanged

#### Scenario: An attempt succeeds
- **WHEN** raw output and all normalized items pass validation
- **THEN** raw output, normalized output, active-result pointer, job status, and source lifecycle SHALL commit in one transaction
- **AND** a uniqueness constraint SHALL prevent that attempt from publishing twice

#### Scenario: A successor generation succeeds
- **WHEN** a re-extraction publishes a complete replacement result
- **THEN** the service SHALL atomically activate the replacement and mark the prior result superseded
- **AND** observations and review decisions SHALL follow their capability-specific preservation and supersession rules

### Requirement: Recover interruption only after durable state
The worker SHALL acknowledge queue delivery only after its phase transition, Textract wait, continuation event, retry schedule, cancellation, or terminal result is durably committed.

#### Scenario: Worker stops before commit
- **WHEN** a worker terminates after claiming a phase but before committing its next durable state
- **THEN** the claim SHALL become recoverable after its five-minute lease
- **AND** no uncommitted output SHALL become active

#### Scenario: Worker stops after commit but before acknowledgement
- **WHEN** durable state commits but SQS acknowledgement does not
- **THEN** redelivery SHALL load the committed state and continue or acknowledge idempotently

### Requirement: Cancel and clean up report work safely
Report deletion SHALL prevent new extraction work, make late deliveries harmless, and trigger idempotent regional cleanup.

#### Scenario: Delete a report with pending work
- **WHEN** an owned report is deleted while its job is queued, claimed, retry-scheduled, or waiting for Textract
- **THEN** the service SHALL synchronously block new claims and mark unfinished attempts `cancelled`
- **AND** later dispatches or callbacks SHALL acknowledge without reading source content or publishing output

#### Scenario: Clean temporary provider objects
- **WHEN** provider output is durably persisted or an attempt terminates
- **THEN** Textract input/output staging objects SHALL be deleted immediately
- **AND** a 24-hour lifecycle SHALL remove any object missed by immediate cleanup

#### Scenario: Apply retention
- **WHEN** extraction data reaches the end of its retention period
- **THEN** successful encrypted raw native/Textract and Bedrock output SHALL remain only until report deletion, failed attempts SHALL retain only a safe non-PHI envelope for 30 days, and delivered outbox/log records SHALL expire after 30 days
- **AND** extraction/callback messages SHALL expire after four days, dead-letter messages after 14 days, and a non-PHI idempotency tombstone after 90 days from report deletion

### Requirement: Preserve a deterministic local execution path
Local development and tests SHALL execute the same claim, phase, retry, callback, publication, and cleanup services without production queue infrastructure.

#### Scenario: Run locally
- **WHEN** queue-backed processing is disabled in an allowed local or test environment
- **THEN** an in-memory dispatcher, fake clock, deterministic jitter source, and fake provider MAY process work synchronously through the production state machine

#### Scenario: Start production with a local adapter
- **WHEN** production configuration selects inline execution, an in-memory dispatcher, a mock provider, or a non-Mumbai resource
- **THEN** startup SHALL fail closed
