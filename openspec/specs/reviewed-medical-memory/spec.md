# Reviewed Medical Memory Specification

## Purpose

Define the human review boundary between untrusted extraction and the medical facts used by the product.

## Requirements

### Requirement: Review every extracted field explicitly
The service SHALL allow an owner to confirm, edit, ignore, or mark incorrect the extracted fields of a record.

#### Scenario: Confirm a field
- **WHEN** a user confirms an extracted field belonging to the record
- **THEN** the field SHALL be marked `confirmed` with a review timestamp

#### Scenario: Edit a field
- **WHEN** a user edits an extracted field and supplies a replacement value
- **THEN** the field SHALL be marked `edited`
- **AND** the replacement SHALL become both its stored and normalized value

#### Scenario: Reject a field
- **WHEN** a user ignores a field or marks it incorrect
- **THEN** the field SHALL retain that review outcome
- **AND** it SHALL NOT contribute a fact to medical memory

#### Scenario: Review a foreign field
- **WHEN** any submitted field does not belong to the owned record
- **THEN** the service SHALL reject the complete review request with HTTP 400

### Requirement: Build memory only from trusted fields
The service SHALL derive medical memory only from confirmed or edited condition, medication, test-result, and follow-up fields.

#### Scenario: Extraction is still pending
- **WHEN** fields have been extracted but not reviewed
- **THEN** those fields SHALL NOT appear in medical memory

#### Scenario: Trusted fields are reviewed
- **WHEN** a condition, medication, test result, or follow-up field is confirmed or edited
- **THEN** the service SHALL rebuild the record's memory facts from all trusted fields
- **AND** every fact SHALL retain its source record and source field identifiers

#### Scenario: A prior decision changes
- **WHEN** review changes which fields are trusted for a record
- **THEN** the service SHALL replace that record's derived memory facts so stale facts do not remain

### Requirement: Apply trusted document metadata
The service SHALL update record metadata only from confirmed or edited document-type and record-date fields.

#### Scenario: Confirm document metadata
- **WHEN** a user confirms or edits an extracted document type or valid ISO record date
- **THEN** the service SHALL apply that value to the record

### Requirement: Complete record review
The service SHALL mark a record as reviewed only after none of its extracted fields remain pending.

#### Scenario: Some fields remain pending
- **WHEN** a review request leaves one or more record fields pending
- **THEN** the record SHALL NOT move to `reviewed`

#### Scenario: All fields have decisions
- **WHEN** every extracted field for a record has a non-pending review status
- **THEN** the record status SHALL become `reviewed`
