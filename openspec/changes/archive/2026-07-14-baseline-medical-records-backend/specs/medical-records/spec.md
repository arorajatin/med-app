## ADDED Requirements

### Requirement: Manage records within an owned profile
An authenticated user SHALL be able to create, list, and retrieve records within a profile they own.

#### Scenario: Create a record
- **WHEN** a user creates a record for an owned profile
- **THEN** the service SHALL store the record with its title and AI-processing consent choice

#### Scenario: List records
- **WHEN** a user lists records for an owned profile
- **THEN** the service SHALL return only that user's records for the profile

### Requirement: Private file upload
The service SHALL store an uploaded record file below the configured private storage root without returning its storage path.

#### Scenario: Successful upload
- **WHEN** a user uploads a file within the configured size limit
- **THEN** the service SHALL persist it under owner-specific storage and return only safe metadata

#### Scenario: Oversized upload
- **WHEN** an upload exceeds the configured byte limit
- **THEN** the service SHALL remove the partial file and return HTTP 413

### Requirement: Explicit AI-processing consent
The service SHALL create an extraction job only for uploads whose record has AI-processing consent.

#### Scenario: Upload with consent
- **WHEN** a file is uploaded to a consented record
- **THEN** the service SHALL create an extraction job

#### Scenario: Upload without consent
- **WHEN** a file is uploaded to a record without consent
- **THEN** the service SHALL store the file without creating an extraction job
