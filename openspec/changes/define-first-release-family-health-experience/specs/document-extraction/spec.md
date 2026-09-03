## MODIFIED Requirements

### Requirement: Explicit logical-document extraction lifecycle
The service SHALL represent each consented immutable logical-document extraction as an attempt-aware job with public status, internal phase, timing, provider-component provenance, processing method, routing reason, and safe failure information.

#### Scenario: Queue one logical document
- **WHEN** a consented upload-complete logical document is accepted
- **THEN** the service SHALL create one job in `queued` for that document and attempt
- **AND** the source SHALL move to `queued_for_extraction`

#### Scenario: Run a queued job
- **WHEN** a worker claims a queued job
- **THEN** it SHALL process every ordered source part as one immutable input
- **AND** internal phases SHALL distinguish native parsing, Textract submission or callback, Bedrock structuring, and normalization as applicable
- **AND** the public job SHALL remain `extracting` until one complete result commits

#### Scenario: Extraction succeeds
- **WHEN** source-reference validation and atomic result persistence complete
- **THEN** the job SHALL become `ready`
- **AND** the source SHALL become `extraction_ready`

#### Scenario: Extraction fails
- **WHEN** an attempt ends without a complete valid result
- **THEN** no partial normalized output SHALL be published
- **AND** the attempt SHALL retain its safe failure code and finish time
- **AND** the public job SHALL become `retrying` when another attempt is scheduled or `failed` when no retry remains

### Requirement: Normalized and auditable extraction results
Successful extraction SHALL retain encrypted raw processing output and normalize it into `patient_evidence`, `document_metadata_candidate`, `metric_observation`, and `memory_candidate` items that can be audited independently. A `memory_candidate` MAY use the `documented_condition_candidate` subtype only when the submitted document literally states the condition and the candidate cites that exact source text.

#### Scenario: Store a successful result
- **WHEN** extraction returns a supported document type and complete schema-valid data
- **THEN** the attempt SHALL retain its processing method, routing reason, component provenance, raw output, and normalized items
- **AND** each normalized item SHALL retain its class, source-backed literal value, confidence, extraction attempt, and at least one valid source reference
- **AND** every documented-condition candidate SHALL retain its subtype, the exact condition text written in the document, and a source reference to the text span that names that condition
- **AND** patient evidence and metric observations SHALL remain explicitly untrusted
- **AND** document metadata and memory candidates SHALL begin in `pending` review status

#### Scenario: Read record extraction
- **WHEN** a user requests extraction details for an owned record
- **THEN** the service SHALL return safe lifecycle, patient evidence, metadata candidates, observations, memory candidates, and source references
- **AND** it SHALL NOT return unrestricted raw provider output, credentials, provider request payloads, or internal object keys

## ADDED Requirements

### Requirement: Restrict V1 document inputs
V1 extraction SHALL support English-language lab reports and prescriptions supplied as unencrypted PDF, JPEG, or PNG logical documents within fixed product ceilings.

#### Scenario: Accept a supported logical document
- **WHEN** a logical document is at most 15,000,000 bytes, contains at most 20 pages or parts, each image is at most 10,000,000 bytes and 10,000 pixels per dimension, and every source part has a supported detected MIME type
- **THEN** it SHALL be eligible for extraction

#### Scenario: Reject invalid input
- **WHEN** content is empty, corrupt, encrypted, oversized, over the page/part limit, over an image limit, or outside PDF/JPEG/PNG
- **THEN** extraction SHALL fail terminally with a stable safe failure code
- **AND** no provider request SHALL be made for content that fails local validation

#### Scenario: Detect another document family
- **WHEN** valid source content is not a lab report or prescription
- **THEN** the private source SHALL remain available to its owner with `unsupported_document_type`
- **AND** extraction SHALL publish no patient assignment, metric, metadata, or memory result from that attempt

### Requirement: Select native text or whole-document OCR deterministically
The service SHALL use `pdfplumber` native extraction only when every nonblank PDF page passes the native-text gate; otherwise it SHALL route the entire PDF through Amazon Textract. JPEG, PNG, and ordered image sets SHALL always use Textract.

#### Scenario: Every PDF page passes native validation
- **WHEN** every nonblank page opens unencrypted, has at least 20 positioned word tokens, has at least 99 percent printable extracted characters, keeps every token bounding box within the page, and has no raster image covering 50 percent or more of the page
- **THEN** the attempt SHALL use `processing_method=native_text`
- **AND** it SHALL retain stable page, word, text-span, and normalized polygon references

