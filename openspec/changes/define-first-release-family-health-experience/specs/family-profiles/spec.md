## ADDED Requirements

### Requirement: Automatically create the self profile
The system SHALL create exactly one account-owned `self` profile during first-run onboarding.

#### Scenario: New account begins onboarding
- **WHEN** a verified account begins onboarding without an existing `self` profile
- **THEN** the system SHALL create one profile with relationship `self`

#### Scenario: Onboarding is repeated
- **WHEN** onboarding resumes or is retried for an account that already has a `self` profile
- **THEN** the system SHALL reuse that profile rather than create a duplicate

### Requirement: Capture unit-aware profile health context
An account manager SHALL be able to record age and weight for an owned profile, with weight accepted in pounds or kilograms and both values retaining their reported date.

#### Scenario: Record weight in kilograms
- **WHEN** the account manager supplies a valid weight in kilograms
- **THEN** the system SHALL retain the entered value and unit
- **AND** the system SHALL retain a normalized weight value for consistent comparison

#### Scenario: Record weight in pounds
- **WHEN** the account manager supplies a valid weight in pounds
- **THEN** the system SHALL retain the entered value and unit
- **AND** the system SHALL retain a normalized weight value for consistent comparison

#### Scenario: Record invalid health context
- **WHEN** age or weight is outside the accepted product range
- **THEN** the system SHALL reject that value as invalid

### Requirement: Manage family profiles under one account
The account manager SHALL be able to create and browse multiple family profiles while every profile remains owned by the same account.

#### Scenario: Add a family member
- **WHEN** the account manager supplies a display name and relationship for a new family member
- **THEN** the system SHALL create the family profile under that account

#### Scenario: Browse the family space
- **WHEN** the account manager lists family profiles
- **THEN** the system SHALL return `self` and all other profiles owned by the account
- **AND** no profile SHALL imply a separate login in the first release

