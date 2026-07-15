# Medical Records Specification

## Purpose

Define creation, browsing, consent, and private file upload behavior for medical records.

## Requirements

### Requirement: Manage records within an owned profile
An authenticated user SHALL be able to create, list, and retrieve medical records within a profile they own.

#### Scenario: Create a record
- **WHEN** a user creates a record with an owned profile, title, and AI-processing consent choice
- **THEN** the service SHALL store the record under the user and profile
- **AND** the initial record status SHALL be `uploaded`

#### Scenario: List profile records
- **WHEN** a user lists records for an owned profile
- **THEN** the service SHALL return only that user's records for the profile
- **AND** the service SHALL order the records by newest creation time first

#### Scenario: Use an unavailable profile
- **WHEN** a user creates or lists records using a missing or unowned profile
- **THEN** the service SHALL return HTTP 404

### Requirement: Private file upload
The service SHALL accept a file for an owned record and store it below the configured private storage root without returning its storage path.

#### Scenario: Successful upload
- **WHEN** a user uploads a file within the configured size limit to an owned record
- **THEN** the service SHALL persist the file under user, profile, and record-specific storage
- **AND** the response SHALL expose file metadata but not the internal storage path

#### Scenario: Oversized upload
- **WHEN** an upload exceeds the configured maximum byte count
- **THEN** the service SHALL delete the partial file
- **AND** the service SHALL return HTTP 413

### Requirement: Explicit AI-processing consent
The service SHALL create an extraction job for an uploaded file only when the record has AI-processing consent.

#### Scenario: Upload with consent
- **WHEN** a file is uploaded to a record whose AI-processing consent is enabled
- **THEN** the service SHALL create an extraction job for that file

#### Scenario: Upload without consent
- **WHEN** a file is uploaded to a record whose AI-processing consent is disabled
- **THEN** the service SHALL store the file without creating an extraction job
