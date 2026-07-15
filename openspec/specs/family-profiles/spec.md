# Family Profiles Specification

## Purpose

Define the user-owned profiles that separate medical history for the user and their family members.

## Requirements

### Requirement: Create a family profile
An authenticated user SHALL be able to create a profile with a display name and relationship, plus optional date-of-birth and sex metadata.

#### Scenario: Valid profile creation
- **WHEN** an authenticated user submits a non-empty display name and relationship
- **THEN** the service SHALL create the profile under that user's ownership
- **AND** the service SHALL return the profile with generated identity and timestamps

#### Scenario: Invalid display name
- **WHEN** a user submits an empty display name
- **THEN** the service SHALL reject the request as invalid

### Requirement: Browse owned profiles
An authenticated user SHALL be able to list and retrieve only their own profiles.

#### Scenario: List profiles
- **WHEN** a user lists profiles
- **THEN** the service SHALL return only profiles owned by that user
- **AND** the service SHALL order the results by newest creation time first

#### Scenario: Retrieve a profile
- **WHEN** a user requests an owned profile by ID
- **THEN** the service SHALL return its demographic metadata

#### Scenario: Retrieve an unavailable profile
- **WHEN** a user requests a missing profile or a profile owned by someone else
- **THEN** the service SHALL return HTTP 404
