# Access Control Specification

## Purpose

Define how callers are authenticated and how private medical resources remain isolated by owner.

## Requirements

### Requirement: Environment-appropriate authentication
The service SHALL authenticate protected API requests using the configured authentication mode.

#### Scenario: Local bearer identity
- **WHEN** development authentication is enabled and a request supplies `Authorization: Bearer <user-id>`
- **THEN** the service SHALL use that value as the current user identity

#### Scenario: Local header identity
- **WHEN** development authentication is enabled and a request supplies `X-User-Id`
- **THEN** the service SHALL use that value as the current user identity

#### Scenario: Missing local identity
- **WHEN** development authentication is enabled and neither supported identity header is present
- **THEN** the service SHALL reject the request with HTTP 401

#### Scenario: Production Supabase token
- **WHEN** development authentication is disabled and a bearer token is supplied
- **THEN** the service SHALL verify its signature, issuer, audience, expiry, and subject against the configured Supabase project
- **AND** the service SHALL use the verified subject as the current user identity

#### Scenario: Missing production configuration
- **WHEN** production authentication is selected without a Supabase URL
- **THEN** the service SHALL reject authenticated access as a server configuration error

### Requirement: Retain verified identity provenance
The service SHALL key an application account on the authentication provider and its stable subject,
and SHALL create or reuse that account idempotently for every later sign-in by the same subject.

Alongside that key the service SHALL retain the upstream method that verified the person, such as
`google`, and their verified email address when the token supplies them, refreshing both on later
sign-ins. It SHALL read this provenance only from token claims the identity provider controls, and
SHALL NOT read it from claims the account holder can write. The upstream method SHALL NOT take part
in the account key, so changing sign-in method never repoints an account.

#### Scenario: First sign-in through a federated provider
- **WHEN** a verified token carries an upstream provider and email in provider-controlled claims
- **THEN** the service SHALL create one account for that subject
- **AND** it SHALL retain the upstream provider and email as identity provenance

#### Scenario: Return sign-in
- **WHEN** the same subject signs in again
- **THEN** the service SHALL reuse the existing account rather than create another
- **AND** it SHALL update the retained provenance when the verified values have changed

#### Scenario: Token carries account-holder-written metadata
- **WHEN** a verified token supplies provider or email values only in claims the account holder can write
- **THEN** the service SHALL ignore those values
- **AND** it SHALL still authenticate the request on its verified subject

### Requirement: User-owned resource isolation
The service SHALL scope profiles, records, extraction jobs, medical memory, appointments, checklists, and appointment reviews to the authenticated user.

#### Scenario: Owner accesses a resource
- **WHEN** an authenticated user requests a resource they own
- **THEN** the service SHALL allow the operation subject to the resource's other validation rules

#### Scenario: User requests another owner's resource
- **WHEN** an authenticated user requests a profile, record, extraction job, or appointment owned by another user
- **THEN** the service SHALL respond as though that resource was not found

### Requirement: Unauthenticated health check
The service SHALL expose a health endpoint that does not require a user identity.

#### Scenario: Health probe
- **WHEN** a caller requests `GET /health`
- **THEN** the service SHALL return an OK status payload
