# Reviewed Medical Memory Specification

## Purpose

Define the human review boundary between untrusted extraction candidates and the trusted medical
facts the product uses.

## Requirements

### Requirement: Review every candidate explicitly
The service SHALL allow an owner to confirm, edit, or ignore the document-metadata candidates and
candidate-memory items belonging to an owned record, and SHALL keep an immutable review history for
every decision. Condition-shaped and unsupported items are not persisted by the extraction boundary
and therefore SHALL NOT be reviewable.

#### Scenario: Confirm a candidate
- **WHEN** an owner confirms a candidate belonging to the record
- **THEN** the candidate's review status SHALL become `confirmed`
- **AND** the service SHALL append an immutable review entry recording the reviewing identity, the action, and the review time

#### Scenario: Edit a candidate
- **WHEN** an owner edits a candidate and supplies a replacement value
- **THEN** the candidate's review status SHALL become `edited`
- **AND** the service SHALL store the submitted value alongside the preserved original value

#### Scenario: Ignore a candidate
- **WHEN** an owner ignores a candidate
- **THEN** the candidate's review status SHALL become `ignored`
- **AND** it SHALL NOT contribute a fact to medical memory

#### Scenario: Review a candidate that does not belong to the record
- **WHEN** any submitted candidate identifier is not a candidate of the owned record
- **THEN** the service SHALL reject the complete review request with HTTP 400
- **AND** it SHALL NOT create or trust a condition fact

#### Scenario: Submit a malformed decision
- **WHEN** an edit decision omits a replacement value, or a non-edit decision supplies one
- **THEN** the service SHALL reject the request as invalid

### Requirement: Build memory only from reviewed candidates and user-attested entries
The service SHALL derive trusted medical memory only from confirmed or edited candidate-memory
items, mapping `prescription_medication` to the `medication` category and
`prescription_instruction` to the `follow_up` category, and from condition and medication entries the
account manager typed directly. Metric observations SHALL never become memory facts.

Memory reads SHALL decide on provenance, not category alone. For `user_attested` facts they SHALL
return the `condition` and `medication` categories. For every other provenance they SHALL return only
the `medication`, `test_result`, and `follow_up` categories until the source-cited
documented-condition contract and its explicit review boundary are implemented.

#### Scenario: Review is still pending
- **WHEN** candidates have been extracted but not reviewed
- **THEN** they SHALL NOT appear in medical memory

#### Scenario: A candidate is trusted
- **WHEN** a prescription medication or instruction candidate is confirmed or edited
- **THEN** the service SHALL create an active memory fact with `reviewed_candidate` provenance
- **AND** the fact SHALL retain its source record, source candidate, and source reference identifiers
- **AND** an edited fact SHALL carry the submitted value while the candidate preserves the original

#### Scenario: The account manager attests a fact
- **WHEN** the account manager declares a current condition or medication for an owned profile
- **THEN** the service SHALL create an active memory fact with `user_attested` provenance
- **AND** the fact SHALL retain the attesting identity, the profile, and the time
- **AND** the fact SHALL carry no source record, source candidate, or source reference

#### Scenario: A declaration is repeated
- **WHEN** the account manager declares the current conditions or medications for that profile again
- **THEN** the declaration SHALL replace the previous set, deactivating the profile's earlier user-attested facts in that category with a supersession time
- **AND** an empty declaration SHALL record that the account manager reported none without creating a fact

#### Scenario: Measurements stay out of memory
- **WHEN** an extraction stores metric observations for a record
- **THEN** those measurements SHALL NOT appear in medical memory regardless of any review decision

#### Scenario: A document-derived condition exists
- **WHEN** stored memory holds a `condition` fact whose provenance is not `user_attested`
- **THEN** memory reads SHALL omit that fact
- **AND** review SHALL NOT recreate it from a condition-shaped candidate, because no such candidate can be persisted

#### Scenario: Unsupported memory exists
- **WHEN** stored memory uses a category outside those permitted for its provenance
- **THEN** memory reads SHALL omit that fact

#### Scenario: A prior decision changes
- **WHEN** a later review changes or ignores a candidate that already produced a fact
- **THEN** the service SHALL deactivate the prior fact with a supersession time
- **AND** a replacement fact SHALL reference the fact it superseded so stale facts do not remain active

### Requirement: Apply trusted document metadata
The service SHALL update record metadata only from confirmed or edited document-metadata candidates,
and an explicit user rename SHALL always win over an extracted display name.

#### Scenario: Confirm document metadata
- **WHEN** an owner confirms or edits an extracted document type or valid ISO record date
- **THEN** the service SHALL apply that value to the record

#### Scenario: Ignore document metadata
- **WHEN** an owner ignores a document-metadata candidate
- **THEN** the service SHALL leave the record's corresponding value untrusted and unchanged

#### Scenario: The user has renamed the report
- **WHEN** a trusted display-name candidate is applied to a record the user has already renamed
- **THEN** the service SHALL keep the user's display name

### Requirement: Complete record review
The service SHALL derive a record's review state from the candidate-memory items currently persisted
for its ingestion, and SHALL treat review as complete once none of them remain pending.
Document-metadata candidates and metric observations SHALL NOT block completion.

#### Scenario: Some candidate memory remains pending
- **WHEN** a review request leaves one or more of the record's memory candidates pending
- **THEN** the ingestion's review state SHALL remain `pending`

#### Scenario: All candidate memory has decisions
- **WHEN** every memory candidate for the record has a non-pending review status
- **THEN** the ingestion's review state SHALL become `reviewed`

#### Scenario: A document produces no candidate memory
- **WHEN** an extraction retains no memory candidates for an ingestion
- **THEN** the ingestion's review state SHALL be `not_required`
- **AND** unsupported provider output SHALL NOT prevent review completion
