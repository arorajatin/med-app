## MODIFIED Requirements

### Requirement: Explicit extraction trust classes
The normalized production contract SHALL classify each supported item as `patient_evidence`, `document_metadata_candidate`, `metric_observation`, or `memory_candidate` and SHALL apply the corresponding publication boundary. A `memory_candidate` MAY use subtype `documented_condition_candidate` only when the cited prescription or lab-report text literally names the condition. The adapter SHALL NOT infer a condition or diagnosis from medication details, lab observations, symptoms, or general medical knowledge.

#### Scenario: Extract patient evidence
- **WHEN** a document contains a literal patient name and may also contain a patient identifier or date of birth
- **THEN** the adapter SHALL return source-linked `patient_evidence` for account-local assignment only
- **AND** patient evidence MAY retain the source-linked date of birth when it is present
- **AND** the date of birth SHALL NOT be copied to a profile or used for automatic assignment
- **AND** the evidence SHALL remain untrusted medical data

#### Scenario: Extract document metadata
- **WHEN** a document supports a report date, issuer or provider, type, or display-name suggestion
- **THEN** the adapter SHALL return a source-linked `document_metadata_candidate`
- **AND** that candidate SHALL require review before becoming trusted metadata

#### Scenario: Extract a lab observation
- **WHEN** a lab report supports an analyte, decimal or categorical value, unit, reference range, flag, or observation date
- **THEN** the adapter SHALL return a source-linked `metric_observation` containing only literal supported values
- **AND** the observation MAY publish only after profile assignment resolves
- **AND** a published observation SHALL remain `unreviewed_extracted`, correctable, and separate from trusted memory

#### Scenario: Extract a prescription candidate
- **WHEN** a prescription supports a medication name, strength, dosage form, dose, route, frequency, duration, or instruction
- **THEN** the adapter SHALL return a source-linked `memory_candidate`
- **AND** that candidate SHALL remain pending until explicitly reviewed

#### Scenario: Extract a condition written in the document
- **WHEN** a prescription or lab report contains text that literally names a condition
- **THEN** the adapter MAY return a source-linked `memory_candidate` with subtype `documented_condition_candidate`
- **AND** the candidate SHALL contain the exact condition text written in the document and a source reference to the span that names it
- **AND** that candidate SHALL remain pending until explicitly confirmed, edited, or ignored

#### Scenario: Medication or lab evidence does not name a condition
- **WHEN** a document contains medication details, lab measurements, reference ranges, or abnormal flags but does not literally name a condition
- **THEN** the adapter SHALL NOT create a documented-condition candidate from those details

#### Scenario: Symptoms or general knowledge do not name a condition
- **WHEN** a document contains symptoms or could be associated with a condition through general medical knowledge but does not literally name that condition
- **THEN** the adapter SHALL NOT create a documented-condition candidate from those symptoms or associations

#### Scenario: A value is absent or interpretive
- **WHEN** a schema value is unavailable from the cited document text or would require diagnosis or clinical interpretation
- **THEN** the adapter SHALL omit the value rather than infer or fabricate it

## ADDED Requirements

### Requirement: Fixed production extraction pipeline
The service SHALL use `pdfplumber`, Amazon Textract, and Amazon Bedrock Mistral Large 3 as the only V1 production extraction pipeline and SHALL fail closed when its privacy or regional configuration is invalid.

#### Scenario: Start with valid production configuration
- **WHEN** production starts with Textract and Bedrock configured in `ap-south-1`, Bedrock model ID `mistral.mistral-large-3-675b-instruct`, and approved zero-data-retention controls
- **THEN** extraction jobs SHALL use those components through the normalized extractor contract
- **AND** cross-region inference and alternate-provider fallback SHALL remain disabled

#### Scenario: Start with invalid production configuration
- **WHEN** a configured region, model, zero-data-retention control, credential, or required staging resource does not satisfy the production contract
- **THEN** production extraction SHALL fail closed before any medical document is submitted

#### Scenario: Run local tests
- **WHEN** the service runs in an explicitly allowed local or test environment with the mock provider selected
- **THEN** deterministic mock extraction SHALL remain available
- **AND** production SHALL never fall back to the mock provider

### Requirement: Bounded logical-document inputs
The production adapter SHALL process one immutable logical document per attempt and SHALL support only unencrypted PDF, JPEG, and PNG input representing an English-language lab report or prescription that completed through an authenticated `direct_file` or `camera` web-upload route.

