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
