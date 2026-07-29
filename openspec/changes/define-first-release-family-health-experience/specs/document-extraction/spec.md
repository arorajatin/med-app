## MODIFIED Requirements

### Requirement: Explicit extraction job lifecycle
The service SHALL represent each consented logical-document extraction as a job with observable status, timing, provider, method, and failure information.

#### Scenario: Queue a job
- **WHEN** a consented completed logical document is accepted
- **THEN** the service SHALL create one job in `queued` status for that logical document
- **AND** the record or staged ingestion SHALL move to `queued_for_extraction`

#### Scenario: Run a queued job
- **WHEN** a queued job is run inline, through the API, or by the worker
- **THEN** the job and source SHALL move through `extracting`
- **AND** successful completion SHALL set the job to `ready` and the source to `extraction_ready`

#### Scenario: Extraction fails
- **WHEN** reading, combining, or extracting the logical document raises an error
- **THEN** the job SHALL move to `failed` with a safe failure reason and finish time
- **AND** the source SHALL move to `extraction_failed`

### Requirement: Normalized and auditable extraction results
Successful extraction SHALL retain raw provider output and create structured patient-match evidence, unreviewed metric observations, and pending candidate-memory items that can be audited independently.

#### Scenario: Store a successful result
- **WHEN** an extractor returns a document type, raw output, and normalized data
- **THEN** the job SHALL retain the raw output
- **AND** each normalized item SHALL retain its class, type, label, value, confidence, optional normalized value, and optional source reference
- **AND** candidate-memory items SHALL begin in `pending` review status
- **AND** patient-match evidence and metric observations SHALL remain explicitly untrusted even though they do not require candidate-memory approval

#### Scenario: Read record extraction
- **WHEN** a user requests extraction details for an owned record
- **THEN** the service SHALL return the source lifecycle, jobs, patient-match evidence, metric observations, and candidate-memory items that the user is authorized to view

## ADDED Requirements

### Requirement: Select a processing path from document content
The extraction system SHALL distinguish text-bearing, scanned-image, and hybrid documents and SHALL retain the selected processing method with the attempt.

#### Scenario: Process a text-bearing document
- **WHEN** a supported document contains usable embedded text
- **THEN** extraction SHALL use the configured text-capable path
- **AND** the attempt SHALL record the selected method and provider

#### Scenario: Process a scanned or photographed document
- **WHEN** a supported document requires OCR or vision processing
- **THEN** extraction SHALL use a configured OCR- or vision-capable path
- **AND** the attempt SHALL record the selected method and provider

#### Scenario: Process a hybrid document
- **WHEN** different pages require different supported processing methods
- **THEN** extraction SHALL preserve page-level source references while producing one normalized result set

### Requirement: Extract patient identity for family-profile resolution
The extraction result SHALL represent the patient name and available identity context as reviewable, source-linked output for matching only against profiles owned by the account.

#### Scenario: Patient identity is available
- **WHEN** a document contains an extractable patient identity
- **THEN** the result SHALL retain the extracted value, confidence, and source reference

#### Scenario: Patient identity is unavailable
- **WHEN** no reliable patient identity can be extracted
- **THEN** extraction SHALL report that identity is unresolved rather than invent a value

### Requirement: Separate observations from candidate memory
The extraction result SHALL classify deterministic report measurements separately from candidate insights, conditions, medications, and follow-up information.

#### Scenario: Extract a deterministic measurement
- **WHEN** a report contains a measurement with an observed value
- **THEN** extraction SHALL return a source-linked observation candidate with its metric identity, original value and unit, optional normalized value, reference range when present, observation date, confidence, and source location
- **AND** the candidate SHALL NOT be classified as trusted medical memory

#### Scenario: Extract a candidate insight or medication
- **WHEN** a report contains a condition, interpretation, medication, or follow-up candidate
- **THEN** extraction SHALL return it as a pending candidate-memory item with confidence and source location

#### Scenario: Extraction output is incomplete
- **WHEN** a normalized value cannot be supported by the document source
- **THEN** extraction SHALL omit or explicitly mark that value unavailable rather than fabricate it

### Requirement: Publish derived output only after successful assignment
The system SHALL defer publication of observations and candidate memory until extraction succeeds atomically and the document has a resolved owned profile.

#### Scenario: Extraction and assignment succeed
- **WHEN** a complete extraction result commits and the document has a resolved profile
- **THEN** eligible observations and pending candidate-memory items SHALL become available under that profile

#### Scenario: Assignment remains pending
- **WHEN** extraction succeeds but patient assignment remains unresolved
- **THEN** normalized output MAY remain staged for account-manager resolution
- **AND** it SHALL NOT appear in a profile's metrics or medical memory
