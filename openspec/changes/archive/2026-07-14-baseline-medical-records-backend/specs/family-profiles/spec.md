## ADDED Requirements

### Requirement: Create a family profile
An authenticated user SHALL be able to create an owned profile with relationship and optional demographic metadata.

#### Scenario: Valid creation
- **WHEN** a user submits a valid display name and relationship
- **THEN** the service SHALL create and return the profile under that user's ownership

### Requirement: Browse owned profiles
An authenticated user SHALL be able to list and retrieve only their own profiles.

#### Scenario: List profiles
- **WHEN** a user lists profiles
- **THEN** the service SHALL return only that user's profiles ordered newest first

#### Scenario: Unavailable profile
- **WHEN** a user requests a missing or unowned profile
- **THEN** the service SHALL return HTTP 404
