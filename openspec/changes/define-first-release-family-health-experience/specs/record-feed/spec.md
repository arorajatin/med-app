## Purpose

Define the chronological Feed for browsing completed web-uploaded reports in All Family or an individual family-member view.

## ADDED Requirements

### Requirement: Aggregate completed uploads across the family
The Feed SHALL default to All Family and include completed document uploads submitted through authenticated file-selection or camera routes and owned by the account across all managed family profiles.

#### Scenario: Browse the family Feed
- **WHEN** the account manager opens Feed
- **THEN** the system SHALL return completed uploads for `self` and every other owned family profile
- **AND** every item SHALL identify its assigned profile or pending patient-match / `needs assignment` state, immutable `direct_file` or `camera` source channel, safe source label, display filename, and current processing state

#### Scenario: Upload is incomplete
- **WHEN** a staged upload has not reached upload-complete state
- **THEN** it SHALL NOT appear in Feed

#### Scenario: Extraction is still processing
- **WHEN** an upload is complete but extraction or review is not complete
- **THEN** it SHALL remain eligible for Feed
- **AND** Feed SHALL expose its current processing or assignment state

#### Scenario: Profile assignment is unresolved
- **WHEN** upload is complete but profile assignment needs account-manager resolution
- **THEN** All Family SHALL include the account-owned item with an attention-required state
- **AND** the item SHALL remain excluded from individual member views, Drive, metrics, memory, and Chat

### Requirement: Select All Family or one family member
Feed SHALL provide the same All Family and owned-family-member choices as Drive. All Family SHALL be the default even when `self` is the only profile.

#### Scenario: Select a family member
- **WHEN** the account manager selects an owned family member
- **THEN** Feed SHALL include only eligible uploads whose assignment is resolved to that person
- **AND** a provisional upload selection SHALL NOT place a report in that person's Feed
- **AND** an empty member view SHALL explain that uploads awaiting assignment are available in All Family

#### Scenario: Change the family view
- **WHEN** the account manager switches between All Family and a family member or between members
- **THEN** Feed SHALL reset pagination, preserve the selected date ordering, and ignore late responses from the prior view

#### Scenario: Select an unavailable profile
- **WHEN** a user requests a missing or foreign family profile
- **THEN** the service SHALL respond as though that profile was not found

### Requirement: Order Feed by the selected date mode
The account manager SHALL be able to order Feed newest-first by upload date or by report date.

#### Scenario: Order by upload date
- **WHEN** the account manager selects upload-date ordering
- **THEN** Feed SHALL order completed documents by upload completion time descending
- **AND** ties SHALL be resolved by a stable unique identifier

#### Scenario: Order by report date
- **WHEN** the account manager selects report-date ordering
- **THEN** Feed SHALL order documents with a confirmed, edited, or user-entered report date by report date descending
- **AND** documents without a report date SHALL appear after dated documents, ordered by upload completion time descending
- **AND** remaining ties SHALL be resolved by upload completion time and a stable unique identifier

### Requirement: Page Feed results consistently
Feed SHALL provide stable pagination without returning another account's documents.

#### Scenario: Request another page
- **WHEN** the account manager follows a valid Feed cursor without changing the ordering mode or family view
- **THEN** the service SHALL return the next owned results under the same ordering and family view
- **AND** a cursor from another ordering mode or family view SHALL be rejected

#### Scenario: Attempt cross-account Feed access
- **WHEN** a user attempts to retrieve another account's Feed or uses an invalid foreign cursor
- **THEN** the service SHALL deny access without revealing foreign document metadata

### Requirement: Follow upload progress from Feed
The web client SHALL open Feed after a successful upload receipt, highlight the new report, and refresh current states while Feed or report details are visible.

#### Scenario: Upload receipt arrives
- **WHEN** the API confirms upload completion
- **THEN** the client SHALL open All Family with upload-date ordering and highlight the uploaded report
- **AND** transport progress alone SHALL NOT trigger this transition

#### Scenario: Upload receipt arrives after leaving Upload
- **WHEN** the API confirms upload completion after the account manager has moved to another tab
- **THEN** the client SHALL stay on the current tab and keep its state, including an open report
- **AND** the Upload tab SHALL show the upload receipt on the next visit

#### Scenario: Processing changes in the background
- **WHEN** extraction, assignment, or review changes while Feed or report details are visible
- **THEN** the client SHALL refresh those states without requiring a reload
- **AND** metadata needing review SHALL remain distinguishable from medical-memory review

#### Scenario: Resolve an unassigned report
- **WHEN** the manager opens a report whose extraction succeeded but assignment is unresolved
- **THEN** the client SHALL show available patient-name evidence and source text and require an explicit owned-profile selection
- **AND** successful assignment SHALL update the report and Feed without implying that extracted information has been reviewed

#### Scenario: Leave Feed or end the session
- **WHEN** the manager leaves Feed or signs out
- **THEN** the client SHALL stop Feed polling and ignore late responses from the previous view
- **AND** sign-out SHALL clear the private Feed and report-detail state
