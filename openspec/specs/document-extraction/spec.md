# Document Extraction Specification

## Purpose

Define the asynchronous job model and reviewable output contract for AI-assisted document extraction.

## Requirements

### Requirement: Explicit extraction job lifecycle
The service SHALL represent each consented file extraction as a job with observable status, timing, provider, and failure information.

#### Scenario: Queue a job
- **WHEN** a consented record file is accepted
- **THEN** the service SHALL create a job in `queued` status
- **AND** the record SHALL move to `queued_for_extraction`

#### Scenario: Run a queued job
- **WHEN** a queued job is run inline, through the API, or by the worker
- **THEN** the job and record SHALL move through `extracting`
- **AND** successful completion SHALL set the job to `ready` and the record to `extraction_ready`

#### Scenario: Extraction fails
- **WHEN** reading or extracting the file raises an error
- **THEN** the job SHALL move to `failed` with a failure reason and finish time
- **AND** the record SHALL move to `extraction_failed`

### Requirement: Normalized and auditable extraction results
Successful extraction SHALL retain raw provider output and create structured fields that can be reviewed independently.

#### Scenario: Store a successful result
- **WHEN** an extractor returns a document type, raw output, and normalized data
- **THEN** the job SHALL retain the raw output
- **AND** each extracted field SHALL retain its type, label, value, confidence, optional normalized value, and optional source reference
- **AND** every new field SHALL begin in `pending` confirmation status

#### Scenario: Read record extraction
- **WHEN** a user requests extraction details for an owned record
- **THEN** the service SHALL return the record, its jobs, and its extracted fields

### Requirement: Controlled job execution and retry
The service SHALL restrict job execution to valid lifecycle transitions and SHALL support retrying an owned job.

#### Scenario: Run a non-runnable job
- **WHEN** a user requests execution for a job that is neither `queued` nor `failed`
- **THEN** the service SHALL return HTTP 409

#### Scenario: Retry a job
- **WHEN** a user retries an owned job
- **THEN** the service SHALL remove pending fields from the prior attempt
- **AND** the service SHALL reset and rerun the job while preserving already reviewed fields

#### Scenario: Read another user's job
- **WHEN** a user requests an extraction job they do not own
- **THEN** the service SHALL return HTTP 404
