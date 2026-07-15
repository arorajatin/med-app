## ADDED Requirements

### Requirement: Production extraction provider selection
The service SHALL select an implemented extraction adapter from validated environment configuration and SHALL restrict the mock adapter to local or test use.

#### Scenario: Select a supported production provider
- **WHEN** production starts with complete configuration for a supported provider
- **THEN** extraction jobs SHALL use that provider through the normalized extractor contract

#### Scenario: Select an unsupported provider
- **WHEN** production configuration names an unknown or incomplete provider
- **THEN** the service SHALL fail closed before a medical document is sent or processed

#### Scenario: Run local tests
- **WHEN** the service runs in a local or test environment with the mock provider selected
- **THEN** deterministic mock extraction SHALL remain available

### Requirement: Real medical document processing
The production adapter SHALL process each supported medical document into reviewable fields without treating provider output as confirmed fact.

#### Scenario: Extract a supported document
- **WHEN** a consented supported file is processed successfully
- **THEN** the adapter SHALL return the detected document type and structured fields through the existing normalized contract
- **AND** fields SHALL include confidence and source context when the provider supplies them
- **AND** every field SHALL remain pending until user review

#### Scenario: Process an unsupported or unreadable document
- **WHEN** the provider cannot reliably process the file type or contents
- **THEN** the job SHALL fail with a safe actionable reason
- **AND** no partial provider output SHALL enter medical memory

### Requirement: Atomic extraction attempt
An extraction attempt SHALL publish either one complete reviewable result set or no new result set.

#### Scenario: Provider fails after partial work
- **WHEN** the provider or normalization logic fails before the attempt completes
- **THEN** newly staged raw output and fields from that attempt SHALL NOT become reviewable
- **AND** previously reviewed fields from earlier attempts SHALL remain unchanged

#### Scenario: Provider succeeds
- **WHEN** extraction and normalization complete successfully
- **THEN** the raw output, structured fields, job status, and record status SHALL commit consistently

### Requirement: Privacy-safe provider operations
The production extraction path SHALL transmit and retain medical data only as required by the configured provider agreement and SHALL avoid emitting document contents in application logs.

#### Scenario: Observe a job
- **WHEN** the service records extraction telemetry or an error
- **THEN** logs SHALL use job identifiers and redacted metadata instead of raw file contents or extracted medical values

#### Scenario: Send a document to a provider
- **WHEN** a consented document is submitted for extraction
- **THEN** the selected provider configuration SHALL satisfy the project's approved data handling and retention policy
