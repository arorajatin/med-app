## Purpose

Define how the sole first-release account manager registers, verifies an identity, establishes a session, and completes the initial health-profile setup.

## ADDED Requirements

### Requirement: Register with a supported identity method
The system SHALL allow a new account manager to register with Google or with an email address and password without storing the password in application-managed medical data.

#### Scenario: Register with email and password
- **WHEN** a new user submits a valid email address and acceptable password
- **THEN** the system SHALL create a verification-pending identity
- **AND** the system SHALL send an email-verification action
- **AND** protected application access SHALL remain unavailable until verification succeeds

#### Scenario: Verify an email identity
- **WHEN** a verification-pending user completes a valid email-verification action
- **THEN** the system SHALL mark that identity verified
- **AND** the system SHALL allow the user to establish an authenticated session

#### Scenario: Register with Google
- **WHEN** a user completes a valid Google authorization flow
- **THEN** the system SHALL treat the provider-verified email as verified
- **AND** the system SHALL create or safely reconcile the corresponding application account

#### Scenario: Registration fails
- **WHEN** identity validation, verification, or the external authorization flow fails or is cancelled
- **THEN** the system SHALL NOT create an active duplicate account
- **AND** the user SHALL receive a safe retryable outcome that does not disclose another account's private details

### Requirement: Establish and end an account session
The system SHALL allow a verified registered identity to sign in and the account manager to sign out.

#### Scenario: Sign in with a verified identity
- **WHEN** a registered user successfully authenticates with a linked identity
- **THEN** the system SHALL establish a session mapped to exactly one application account

#### Scenario: Sign in with an unverified email identity
- **WHEN** an email/password identity has not completed verification
- **THEN** the system SHALL deny protected application access
- **AND** the system SHALL offer a safe way to resend verification

#### Scenario: Sign out
- **WHEN** the account manager signs out
- **THEN** the current session SHALL no longer authorize protected application access

### Requirement: Complete first-run onboarding
The system SHALL automatically create one `self` family profile and SHALL collect the account manager's name, age, weight with an entered unit, current conditions, and current medications before onboarding completes.

#### Scenario: Complete health context
- **WHEN** a verified account supplies valid required onboarding data
- **THEN** the system SHALL complete the `self` profile
- **AND** weight SHALL retain the entered `lb` or `kg` unit and a normalized value
- **AND** age and weight SHALL retain the date on which the user reported them

#### Scenario: Resume incomplete onboarding
- **WHEN** a verified account has not completed all required onboarding steps
- **THEN** the system SHALL resume at the first incomplete step
- **AND** the account SHALL NOT create an additional `self` profile

### Requirement: Capture account-level AI-processing consent
The system SHALL present one explicit AI-processing consent choice during onboarding, describing document extraction and use of reviewed personal memory in Chat, and SHALL retain the accepted scope, policy version, and timestamp for the account.

#### Scenario: Accept account-level consent
- **WHEN** the account manager accepts the presented AI-processing terms
- **THEN** future ingestions for that account SHALL be eligible for AI processing without another per-document consent prompt

#### Scenario: Do not accept account-level consent
- **WHEN** the account manager does not accept the presented AI-processing terms
- **THEN** the account and private profiles MAY remain available
- **AND** document ingestion SHALL NOT dispatch AI extraction
- **AND** Chat SHALL NOT send personal medical memory to an AI provider

### Requirement: One manager owns the first-release family space
The first release SHALL allow only the authenticated account manager to create and manage profiles and reports in that account's family space.

#### Scenario: Account manager uses a family profile
- **WHEN** the account manager selects a profile owned by the account
- **THEN** the system SHALL allow the requested operation subject to that capability's validation rules

#### Scenario: Family member attempts separate access
- **WHEN** a family member without the account manager's authenticated session attempts to access a managed profile
- **THEN** the system SHALL deny access