#### Scenario: Any PDF page fails native validation
- **WHEN** one or more pages fails any native-text condition
- **THEN** the entire PDF SHALL use `processing_method=textract_ocr`
- **AND** the attempt SHALL record the first deterministic fallback reason
- **AND** it SHALL NOT combine native and OCR pages in one result

#### Scenario: Process ordered images
- **WHEN** the logical document contains one or more ordered JPEG or PNG parts
- **THEN** every part SHALL use Textract in source-part order
- **AND** all pages SHALL contribute to one normalized atomic result

### Requirement: Use the approved India-resident production providers
Production OCR and structuring SHALL use Amazon Textract and Amazon Bedrock Mistral Large 3 only through in-region `ap-south-1` endpoints, while local native parsing SHALL execute inside the Mumbai application boundary.

#### Scenario: Run Textract document analysis
- **WHEN** a document requires OCR
- **THEN** Textract SHALL analyze layout, tables, and forms in `ap-south-1`
- **AND** asynchronous PDF input/output, SNS completion, and SQS delivery SHALL remain in `ap-south-1`
- **AND** customer-controlled `OutputConfig` and KMS encryption SHALL be used for provider output

#### Scenario: Run structured extraction
- **WHEN** normalized source blocks are ready
- **THEN** Bedrock SHALL invoke `mistral.mistral-large-3-675b-instruct` through its in-region Mumbai endpoint with schema-constrained output
- **AND** the request SHALL contain document blocks and schema instructions but no account profile list

#### Scenario: Provider configuration violates the boundary
- **WHEN** a provider, endpoint, bucket, topic, queue, or model configuration is outside `ap-south-1`, enables cross-region inference, or selects an unapproved fallback
- **THEN** production extraction SHALL fail closed before transmitting medical data

#### Scenario: Zero-data-retention is unavailable
- **WHEN** the Bedrock account/model does not report effective `data_retention_mode: none`
- **THEN** production extraction SHALL remain disabled
- **AND** it SHALL NOT fall back to another model, region, or retention mode

### Requirement: Require valid source references
Every normalized item SHALL contain at least one `SourceReference` with source part ID, one-based logical page, native word or Textract block IDs, supporting text span, and normalized bounding polygon.

#### Scenario: References resolve
- **WHEN** every referenced part, page, block, span, and polygon resolves inside the immutable attempt input
- **THEN** normalization MAY commit the complete result

#### Scenario: A reference is absent or fabricated
- **WHEN** any normalized item lacks a reference or names a block, span, page, or polygon that cannot be resolved
- **THEN** the entire attempt SHALL fail terminally with `invalid_source_reference`
- **AND** no normalized item from that attempt SHALL be published

#### Scenario: A documented condition does not cite the condition itself
- **WHEN** a proposed documented-condition candidate cites medication, dosage, measurement, range, flag, symptom, or other text that does not itself name the condition
- **THEN** normalization SHALL omit that candidate
- **AND** other valid normalized items MAY still commit when the complete result passes all validation rules

### Requirement: Separate extraction trust classes
The extraction result SHALL preserve literal evidence and SHALL NOT infer a condition, diagnosis, follow-up, or other clinical interpretation in V1. It MAY extract a `documented_condition_candidate` only when a prescription or lab report literally names the condition.

#### Scenario: Extract patient evidence
- **WHEN** a document contains a literal patient name and may also contain a patient identifier or date of birth
- **THEN** extraction SHALL return it as source-linked `patient_evidence` for account-local matching only
- **AND** patient evidence MAY retain the source-linked date of birth when it is present
- **AND** the date of birth SHALL NOT be copied to a profile or used for automatic assignment

#### Scenario: Extract document metadata
- **WHEN** a document contains a literal report date, issuer, document type, or evidence for a display name
- **THEN** extraction SHALL return a `document_metadata_candidate`
- **AND** it SHALL require account-manager confirmation or edit before trusted use

#### Scenario: Extract a lab observation
- **WHEN** a lab report contains a literal measurement
- **THEN** extraction SHALL return a source-linked `metric_observation` with analyte, decimal or categorical value, original unit, reference range, flag, observation date, optional normalized value/unit, and confidence when present
- **AND** the observation SHALL remain `unreviewed_extracted` and outside medical memory and Chat evidence

#### Scenario: Extract a prescription item
- **WHEN** a prescription contains a literal medication instruction
- **THEN** extraction SHALL return a source-linked `memory_candidate` with medication name, strength, dosage form, dose, route, frequency, duration, and instructions when present
- **AND** it SHALL require explicit submitted review before becoming medical memory

