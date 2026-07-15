## ADDED Requirements

### Requirement: Review every extracted field explicitly
The service SHALL allow an owner to confirm, edit, ignore, or mark incorrect an extracted field.

#### Scenario: Accept or edit a field
- **WHEN** a user confirms or edits a field belonging to the record
- **THEN** the field SHALL become trusted and retain its review timestamp

#### Scenario: Reject a field
- **WHEN** a user ignores a field or marks it incorrect
- **THEN** the field SHALL NOT contribute to medical memory

### Requirement: Build memory only from trusted fields
The service SHALL derive memory only from confirmed or edited medical fields.

#### Scenario: Trusted medical field
- **WHEN** a medical field becomes trusted
- **THEN** the service SHALL rebuild source-linked facts for that record

#### Scenario: Pending field
- **WHEN** a field has not been reviewed
- **THEN** it SHALL NOT appear in medical memory

### Requirement: Apply trusted document metadata
The service SHALL update record metadata only from confirmed or edited document metadata fields.

#### Scenario: Trusted record date
- **WHEN** a valid record date is confirmed or edited
- **THEN** the service SHALL apply it to the record

### Requirement: Complete record review
The service SHALL mark a record reviewed only when no extracted fields remain pending.

#### Scenario: All decisions complete
- **WHEN** all fields have a non-pending decision
- **THEN** the record status SHALL become reviewed
