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
An account manager SHALL be able to record age and weight for an owned profile. Reported age SHALL be a whole number of completed years from 0 through 130 inclusive. Weight SHALL be a positive decimal entered in `kg` or `lb` whose unrounded normalized value is from 0.5 through 500 kilograms inclusive. Both values SHALL retain `reported_at`.

The profile SHALL NOT store or return a date of birth or year of birth. This restriction applies only to profile metadata and SHALL NOT prohibit extraction or retention of a source-linked date of birth as document patient evidence.

The service SHALL retain the entered weight decimal and unit unchanged and SHALL normalize pounds with the exact conversion `1 lb = 0.45359237 kg`. Conversion and range comparison SHALL use decimal arithmetic without binary floating point or intermediate rounding. Any presentation rounding SHALL NOT replace the stored original or normalized value.

The latest accepted age and weight SHALL remain visible with their reported dates. The service SHALL NOT silently increment age or derive a replacement value. It SHALL make age due for a non-blocking refresh one calendar year after `reported_at` and weight due for a non-blocking refresh six calendar months after `reported_at`. These limits and freshness states SHALL be presented only as input-quality and recency controls, not as clinical classifications.

#### Scenario: Record age in completed years
- **WHEN** the account manager supplies a whole-number age from 0 through 130 inclusive
- **THEN** the system SHALL retain that reported age and `reported_at`
- **AND** it SHALL NOT increment the stored age automatically

#### Scenario: Record weight in kilograms
- **WHEN** the account manager supplies a decimal weight in kilograms whose value is from 0.5 through 500 inclusive
- **THEN** the system SHALL retain the entered value and unit
- **AND** the normalized kilogram value SHALL equal the entered decimal without conversion loss

#### Scenario: Record weight in pounds
- **WHEN** the account manager supplies a decimal weight in pounds whose exact converted value is from 0.5 through 500 kilograms inclusive
- **THEN** the system SHALL retain the entered value and unit
- **AND** the system SHALL retain the exact decimal product of the entered value and `0.45359237` as the normalized kilogram value

#### Scenario: A reported value is due for refresh
- **WHEN** an age is at least one calendar year old or a weight is at least six calendar months old
- **THEN** the system SHALL keep the latest value visible with its reported date
- **AND** it SHALL present a non-blocking refresh prompt
- **AND** it SHALL NOT characterize the value as healthy, unhealthy, plausible, implausible, or diagnostic

#### Scenario: Record invalid health context
- **WHEN** age is fractional or outside 0 through 130 completed years, the weight unit is not `kg` or `lb`, or the exact normalized weight is outside 0.5 through 500 kilograms
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
