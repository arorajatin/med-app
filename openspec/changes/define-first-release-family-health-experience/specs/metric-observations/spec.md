## Purpose

Define auditable, report-linked longitudinal measurements that can be explored separately from reviewed medical insights and personal medical memory.

## ADDED Requirements

### Requirement: Store deterministic measurements automatically
The system SHALL store literal measurement observations from a successfully extracted, profile-resolved English lab report without requiring a medical-memory approval action.

#### Scenario: Publish a report measurement
- **WHEN** a resolved report produces a valid deterministic measurement
- **THEN** the system SHALL create an observation linked to the account, family profile, source report, source field or location, and extraction attempt
- **AND** the observation SHALL retain the metric identity, original value and unit, normalized value when available, reference range when available, flag when available, observation date, optional body-system classification, extraction confidence, and a validated page/block/text/polygon source reference

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

### Requirement: Keep measurements separate from documented conditions
The system SHALL treat literal lab measurements and literal conditions written in a report as separate extracted items with independent trust and review state. A measurement, reference range, or abnormal flag SHALL NOT create a condition candidate by itself.

#### Scenario: Lab values do not state a condition
- **WHEN** a lab report contains a measurement, reference range, or abnormal flag but does not literally name a condition
- **THEN** the system SHALL store eligible metric observations
- **AND** it SHALL NOT create a documented-condition candidate from those values, ranges, or flags

#### Scenario: The same report explicitly names a condition
- **WHEN** a lab report contains both a literal measurement and separate text that literally names a condition
- **THEN** the system MAY create the measurement as an `unreviewed_extracted` metric observation
- **AND** it MAY create a separate pending `documented_condition_candidate` containing the exact condition text and its own source reference

#### Scenario: Review a documented condition next to a measurement
- **WHEN** the account manager confirms or edits a documented-condition candidate from a report that also contains a metric observation
- **THEN** the condition decision SHALL NOT make the metric observation trusted medical memory
- **AND** the observation SHALL remain `unreviewed_extracted` unless it is independently corrected or excluded

#### Scenario: Correct or exclude a measurement next to a documented condition
- **WHEN** the account manager corrects or excludes a metric observation from a report that also contains a documented-condition candidate
- **THEN** the observation decision SHALL NOT confirm, edit, ignore, or otherwise change the condition candidate

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
