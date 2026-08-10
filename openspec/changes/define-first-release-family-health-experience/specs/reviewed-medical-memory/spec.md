## ADDED Requirements

### Requirement: Review every candidate memory item explicitly
The service SHALL apply subtype-specific review to every extracted `memory_candidate`. Prescription medication and instruction candidates SHALL be selected by default but SHALL require an explicit review submission before becoming trusted. A `documented_condition_candidate` SHALL begin pending and SHALL require one explicit decision: `confirm`, `edit`, or `ignore`.

#### Scenario: Submit the default prescription selection
- **WHEN** the account manager submits a review with a prescription medication or instruction candidate still selected
- **THEN** the item SHALL be marked confirmed with a review timestamp
- **AND** it MAY contribute a fact to medical memory

#### Scenario: Uncheck a prescription candidate
- **WHEN** the account manager deselects a prescription medication or instruction candidate before submitting review
- **THEN** the item SHALL be marked ignored
- **AND** it SHALL NOT contribute a fact to medical memory

#### Scenario: Edit a prescription candidate
- **WHEN** the account manager edits a prescription medication or instruction candidate and submits a valid replacement
- **THEN** the item SHALL be marked edited
- **AND** the replacement SHALL become the trusted value while original extraction provenance remains auditable

#### Scenario: Review a condition written in a document
- **WHEN** the account manager views a pending `documented_condition_candidate`
- **THEN** the service SHALL label it `Condition written in this document — verify before saving`
- **AND** it SHALL show the exact extracted condition text and the source reference to the span that names it

#### Scenario: Confirm a documented condition
- **WHEN** the account manager chooses `confirm` for a documented-condition candidate
- **THEN** the candidate SHALL become confirmed with reviewer and review time
- **AND** it SHALL create a trusted condition fact that retains the exact extracted text, source record, candidate identifier, and source reference as provenance

#### Scenario: Edit a documented condition
- **WHEN** the account manager chooses `edit` and submits a valid replacement for a documented-condition candidate
- **THEN** the candidate SHALL become edited with reviewer and review time
- **AND** the replacement SHALL create the trusted condition fact while the original extracted text, source record, candidate identifier, and source reference remain auditable

#### Scenario: Ignore a documented condition
- **WHEN** the account manager chooses `ignore` for a documented-condition candidate
- **THEN** the candidate SHALL become ignored with reviewer and review time
- **AND** it SHALL remain outside trusted medical memory, Chat evidence, Drive condition groups, and appointment evidence

#### Scenario: Review a foreign candidate
- **WHEN** any submitted candidate does not belong to the account's owned record
- **THEN** the service SHALL reject the complete review request as invalid

### Requirement: Trust user-attested onboarding facts
Conditions and medications entered directly by the account manager during profile onboarding SHALL enter medical memory as user-attested facts without an AI-extraction review step.

#### Scenario: Enter a current condition
- **WHEN** the account manager supplies a valid current condition for an owned profile
- **THEN** the service SHALL create a trusted memory fact with user-attested provenance

#### Scenario: Enter a current medication
- **WHEN** the account manager supplies a valid current medication for an owned profile
- **THEN** the service SHALL create a trusted memory fact with user-attested provenance

## MODIFIED Requirements

### Requirement: Build memory only from trusted fields
The service SHALL derive medical memory only from confirmed or edited prescription candidate-memory items, confirmed or edited documented-condition candidates, and valid user-attested condition or medication entries. It SHALL exclude automatic metric observations and every pending or ignored documented-condition candidate.

#### Scenario: Candidate review is still pending
- **WHEN** candidate-memory items have been extracted but their review has not been submitted
- **THEN** those items SHALL NOT appear in medical memory

#### Scenario: Trusted candidates are reviewed
- **WHEN** a prescription medication or instruction candidate is confirmed or edited
- **THEN** the service SHALL rebuild the record's memory facts from all trusted candidate items
- **AND** every derived fact SHALL retain its source record and candidate identifiers

#### Scenario: A literal documented condition is confirmed or edited
- **WHEN** a documented-condition candidate is confirmed or edited
- **THEN** the service SHALL create or supersede the corresponding trusted condition fact
- **AND** it SHALL retain the reviewer, review time, candidate, original extracted text, source reference, and source record as provenance

#### Scenario: A literal documented condition is not trusted
- **WHEN** a documented-condition candidate is pending or ignored
- **THEN** it SHALL NOT create or update a trusted condition fact

#### Scenario: User attests a fact
- **WHEN** the account manager directly enters a valid current condition or medication
- **THEN** the service SHALL retain the account manager, profile, time, and user-attested source as provenance

#### Scenario: A deterministic measurement is stored
- **WHEN** an extracted measurement becomes a metric observation
- **THEN** that observation SHALL NOT become a medical-memory fact

#### Scenario: A prior decision changes
- **WHEN** review changes which candidate items are trusted for a record
- **THEN** the service SHALL supersede or replace that record's derived memory facts so stale active facts do not remain
- **AND** existing citations SHALL remain resolvable to retained audit provenance or an explicit tombstone

### Requirement: Complete record review
The service SHALL mark the memory-review portion of a record complete only after none of its candidate-memory items remain pending; deterministic metric observations SHALL NOT block completion.

#### Scenario: Candidate items remain pending
- **WHEN** a review request leaves one or more candidate-memory items pending
- **THEN** the record's memory review SHALL NOT be complete

#### Scenario: All candidate items have decisions
- **WHEN** every candidate-memory item for a record has a non-pending review status
- **THEN** the record's memory review SHALL become complete

#### Scenario: Record has measurements but no candidate memory
- **WHEN** a record publishes deterministic observations and has no candidate-memory items
- **THEN** its memory review SHALL be complete without requiring approval of those observations

## REMOVED Requirements

### Requirement: Review every extracted field explicitly
**Reason**: Extraction now separates automatic deterministic observations from semantic candidate-memory items, so requiring one review rule for every field would conflate metric tracking with trusted medical memory.

**Migration**: Existing extracted fields SHALL be classified as deterministic observations or candidate-memory items. Existing review decisions SHALL be retained, and only candidate-memory items SHALL continue through the explicit memory-review workflow.
