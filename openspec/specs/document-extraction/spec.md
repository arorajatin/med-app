# Document Extraction Specification

## Purpose

Define the asynchronous job and attempt model, the normalized output classes, and the fail-closed
safety boundary for AI-assisted extraction of one immutable logical document.

## Requirements

### Requirement: Explicit extraction job and attempt lifecycle
The service SHALL represent each consented logical-document extraction as a job with observable
status, phase, timing, and failure information. Every run of a job SHALL create one atomic numbered
attempt that records the provider, its components, the processing method, and the routing reason.

#### Scenario: Queue a job
- **WHEN** an upload-complete ingestion has accepted consent
- **THEN** the service SHALL create a job in `queued` status
- **AND** the ingestion's extraction state SHALL become `queued`

#### Scenario: Run a queued job
- **WHEN** a queued job is run inline, through the API, or by the worker
- **THEN** the job and the ingestion SHALL move through `extracting`
- **AND** the run SHALL create the next sequential attempt for that job
- **AND** successful completion SHALL set the job, its attempt, and the ingestion's extraction state to `ready`

#### Scenario: Extraction fails
- **WHEN** reading or extracting the logical document raises an error
- **THEN** the job and its attempt SHALL move to `failed` with the generic failure code `extraction_failed` and a finish time
- **AND** the ingestion's extraction state SHALL become `failed`
- **AND** provider exception text and partial provider output SHALL NOT be persisted or returned

#### Scenario: Run a non-runnable job
- **WHEN** an owner requests execution for a job that is neither `queued` nor `failed`
- **THEN** the service SHALL return HTTP 409

#### Scenario: Retry a job
- **WHEN** an owner retries an owned job
- **THEN** the service SHALL reset the job to `queued` and rerun it as a new numbered attempt
- **AND** the service SHALL discard the earlier attempt's pending candidates and patient evidence, together with their source references, so the retry leaves no duplicate and no orphaned reference
- **AND** a re-extracted metric observation SHALL supersede the prior active observation for the same metric so exactly one active value remains

#### Scenario: Retry a job whose candidates were already reviewed
- **WHEN** a retried job re-proposes a document-metadata candidate of a type, or a candidate-memory item of a subtype and label, that the owner has already confirmed, edited, or ignored
- **THEN** the service SHALL preserve the reviewed candidate and its review history
- **AND** it SHALL NOT persist a pending duplicate that would displace the owner's decision
- **AND** the memory facts derived from that decision SHALL remain active

#### Scenario: Read another account's job
- **WHEN** a caller requests an extraction job their account does not own
- **THEN** the service SHALL return HTTP 404

### Requirement: Normalized output classes with resolvable source references
A successful extraction SHALL produce only patient evidence, document-metadata candidates, metric
observations, and candidate-memory items. Every persisted item SHALL carry at least one source
reference that resolves to an ingestion part, a logical page, the exact text span, and a bounding
polygon.

#### Scenario: Persist a normalized result
- **WHEN** an extraction result is persisted
- **THEN** each item SHALL record the attempt that produced it and its confidence
- **AND** each item SHALL store its source references against the ingestion part identified by the reference's part ordinal

#### Scenario: A source reference points nowhere
- **WHEN** an item's source reference names a part ordinal that the ingestion does not contain
- **THEN** the attempt SHALL fail without persisting a partial result

#### Scenario: Deterministic measurements bypass review
- **WHEN** an extraction produces metric observations
- **THEN** the service SHALL store them automatically as untrusted, auditable, source-linked values
- **AND** they SHALL NOT require review and SHALL NOT enter medical memory

### Requirement: Fail-closed condition-safety boundary
Until the structured literal-source contract for documented conditions is implemented, every
successful extraction SHALL pass through a fail-closed condition-safety boundary before persistence.
Only the built-in mock extractor implementation MAY persist the closed set of baseline non-condition
items: `document_type` and `record_date` metadata, metric observations, and
`prescription_medication` and `prescription_instruction` memory candidates. Items from any other
extractor implementation, unknown metadata types and subtypes, condition-shaped items, and items
without structured source references SHALL be omitted. The boundary SHALL persist a sanitized audit
summary as the attempt's protected raw output instead of unrestricted provider output.

#### Scenario: Store a safe built-in mock result
- **WHEN** the built-in mock extractor returns a permitted baseline non-condition item with structured source references
- **THEN** the attempt SHALL retain only a sanitized document type, provider item count, retained item count, and condition-safety decision summary as its raw output
- **AND** it SHALL NOT retain the extractor's unrestricted provider output
- **AND** each retained candidate SHALL begin in `pending` review status

#### Scenario: An unapproved extractor returns output
- **WHEN** an extractor other than the exact built-in mock implementation returns items
- **THEN** the boundary SHALL omit every item before persistence
- **AND** a provider name that happens to equal `mock` SHALL NOT bypass the implementation check

#### Scenario: Provider output proposes a condition
- **WHEN** an item's metadata type or subtype contains `condition`, `diagnosis`, `disease`, `impression`, or `problem`, or a memory candidate carries exact condition text
- **THEN** the service SHALL omit that item before persistence
- **AND** it SHALL NOT create a reviewable condition candidate or a trusted condition fact

#### Scenario: Provider output is not anchored to the source
- **WHEN** an item has no source reference, or a reference lacks a positive logical page, a non-empty text span, or a polygon of at least three points
- **THEN** the service SHALL omit that item before persistence

#### Scenario: Read an extraction
- **WHEN** an owner requests extraction details for an owned record or ingestion
- **THEN** the service SHALL return the ingestion, its record, its jobs and attempts, and the persisted patient evidence, metadata candidates, metric observations, memory candidates, and source references
- **AND** it SHALL return only active metric observations, omitting values a later attempt superseded
- **AND** the protected raw-output storage identity SHALL NOT appear in the response
- **AND** condition-shaped and unsupported provider output SHALL never appear because the persistence boundary omits it
