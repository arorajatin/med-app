## Purpose

Define how the sole first-release account manager registers, verifies an identity, establishes a session, and completes the initial health-profile setup.

## ADDED Requirements

### Requirement: Register with a supported identity method
The first release SHALL allow a new account manager to register only through Google, and SHALL NOT store an application-managed password. The system SHALL refuse to create or reconcile an application account for a credential whose upstream sign-in method is anything other than Google, including an email and password identity created directly with the identity provider. Email and password registration is a post-V1 roadmap item.

#### Scenario: Register with Google
- **WHEN** a user completes a valid Google authorization flow
- **THEN** the system SHALL treat the provider-verified email as verified
- **AND** the system SHALL create or safely reconcile the corresponding application account

#### Scenario: Present an unsupported identity method
- **WHEN** a verified credential names an upstream sign-in method other than Google, or names no method at all
- **THEN** the system SHALL deny protected application access
- **AND** the system SHALL NOT create or reconcile an application account for that identity

#### Scenario: Registration fails
- **WHEN** identity validation or the external authorization flow fails or is cancelled
- **THEN** the system SHALL NOT create an active duplicate account
- **AND** the user SHALL receive a safe retryable outcome that does not disclose another account's private details

### Requirement: Establish and end an account session
The system SHALL allow a verified registered identity to sign in and the account manager to sign out.

#### Scenario: Sign in with a verified identity
- **WHEN** a registered user successfully authenticates with a linked identity
- **THEN** the system SHALL establish a session mapped to exactly one application account

#### Scenario: Sign in after the provider flow is cancelled
- **WHEN** the Google authorization flow is cancelled or fails
- **THEN** the system SHALL NOT establish a session
- **AND** the user SHALL be able to retry sign-in without losing an existing account

#### Scenario: Sign out
- **WHEN** the account manager signs out
- **THEN** the current session SHALL no longer authorize protected application access

### Requirement: Complete first-run onboarding
The system SHALL automatically create one `self` family profile and SHALL collect the account manager's name, age, weight with an entered unit, current conditions, and current medications before onboarding completes. Age and weight SHALL use the accepted ranges, exact decimal normalization, reported-date display, and non-blocking refresh policy defined for profile health context.

#### Scenario: Complete health context
- **WHEN** a verified account supplies valid required onboarding data
- **THEN** the system SHALL complete the `self` profile
- **AND** weight SHALL retain the entered `lb` or `kg` unit and a normalized value
- **AND** age and weight SHALL retain the date on which the user reported them
- **AND** the service SHALL treat their validation and freshness states as non-diagnostic product controls

#### Scenario: Resume incomplete onboarding
- **WHEN** a verified account has not completed all required onboarding steps
- **THEN** the system SHALL resume at the first incomplete step
- **AND** the account SHALL NOT create an additional `self` profile

### Requirement: Account creation authorizes required AI processing
The system SHALL state during signup that AI processing is inherent to document extraction and use of reviewed personal memory in Chat. Creating an account SHALL authorize that processing without a separate onboarding step, stored application consent record, per-document choice, or AI-disabled runtime mode.

#### Scenario: Create an account
- **WHEN** a verified identity creates an application account
- **THEN** the account SHALL be eligible to use capabilities that require AI processing
- **AND** onboarding SHALL begin with the `self` profile rather than a separate consent step

### Requirement: Enter the tab interface after onboarding
A completed account SHALL enter a persistent interface with Feed, Chat, Upload, Drive, and Profile in that order. During the document-upload milestone, Upload SHALL be the initial active tab, Feed/Chat/Drive SHALL identify themselves as coming soon, and Profile SHALL retain existing family settings and health-summary editing.

#### Scenario: Finish or resume completed onboarding
- **WHEN** the final required onboarding step completes or a completed account restores its session
- **THEN** the client SHALL open Upload within the five-tab interface
- **AND** an incomplete account SHALL continue to resume its required onboarding step

#### Scenario: Switch away from an upload draft
- **WHEN** the account manager switches tabs before submitting a report
- **THEN** the client SHALL retain the selected profile, ordered files, and optional context in memory
- **AND** it SHALL stop active camera access while Upload is hidden

#### Scenario: End the session with an upload draft
- **WHEN** the session ends
- **THEN** the client SHALL discard private draft files and previews, stop camera access, and abort pending upload transport
- **AND** the tab interface SHALL no longer be visible

### Requirement: One manager owns the first-release family space
The first release SHALL allow only the authenticated account manager to create and manage profiles and reports in that account's family space.

#### Scenario: Account manager uses a family profile
- **WHEN** the account manager selects a profile owned by the account
- **THEN** the system SHALL allow the requested operation subject to that capability's validation rules

#### Scenario: Family member attempts separate access
- **WHEN** a family member without the account manager's authenticated session attempts to access a managed profile
- **THEN** the system SHALL deny access