#### Scenario: Accept a supported logical document
- **WHEN** a consented input is one PDF, one image, or an ordered JPEG/PNG image set within all product limits
- **THEN** the adapter SHALL preserve source-part order and logical page numbering for one extraction attempt

#### Scenario: Receive input outside authenticated web upload
- **WHEN** a logical document does not carry immutable `direct_file` or `camera` provenance stamped by an authenticated web-upload route
- **THEN** the production adapter SHALL reject it before provider submission

#### Scenario: Enforce product limits
- **WHEN** a logical document exceeds 15,000,000 bytes, 20 pages or parts, 10,000,000 bytes for an image, or 10,000 pixels for an image dimension
- **THEN** the attempt SHALL fail before provider submission with a safe terminal reason
- **AND** no normalized clinical output SHALL be published

#### Scenario: Receive an unsupported input
- **WHEN** an input is encrypted, corrupt, in another file format or language, or is not a lab report or prescription
- **THEN** the attempt SHALL end with a safe terminal reason such as `unsupported_document_type`
- **AND** the service SHALL NOT publish a partial extraction

### Requirement: Deterministic whole-document routing
The adapter SHALL select one processing method for the complete logical document and SHALL retain the selected method and routing reason with the attempt.

#### Scenario: Use native PDF text
- **WHEN** every nonblank PDF page opens successfully, contains at least 20 positioned word tokens, has at least 99% printable extracted characters, keeps every token coordinate inside its page bounds, and has no raster image covering 50% or more of the page
- **THEN** `pdfplumber` SHALL produce the provider-neutral text and layout stream
- **AND** the attempt SHALL record `processing_method = native_text`

#### Scenario: Fall back for one deficient PDF page
- **WHEN** any nonblank page of an otherwise valid PDF fails any native-text condition
- **THEN** the complete PDF SHALL be processed through Textract document analysis
- **AND** the adapter SHALL NOT combine native and Textract coordinate systems in that attempt
- **AND** the attempt SHALL record `processing_method = textract_ocr` and the failed gate condition

#### Scenario: Process images
- **WHEN** the logical document is one image or an ordered image set
- **THEN** every part SHALL be processed through Textract in source-part order
- **AND** the attempt SHALL record `processing_method = textract_ocr`

### Requirement: Source-preserving OCR and structured extraction
The adapter SHALL convert native text or Textract output into a provider-neutral layout stream and SHALL accept model output only when every normalized item is supported by that stream.

#### Scenario: Process a PDF through Textract
- **WHEN** a PDF requires OCR
- **THEN** the adapter SHALL use asynchronous Textract document analysis with layout, tables, and forms
- **AND** Textract input, notification, queue, output, and KMS resources SHALL remain in `ap-south-1`
- **AND** Textract results SHALL use a customer-controlled, KMS-encrypted `OutputConfig` location

#### Scenario: Invoke structured extraction
- **WHEN** the provider-neutral layout stream is complete
- **THEN** Mistral Large 3 SHALL receive the text, layout, stable source IDs, and schema instructions
- **AND** it SHALL NOT receive account profiles, aliases, authentication email, or other unrelated account or patient-matching context
- **AND** the adapter SHALL require schema-valid output

#### Scenario: Validate a source reference
- **WHEN** a normalized item is staged
- **THEN** it SHALL contain at least one `SourceReference` with source-part ID, logical page, native word IDs or Textract block IDs, supporting text span, and normalized bounding polygon
- **AND** every ID, page, span, and polygon SHALL resolve against the persisted layout for that attempt

#### Scenario: Reject an invalid citation
- **WHEN** any normalized item cites missing, mismatched, or fabricated source content
- **THEN** the complete attempt SHALL fail terminally
- **AND** none of that attempt's otherwise valid items SHALL be published

### Requirement: Exact account-local assignment boundary
Automatic profile assignment SHALL use source-linked patient evidence only after extraction and SHALL match only profiles and explicit aliases owned by the same account.

#### Scenario: Resolve one exact match
- **WHEN** Unicode NFKC normalization, whitespace normalization, and case folding produce exactly one full-name or explicit-alias match
- **THEN** the logical document MAY resolve automatically to that owned profile

#### Scenario: Evidence is ambiguous or unmatched
- **WHEN** there is no exact match or more than one exact match
- **THEN** assignment SHALL become `needs_assignment`
- **AND** no profile-scoped observation or memory candidate SHALL publish automatically

#### Scenario: A model supplies identity confidence
- **WHEN** patient evidence includes a provider confidence value
- **THEN** confidence alone SHALL NOT permit fuzzy, phonetic, cross-account, or otherwise non-exact assignment

