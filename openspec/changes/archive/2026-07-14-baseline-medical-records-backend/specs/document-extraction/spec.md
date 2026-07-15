## ADDED Requirements

### Requirement: Explicit extraction job lifecycle
The service SHALL represent each consented extraction as a job with status, timing, provider, and failure information.

#### Scenario: Successful run
- **WHEN** a queued job is run successfully
- **THEN** it SHALL progress through extracting to ready
- **AND** its record SHALL move to extraction ready

#### Scenario: Failed run
- **WHEN** reading or extracting a file fails
- **THEN** the job SHALL retain a failure reason and its record SHALL move to extraction failed

### Requirement: Normalized and auditable extraction results
Successful extraction SHALL retain raw provider output and structured reviewable fields.

#### Scenario: Store result
- **WHEN** the extractor returns output
- **THEN** the job SHALL retain raw output
- **AND** each field SHALL retain its value, confidence, source context, and pending status

### Requirement: Controlled job execution and retry
The service SHALL restrict job execution to valid states and allow owned jobs to be retried.

#### Scenario: Retry a job
- **WHEN** an owner retries a job
- **THEN** pending output from the prior attempt SHALL be removed before rerunning
- **AND** reviewed fields SHALL be preserved
