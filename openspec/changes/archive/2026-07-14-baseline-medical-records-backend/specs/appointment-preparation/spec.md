## ADDED Requirements

### Requirement: Manage appointments for an owned profile
An authenticated user SHALL be able to create and list appointments for a profile they own.

#### Scenario: Create and list
- **WHEN** a user manages appointments for an owned profile
- **THEN** the service SHALL keep the appointments scoped to that user and profile

### Requirement: Generate a checklist from reviewed memory
The service SHALL build appointment questions only from reviewed memory for the appointment profile.

#### Scenario: Facts available
- **WHEN** reviewed facts exist
- **THEN** the checklist SHALL contain source-linked questions based on recent facts

#### Scenario: No facts available
- **WHEN** reviewed facts do not exist
- **THEN** the checklist SHALL contain a generic question without a source fact

### Requirement: Retrieve an appointment checklist
An owner SHALL be able to retrieve the stored checklist for an appointment.

#### Scenario: Read checklist
- **WHEN** an owner requests an appointment checklist
- **THEN** the service SHALL return its items in creation order

### Requirement: Record appointment feedback
An owner SHALL be able to submit a one-to-five-star appointment review.

#### Scenario: Valid review
- **WHEN** an owner submits a valid rating
- **THEN** the service SHALL store it and mark the appointment reviewed
