## Purpose

Define a dynamic Drive (Folder) view that projects completed, assigned reports for All Family or one family member into month or reviewed-condition groups without duplicating source files.

## ADDED Requirements

### Requirement: Select All Family or one family member for Drive
Drive SHALL provide the same All Family and owned-family-member choices as Feed. All Family SHALL be the default even when `self` is the only profile.

#### Scenario: Open All Family
- **WHEN** the account manager opens Drive
- **THEN** Drive SHALL group completed reports with resolved assignment across all owned family profiles
- **AND** each report SHALL identify its assigned family member

#### Scenario: Select a family member
- **WHEN** the account manager selects an owned family member
- **THEN** Drive SHALL group only completed reports whose assignment is resolved to that person
- **AND** switching the family view SHALL retain the month or condition organization choice and clear the previous group's results

#### Scenario: Upload is incomplete or assignment is unresolved
- **WHEN** an upload is incomplete or lacks resolved assignment
- **THEN** it SHALL NOT appear in either All Family or an individual member's Drive
- **AND** completed uploads awaiting assignment SHALL remain accessible in Feed's All Family view

#### Scenario: Select an unavailable profile
- **WHEN** a user selects a missing or foreign profile
- **THEN** the service SHALL respond as though that profile was not found

### Requirement: Organize completed reports by month
Drive SHALL be able to project completed, assigned uploads in the selected family view into month groups and sort reports within each group by report date descending.

#### Scenario: Group reports with known dates
- **WHEN** the account manager selects month organization
- **THEN** each report with a confirmed, edited, or user-entered report date SHALL appear in that date's calendar month

#### Scenario: Report date is unavailable
- **WHEN** a completed report has no report date
- **THEN** Drive SHALL place it in an undated group
- **AND** order it by upload completion time relative to other undated reports

### Requirement: Organize completed reports by condition
Drive SHALL be able to project completed, assigned uploads in the selected family view into groups derived only from trusted condition links. A trusted condition link SHALL use either a user-attested condition explicitly linked to the report or a confirmed or edited `documented_condition_candidate` extracted from that report. Drive SHALL NOT infer a condition link from medication details, lab observations, symptoms, or general medical knowledge.

#### Scenario: Report has trusted condition links
- **WHEN** a completed report is linked to one or more user-attested conditions or confirmed or edited documented-condition candidates
- **THEN** Drive SHALL include the report in each corresponding virtual condition group
- **AND** the source report SHALL remain a single private record

#### Scenario: Report has no trusted condition link
- **WHEN** a completed report has no trusted condition link
- **THEN** Drive SHALL include it in an uncategorized group

#### Scenario: Documented condition is pending or ignored
- **WHEN** a documented-condition candidate is pending or ignored
- **THEN** it SHALL NOT create a condition group

#### Scenario: Report evidence only implies a condition
- **WHEN** medication details, lab observations, symptoms, or general medical knowledge could be associated with a condition but the report has no trusted condition link
- **THEN** Drive SHALL NOT create that condition group
- **AND** the report SHALL remain in the uncategorized group for condition organization

### Requirement: Reflect the current display filename
Drive SHALL show the current display filename for each report while retaining the source report's original filename outside the organization projection.

#### Scenario: Report is renamed
- **WHEN** the account manager renames an owned report
- **THEN** subsequent Drive views SHALL show the new display filename without moving or duplicating the private source file