### Requirement: Atomic extraction attempts
An extraction attempt SHALL publish one complete validated result set or no new result set and SHALL preserve output from previously committed attempts.

#### Scenario: Extraction fails after partial work
- **WHEN** reading, OCR, model invocation, normalization, source-reference validation, or commit fails before the attempt completes
- **THEN** staged raw output and normalized items from that execution SHALL NOT become reviewable or profile-scoped
- **AND** previously committed or reviewed output SHALL remain unchanged

#### Scenario: Extraction succeeds
- **WHEN** component processing and all validation complete successfully
- **THEN** native or Textract output, raw Bedrock output, normalized items, source references, component provenance, job status, and record status SHALL commit consistently

#### Scenario: Retry a transient provider failure
- **WHEN** a numbered attempt encounters a queue-policy transient failure such as a provider/network timeout, throttle or HTTP 429, temporary provider/AWS failure, transient S3/SQS/SNS/KMS transport failure, interrupted claim, retryable Textract failure, or bounded callback timeout
- **THEN** the queue worker MAY create at most three total numbered attempts using jittered delays based on 30 seconds and two minutes
- **AND** every attempt SHALL use the same immutable logical-document manifest

#### Scenario: Encounter a permanent failure
- **WHEN** input, document family, schema, source references, region, or zero-data-retention controls are invalid, or transient retries are exhausted
- **THEN** the attempt SHALL end terminally without automatic fallback to another provider, region, or the mock

### Requirement: Privacy-safe retention and operations
The production path SHALL require the governing accepted account-level extraction-consent snapshot without another prompt for each document or condition candidate, process and stage medical content only in `ap-south-1`, and restrict retained content to the report's approved audit lifecycle.

#### Scenario: Consent is absent
- **WHEN** a logical document lacks valid AI-processing consent
- **THEN** the service SHALL NOT invoke `pdfplumber`, Textract, or Bedrock for extraction

#### Scenario: Account consent already governs the upload
- **WHEN** an authenticated web upload references an accepted account-level extraction-consent snapshot
- **THEN** the service SHALL treat that snapshot as the governing consent for extraction dispatch
- **AND** it SHALL NOT ask for another consent choice for the document or any documented-condition candidate it produces

#### Scenario: Retain a successful result
- **WHEN** an extraction attempt commits successfully
- **THEN** native or Textract layout and raw Bedrock output SHALL be encrypted and operationally restricted until the source report is deleted
- **AND** report deletion SHALL remove raw output, normalized results, and source-reference material

#### Scenario: Clean up provider staging
- **WHEN** Textract input and output have been persisted into approved application storage or the attempt is rejected
- **THEN** temporary S3 objects SHALL be deleted promptly
- **AND** a 24-hour lifecycle policy SHALL provide a deletion backstop

#### Scenario: Invoke Bedrock
- **WHEN** a consented layout stream is sent to Mistral Large 3
- **THEN** the invocation SHALL use `data_retention_mode: none`
- **AND** IAM or SCP policy SHALL prevent relaxing the zero-data-retention requirement

#### Scenario: Observe an attempt
- **WHEN** the service records telemetry, queue metadata, or an error
- **THEN** it SHALL use internal identifiers, component and method names, timings, counts, configuration versions or hashes, request IDs, and safe failure codes
- **AND** it SHALL NOT emit file/document hashes, file bytes, document text, source spans, raw responses, extracted values, patient identifiers, or credentials

### Requirement: Precision-gated production rollout
The production feature SHALL remain disabled until the approved, versioned de-identified English fixture corpus satisfies all safety and provenance gates.

#### Scenario: Evaluate the candidate release
- **WHEN** the pipeline is evaluated against digital PDFs, scans, photographs, multi-page lab reports, ordered image sets, and prescriptions
- **THEN** it SHALL produce zero false automatic profile assignments
- **AND** published lab `(metric name, value, unit, source page)` tuples SHALL have at least 99.5% exact precision
- **AND** source-page attribution SHALL be at least 99.5% correct
- **AND** published observations SHALL include zero unanchored or fabricated items
- **AND** review-required prescription memory candidates SHALL have at least 95% precision
- **AND** documented-condition candidates SHALL include zero candidates whose cited source text does not literally name the extracted condition

#### Scenario: A quality or privacy gate fails
- **WHEN** any quality threshold, India-residency check, provider privacy approval, Bedrock ZDR check, migration check, or RLS check fails
- **THEN** the production extraction feature SHALL remain disabled