#### Scenario: Extract a condition written in a prescription or lab report
- **WHEN** a prescription or lab report literally names a condition
- **THEN** extraction MAY return a source-linked `memory_candidate` with subtype `documented_condition_candidate`
- **AND** the candidate SHALL contain the exact condition text written in the document and a source reference to the span that names it
- **AND** it SHALL begin `pending` and remain outside trusted medical memory, Chat evidence, and Drive condition groups until the account manager confirms or edits it

#### Scenario: Medication evidence does not state a condition
- **WHEN** a prescription contains medication names, strengths, dosages, routes, frequencies, durations, or instructions but does not literally name a condition
- **THEN** extraction SHALL NOT create a documented-condition candidate from those medication details

#### Scenario: Lab evidence does not state a condition
- **WHEN** a lab report contains measurements, reference ranges, or abnormal flags but does not literally name a condition
- **THEN** extraction SHALL NOT create a documented-condition candidate from those lab details

#### Scenario: Symptoms or general knowledge do not state a condition
- **WHEN** a document contains symptoms or could be associated with a condition through general medical knowledge but does not literally name that condition
- **THEN** extraction SHALL NOT create a documented-condition candidate from those symptoms or associations

#### Scenario: Source does not support a value
- **WHEN** a requested normalized value is absent or cannot be cited
- **THEN** extraction SHALL omit it or mark it unavailable rather than infer or fabricate it


### Requirement: Review document metadata before trusted use
The account manager SHALL be able to confirm, edit, or ignore each owned `document_metadata_candidate`, and the system SHALL retain the original extraction, submitted value, reviewer, time, and source reference.

#### Scenario: Confirm or edit report metadata
- **WHEN** the account manager confirms or edits a pending report date, issuer, type, or display-name suggestion
- **THEN** the submitted value SHALL become trusted document metadata
- **AND** a trusted report date MAY drive Feed ordering
- **AND** a trusted generated display name SHALL remain subordinate to an explicit user rename

#### Scenario: Ignore report metadata
- **WHEN** the account manager ignores a metadata candidate
- **THEN** it SHALL NOT drive report-date ordering, issuer display, type-dependent derived publication, or a generated display name

#### Scenario: Review another account's metadata
- **WHEN** a review submission references a candidate outside the authenticated account
- **THEN** the complete review request SHALL be rejected without revealing foreign metadata

### Requirement: Resolve patients with exact account-local matching
Patient matching SHALL compare source-linked patient evidence only with normalized full names and explicit aliases of profiles owned by the ingestion account.

#### Scenario: Exactly one profile matches
- **WHEN** Unicode NFKC, case-folded, trimmed, whitespace-collapsed patient name exactly equals one owned profile name or explicit alias
- **THEN** that profile SHALL be the automatic assignment result

#### Scenario: Matching is unsafe
- **WHEN** zero or multiple profiles match exactly, or only fuzzy, phonetic, partial, or scored similarity exists
- **THEN** automatic matching SHALL return unresolved
- **AND** the document SHALL become `needs_assignment`

### Requirement: Publish output only after atomic success and assignment
The system SHALL defer profile-scoped publication until one complete extraction result commits and the logical document has a resolved owned profile.

#### Scenario: Extraction and assignment succeed
- **WHEN** a complete valid result commits and assignment is resolved
- **THEN** eligible unreviewed observations, pending metadata candidates, and pending memory candidates SHALL become available under that profile

#### Scenario: Assignment remains pending
- **WHEN** extraction succeeds but assignment remains unresolved
- **THEN** normalized output MAY remain staged for account-manager resolution
- **AND** it SHALL NOT appear in profile metrics, trusted metadata, medical memory, Drive, or Chat

### Requirement: Retry attempts safely and retain audit output
An attempt SHALL publish either one complete result set or none, SHALL retry only transient failures, and SHALL retain successful raw processing output until report deletion.

#### Scenario: A transient failure occurs
- **WHEN** a timeout, throttle, or provider 5xx prevents completion
- **THEN** the worker SHALL make at most three total attempts
- **AND** retries SHALL use jittered delays based on 30 seconds and two minutes

#### Scenario: A terminal failure occurs
- **WHEN** input validation, document-type support, schema validation, or source-reference validation fails
- **THEN** the job SHALL fail without automatic retry

#### Scenario: A later attempt succeeds
- **WHEN** a retry commits a complete result
- **THEN** it SHALL supersede matching active output without duplicate publication
- **AND** prior attempt identity and safe audit history SHALL remain traceable

#### Scenario: Retain and delete successful raw output
- **WHEN** native/Textract and Bedrock processing succeeds
- **THEN** raw output SHALL remain encrypted and inaccessible to routine clients until the report is deleted
- **AND** report deletion SHALL purge that raw output and every report-derived result
- **AND** provider staging/output SHALL be deleted immediately after persistence with a 24-hour lifecycle backstop
