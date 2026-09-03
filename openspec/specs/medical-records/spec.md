# Medical Records Specification

## Purpose

Define account-level AI-processing consent, staged logical-document ingestion, explicit patient
assignment, and private file storage for medical records.

## Requirements

### Requirement: Account-level AI-processing consent
The service SHALL record versioned consent evidence for an account and SHALL snapshot the accepted
consent on every ingestion. Accepted consent SHALL be a precondition for uploading, because every
capability depends on AI processing, and the service SHALL NOT prompt for consent again for each
document.

#### Scenario: Accept consent
- **WHEN** an account manager submits a policy version and accepted scope
- **THEN** the service SHALL store consent evidence with the accepting identity and acceptance time

#### Scenario: Ingest with accepted consent
- **WHEN** a document is uploaded and the account has accepted consent
- **THEN** the ingestion SHALL reference the most recently accepted consent evidence
- **AND** the service SHALL create an extraction job for that ingestion

#### Scenario: Ingest without accepted consent
- **WHEN** a document is uploaded and the account has no accepted consent
- **THEN** the service SHALL reject the upload with HTTP 403
- **AND** the service SHALL NOT store the ingestion, its parts, or any file content

### Requirement: Staged logical document ingestion
The service SHALL accept a logical document as one to twenty ordered immutable source parts through
a route that stamps an immutable `direct_file` or `camera` source channel. Supported input SHALL be
limited to PDF, JPEG, and PNG, and camera capture SHALL accept only images.

#### Scenario: Upload a supported document
- **WHEN** an authenticated owner uploads one or more supported files to the direct-file route
- **THEN** the service SHALL create an ingestion with the `direct_file` source channel
- **AND** each part SHALL record its ordinal, original filename, detected media type, byte size, content digest, and private storage identity
- **AND** the ingestion's upload state SHALL become `complete` with a completion time

#### Scenario: Capture from the camera
- **WHEN** an owner uploads through the camera route
- **THEN** the service SHALL stamp the `camera` source channel
- **AND** it SHALL reject any part that is not a JPEG or PNG image

#### Scenario: Unsupported media type
- **WHEN** any submitted part is not an accepted media type for its route
- **THEN** the service SHALL return HTTP 415

#### Scenario: Too many parts
- **WHEN** an upload contains no parts or more than twenty parts
- **THEN** the service SHALL return HTTP 413

#### Scenario: Oversized upload
- **WHEN** a logical document exceeds the configured maximum byte count, or an image part exceeds the image byte ceiling
- **THEN** the service SHALL delete every object already stored for that upload
- **AND** the service SHALL return HTTP 413

#### Scenario: Private storage is never disclosed
- **WHEN** the service returns an ingestion or its parts
- **THEN** the response SHALL expose part metadata but SHALL NOT expose the storage bucket or object key

### Requirement: Enable each release slice independently
Web ingestion, extraction, observation publication, Feed and Drive, and Chat SHALL each be
controlled by their own setting, every one of which SHALL default to disabled. A disabled slice SHALL
be indistinguishable from an absent one, and disabling a slice SHALL NOT disable another.

#### Scenario: Request a disabled slice
- **WHEN** an authenticated owner requests a route belonging to a disabled slice
- **THEN** the service SHALL return HTTP 404
- **AND** it SHALL NOT create or change any private row or stored object

#### Scenario: Authentication is still checked first
- **WHEN** an unauthenticated request reaches a route belonging to a disabled slice
- **THEN** the service SHALL return HTTP 401, so the response never reveals which slices are enabled

#### Scenario: Ingest while extraction is disabled
- **WHEN** an owner uploads a supported document while web ingestion is enabled and extraction is disabled
- **THEN** the service SHALL store the logical document and complete its upload
- **AND** it SHALL create no extraction job, leaving the ingestion's extraction state `not_requested`

#### Scenario: Extract while observations are disabled
- **WHEN** an extraction attempt succeeds while observation publication is disabled
- **THEN** the service SHALL persist its other normalized output
- **AND** it SHALL publish no metric observation

### Requirement: Explicit patient assignment
An ingestion SHALL carry a provisional profile selection that does not by itself resolve the
patient. A medical record SHALL be created only when the ingestion resolves to a profile the account
owns, and derived extraction rows SHALL be attached to that record and profile on resolution.

#### Scenario: Resolution is still pending
- **WHEN** extraction completes and the ingestion has no resolved profile
- **THEN** the ingestion's assignment state SHALL become `needs_assignment`
- **AND** the service SHALL NOT create a medical record

#### Scenario: Resolve an ingestion to an owned profile
- **WHEN** an owner assigns an owned ingestion to an owned profile
- **THEN** the service SHALL create the medical record for that ingestion exactly once
- **AND** the assignment state SHALL become `resolved` with a resolution time and resolving identity
- **AND** the service SHALL attach that ingestion's metadata candidates, metric observations, and memory candidates to the record and profile

#### Scenario: Assign using an unavailable profile or ingestion
- **WHEN** an owner assigns using a missing or unowned ingestion or profile
- **THEN** the service SHALL return HTTP 404

### Requirement: Browse records within an owned profile
An authenticated owner SHALL be able to list and retrieve the medical records of a profile they own.

#### Scenario: List profile records
- **WHEN** an owner lists records for an owned profile
- **THEN** the service SHALL return only that account's records for the profile
- **AND** it SHALL order the records by newest creation time first
- **AND** it SHALL omit records whose ingestion has been tombstoned

#### Scenario: Use an unavailable profile or record
- **WHEN** an owner lists records for a missing or unowned profile, or retrieves a missing or unowned record
- **THEN** the service SHALL return HTTP 404
