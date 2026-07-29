## ADDED Requirements

### Requirement: Review every candidate memory item explicitly
The service SHALL present every extracted candidate insight, condition, medication, and follow-up item selected by default, and SHALL require an explicit review submission before any selected candidate becomes trusted memory.

#### Scenario: Submit the default selection
- **WHEN** the account manager submits a review with a candidate item still selected
- **THEN** the item SHALL be marked confirmed with a review timestamp
- **AND** it MAY contribute a fact to medical memory

#### Scenario: Uncheck a candidate
- **WHEN** the account manager deselects a candidate before submitting review
- **THEN** the item SHALL be marked ignored
- **AND** it SHALL NOT contribute a fact to medical memory

#### Scenario: Edit a candidate
- **WHEN** the account manager edits a candidate and submits a valid replacement
- **THEN** the item SHALL be marked edited
- **AND** the replacement SHALL become the trusted value while original extraction provenance remains auditable

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
The service SHALL derive medical memory only from confirmed or edited candidate-memory items and valid user-attested condition or medication entries, and SHALL exclude automatic metric observations.

#### Scenario: Candidate review is still pending
- **WHEN** candidate-memory items have been extracted but their review has not been submitted
- **THEN** those items SHALL NOT appear in medical memory

#### Scenario: Trusted candidates are reviewed
- **WHEN** a condition, medication, insight, or follow-up candidate is confirmed or edited
- **THEN** the service SHALL rebuild the record's memory facts from all trusted candidate items
- **AND** every derived fact SHALL retain its source record and candidate identifiers

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

