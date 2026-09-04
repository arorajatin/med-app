# Family Profiles Specification

## Purpose

Define the user-owned profiles that separate medical history for the user and their family members.

## Requirements

### Requirement: Create a family profile
An authenticated user SHALL be able to create a profile with a display name and relationship, plus optional sex metadata.

#### Scenario: Valid profile creation
- **WHEN** an authenticated user submits a non-empty display name and relationship
- **THEN** the service SHALL create the profile under that user's ownership
- **AND** the service SHALL return the profile with generated identity and timestamps
- **AND** the returned profile SHALL NOT contain a date of birth

#### Scenario: Invalid display name
- **WHEN** a user submits an empty display name
- **THEN** the service SHALL reject the request as invalid

#### Scenario: A second self profile is requested
- **WHEN** a user creates a profile with relationship `self` while the account already has one
- **THEN** the service SHALL reject the request as a conflict

### Requirement: Establish the one self profile through onboarding
An account SHALL own exactly one profile with relationship `self`. The onboarding self-profile
request SHALL create that profile when it is absent and update the existing one when it is present,
so a resumed or retried onboarding never produces a duplicate.

#### Scenario: First-run onboarding
- **WHEN** an account submits its self profile for the first time
- **THEN** the service SHALL create one profile with relationship `self`

#### Scenario: Onboarding is repeated
- **WHEN** an account submits its self profile again
- **THEN** the service SHALL return the same profile with the submitted display name and sex
- **AND** the account SHALL still own exactly one `self` profile

### Requirement: Record answered onboarding declarations
A profile SHALL retain when the account manager last declared its current conditions and its current
medications, so an empty declaration is distinguishable from an unanswered one.

#### Scenario: Declare no current conditions
- **WHEN** the account manager declares an empty set of current conditions for an owned profile
- **THEN** the service SHALL record the declaration time
- **AND** the service SHALL treat that onboarding step as answered

#### Scenario: Declare for an unavailable profile
- **WHEN** a user declares conditions or medications for a missing profile or one owned by someone else
- **THEN** the service SHALL return HTTP 404

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
