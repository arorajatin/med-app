## Purpose

Define auditable, report-linked longitudinal measurements that can be explored separately from reviewed medical insights and personal medical memory.

## ADDED Requirements

### Requirement: Store deterministic measurements automatically
The system SHALL store deterministic measurement observations from a successfully extracted, profile-resolved report without requiring a medical-memory approval action.

#### Scenario: Publish a report measurement
- **WHEN** a resolved report produces a valid deterministic measurement
- **THEN** the system SHALL create an observation linked to the account, family profile, source report, source field or location, and extraction attempt
- **AND** the observation SHALL retain the metric identity, original value and unit, normalized value when available, reference range when available, observation date, optional body-system classification, and extraction confidence

#### Scenario: Retry extraction
- **WHEN** the same extraction attempt is retried or superseded
- **THEN** the system SHALL NOT present duplicate active observations for the same source measurement
- **AND** prior observation provenance SHALL remain auditable

### Requirement: Keep observations outside trusted memory
Automatically extracted observations SHALL remain explicitly source-linked and unreviewed and SHALL NOT become reviewed medical-memory facts or personal-memory Chat evidence merely because they were stored.

#### Scenario: Build reviewed memory
- **WHEN** the system rebuilds medical memory for a report
- **THEN** it SHALL exclude automatic measurement observations

#### Scenario: Ground a personal-memory answer
- **WHEN** Chat retrieves reviewed personal memory
- **THEN** it SHALL exclude unreviewed metric observations from that evidence set

### Requirement: Correct or exclude an observation
The account manager SHALL be able to correct or exclude an observation while the system retains the original extracted value and source provenance.

#### Scenario: Correct an extracted observation
- **WHEN** the account manager supplies a valid correction for an owned observation
- **THEN** the corrected value SHALL become the active value
- **AND** the original extracted value and correction audit SHALL remain available

#### Scenario: Exclude an observation
- **WHEN** the account manager marks an owned observation unusable
- **THEN** it SHALL be excluded from active longitudinal results without deleting its audit provenance

### Requirement: Retrieve a longitudinal metric series
The account manager SHALL be able to retrieve observations for one owned family profile and metric, optionally filtered by a known body-system classification, in observation-date order.

#### Scenario: Read a metric series
- **WHEN** the account manager requests an owned profile's metric series
- **THEN** the system SHALL return active observations ordered by observation date
- **AND** every point SHALL retain a reference to its source report

#### Scenario: Read another account's series
- **WHEN** a user requests a metric series for a profile they do not own
- **THEN** the system SHALL respond as though that profile was not found
