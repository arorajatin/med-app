# Appointment Preparation Specification

## Purpose

Define appointment tracking, medical-memory-based question generation, and post-visit feedback.

## Requirements

### Requirement: Manage appointments for an owned profile
An authenticated user SHALL be able to create and list appointments for a profile they own.

#### Scenario: Create an appointment
- **WHEN** a user supplies an owned profile, scheduled time, and optional visit details
- **THEN** the service SHALL create a scheduled appointment under that user and profile

#### Scenario: List appointments
- **WHEN** a user lists appointments for an owned profile
- **THEN** the service SHALL return that profile's appointments ordered by scheduled time ascending

### Requirement: Generate a checklist from reviewed memory
The service SHALL generate appointment questions only from reviewed memory facts for the appointment's user and profile.

#### Scenario: Reviewed memory is available
- **WHEN** a user generates a checklist and the profile has reviewed memory facts
- **THEN** the service SHALL create questions from up to eight most recently created facts
- **AND** every generated item SHALL reference its source fact

#### Scenario: No reviewed memory is available
- **WHEN** a user generates a checklist and the profile has no reviewed memory facts
- **THEN** the service SHALL create a generic tracking question without a source fact

#### Scenario: Regenerate a checklist
- **WHEN** a user generates a checklist for an appointment that already has items
- **THEN** the service SHALL replace the existing items with the newly generated checklist

### Requirement: Retrieve an appointment checklist
An authenticated owner SHALL be able to retrieve the stored checklist for an appointment.

#### Scenario: Read checklist
- **WHEN** a user requests the checklist for an owned appointment
- **THEN** the service SHALL return its items ordered by creation time ascending

### Requirement: Record appointment feedback
An authenticated owner SHALL be able to submit a one-to-five-star review for an appointment.

#### Scenario: Submit valid feedback
- **WHEN** a user submits an integer rating from one through five for an owned appointment
- **THEN** the service SHALL store the review
- **AND** the appointment status SHALL become `reviewed`

#### Scenario: Submit invalid feedback
- **WHEN** a user submits a rating outside one through five
- **THEN** the service SHALL reject the request as invalid
