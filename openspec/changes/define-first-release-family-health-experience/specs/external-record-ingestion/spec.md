## Purpose

Define secure first-release intake of medical documents from authorized email and WhatsApp sources through the same private report pipeline as direct uploads.

## ADDED Requirements

### Requirement: Connect an external ingestion source
The account manager SHALL be able to authorize an email or WhatsApp ingestion source for only their account, and connector credentials and delivery metadata SHALL remain private.

#### Scenario: Connect a supported source
- **WHEN** the account manager successfully completes the supported source-authorization flow
- **THEN** the system SHALL associate the connection with that account
- **AND** the system SHALL expose a safe active connection state without returning credentials

#### Scenario: Source authorization fails
- **WHEN** authorization is rejected, cancelled, expired, or temporarily unavailable
- **THEN** the system SHALL NOT activate the connection
- **AND** the account manager SHALL receive a safe actionable status

#### Scenario: Access another account's connection
- **WHEN** a user requests connector state owned by another account
- **THEN** the service SHALL respond as though the connection was not found

### Requirement: Import supported external documents
The system SHALL accept supported PDF, image, and ordered multi-image report content delivered through an active owned email or WhatsApp source.

#### Scenario: Import one supported attachment
- **WHEN** an active source delivers a complete supported attachment
- **THEN** the system SHALL create an account-owned staged ingestion
- **AND** it SHALL retain external-source provenance without exposing message contents beyond what is required for the report workflow

#### Scenario: Import multiple pages as one report
- **WHEN** one supported delivery identifies multiple ordered images as one report
- **THEN** the system SHALL retain their order and finalize one logical document only after every page is stored

#### Scenario: Import unsupported or incomplete content
- **WHEN** an external delivery contains no usable supported report or fails before private storage completes
- **THEN** it SHALL NOT become an upload-complete Feed item
- **AND** the account manager SHALL be able to see a safe failure status

### Requirement: Apply consent and patient assignment to external intake
External ingestions SHALL use the account's recorded AI-processing consent and, because they have no direct-upload preselection, SHALL remain unassigned until patient identity resolves confidently or the account manager assigns a profile.

#### Scenario: Consent allows processing
- **WHEN** an external upload completes under accepted account AI consent
- **THEN** the system SHALL dispatch the same extraction and patient-resolution workflow used for direct uploads

#### Scenario: Consent does not allow processing
- **WHEN** an external upload completes without accepted account AI consent
- **THEN** the system SHALL store the source privately without extraction
- **AND** it SHALL require the account manager to assign an owned profile

#### Scenario: Extracted patient matches one profile
- **WHEN** extraction finds one sufficiently confident match among the account's existing profiles
- **THEN** the system SHALL resolve the imported report to that profile

#### Scenario: Extracted patient is ambiguous or unknown
- **WHEN** extraction does not find one sufficiently confident existing-profile match
- **THEN** the report SHALL remain in `needs assignment`
- **AND** it SHALL NOT publish profile metrics or memory

### Requirement: Deduplicate external deliveries
The system SHALL process replayed connector events idempotently and SHALL avoid creating duplicate active reports from the same source delivery and attachment.

#### Scenario: Delivery is replayed
- **WHEN** a connector redelivers an event with the same trusted source identity and attachment identity
- **THEN** the system SHALL acknowledge or resume the existing ingestion without creating a duplicate active report

#### Scenario: Different reports share a filename
- **WHEN** two distinct trusted source deliveries use the same attachment filename
- **THEN** the system SHALL NOT treat filename alone as proof that they are duplicates

