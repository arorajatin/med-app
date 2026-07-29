## Purpose

Define a dynamic, person-scoped Drive view that projects completed reports into month or reviewed-condition groups without duplicating source files.

## ADDED Requirements

### Requirement: Select a family profile for Drive
Drive SHALL operate on one owned family profile at a time and SHALL require profile selection when the account contains profiles in addition to `self`.

#### Scenario: Account has only self
- **WHEN** the account manager opens Drive and `self` is the only profile
- **THEN** Drive SHALL select `self` automatically

#### Scenario: Account has multiple profiles
- **WHEN** the account manager opens Drive with more than one owned profile
- **THEN** the system SHALL require or restore an explicit owned-profile selection before listing report groups

#### Scenario: Select an unavailable profile
- **WHEN** a user selects a missing or foreign profile
- **THEN** the service SHALL respond as though that profile was not found

### Requirement: Organize completed reports by month
Drive SHALL be able to project the selected profile's completed uploads into month groups and sort reports within each group by report date descending.

#### Scenario: Group reports with known dates
- **WHEN** the account manager selects month organization
- **THEN** each report with a confirmed, edited, or user-entered report date SHALL appear in that date's calendar month

#### Scenario: Report date is unavailable
- **WHEN** a completed report has no report date
- **THEN** Drive SHALL place it in an undated group
- **AND** order it by upload completion time relative to other undated reports

### Requirement: Organize completed reports by condition
Drive SHALL be able to project the selected profile's completed uploads into groups derived only from reviewed conditions linked to each report.

#### Scenario: Report has reviewed conditions
- **WHEN** a completed report is linked to one or more reviewed conditions
- **THEN** Drive SHALL include the report in each corresponding virtual condition group
- **AND** the source report SHALL remain a single private record

#### Scenario: Report has no reviewed condition
- **WHEN** a completed report has no reviewed condition
- **THEN** Drive SHALL include it in an uncategorized group

#### Scenario: Candidate condition is unreviewed
- **WHEN** a condition candidate has not been confirmed or edited
- **THEN** it SHALL NOT create a condition group

### Requirement: Reflect the current display filename
Drive SHALL show the current display filename for each report while retaining the source report's original filename outside the organization projection.

#### Scenario: Report is renamed
- **WHEN** the account manager renames an owned report
- **THEN** subsequent Drive views SHALL show the new display filename without moving or duplicating the private source file
