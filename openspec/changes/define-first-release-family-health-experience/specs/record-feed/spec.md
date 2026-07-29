## Purpose

Define the account-wide chronological Feed for browsing completed family reports across every managed profile and ingestion source.

## ADDED Requirements

### Requirement: Aggregate completed uploads across the family
The Feed SHALL include completed document uploads owned by the account across all managed family profiles and supported ingestion sources.

#### Scenario: Browse the family Feed
- **WHEN** the account manager opens Feed
- **THEN** the system SHALL return completed uploads for `self` and every other owned family profile
- **AND** every item SHALL identify its assigned profile or `needs assignment` state, ingestion source, display filename, and current processing state

#### Scenario: Upload is incomplete
- **WHEN** a staged upload has not reached upload-complete state
- **THEN** it SHALL NOT appear in Feed

#### Scenario: Extraction is still processing
- **WHEN** an upload is complete but extraction or review is not complete
- **THEN** it SHALL remain eligible for Feed
- **AND** Feed SHALL expose its current processing or assignment state

#### Scenario: Profile assignment is unresolved
- **WHEN** upload is complete but profile assignment needs account-manager resolution
- **THEN** Feed SHALL include the account-owned item with an attention-required state
- **AND** the item SHALL remain excluded from profile-scoped Drive, metrics, memory, and Chat

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
- **WHEN** the account manager follows a valid Feed cursor without changing the ordering mode
- **THEN** the service SHALL return the next owned results under the same ordering

#### Scenario: Attempt cross-account Feed access
- **WHEN** a user attempts to retrieve another account's Feed or uses an invalid foreign cursor
- **THEN** the service SHALL deny access without revealing foreign document metadata
