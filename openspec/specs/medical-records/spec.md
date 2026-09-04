# Medical Records Specification

## Purpose

Define staged logical-document ingestion, explicit patient assignment, and private file storage for
medical records.

## Requirements

### Requirement: Account-authorized AI processing
Creating an application account SHALL authorize the AI processing required by the product. The
service SHALL NOT store a separate application consent record or repeat that choice on an ingestion
or medical record.

#### Scenario: Ingest an account-owned document
- **WHEN** an authenticated account uploads a document
- **THEN** the service SHALL create an extraction job for that ingestion
- **AND** the ingestion SHALL NOT store a separate AI-processing consent value or reference

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
