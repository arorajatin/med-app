## ADDED Requirements

### Requirement: Environment-appropriate authentication
The service SHALL authenticate protected API requests using the configured authentication mode.

#### Scenario: Local identity
- **WHEN** development authentication is enabled and a request supplies a bearer user ID or `X-User-Id`
- **THEN** the service SHALL use that value as the current user identity

#### Scenario: Production identity
- **WHEN** development authentication is disabled and a bearer token is supplied
- **THEN** the service SHALL verify the token against the configured Supabase project
- **AND** the verified subject SHALL become the current user identity

#### Scenario: Missing identity
- **WHEN** a protected request has no identity for the configured mode
- **THEN** the service SHALL reject the request with HTTP 401

### Requirement: User-owned resource isolation
The service SHALL scope all private medical resources to the authenticated user.

#### Scenario: Cross-owner request
- **WHEN** a user requests another user's profile, record, extraction job, or appointment
- **THEN** the service SHALL respond as though the resource was not found

### Requirement: Unauthenticated health check
The service SHALL expose a health endpoint that does not require a user identity.

#### Scenario: Health probe
- **WHEN** a caller requests `GET /health`
- **THEN** the service SHALL return an OK status payload
