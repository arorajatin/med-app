## ADDED Requirements

### Requirement: Managed production persistence
The production service SHALL persist relational medical data in the configured Supabase Postgres database through the versioned schema.

#### Scenario: Production write
- **WHEN** an authenticated production request creates or updates a supported resource
- **THEN** the resource SHALL be committed to Supabase Postgres
- **AND** a subsequent service instance SHALL be able to read it subject to ownership rules

#### Scenario: Missing production database configuration
- **WHEN** the production service lacks a valid database configuration
- **THEN** it SHALL fail closed rather than fall back to a local SQLite database

### Requirement: Database-enforced ownership
Every user-owned production table SHALL enforce row-level access using the authenticated user's Supabase identity.

#### Scenario: Owner database access
- **WHEN** a database operation runs with a user's verified identity
- **THEN** row-level policies SHALL permit only the rows that identity is allowed to access

#### Scenario: Cross-user database access
- **WHEN** a database operation attempts to read or mutate another user's medical row
- **THEN** row-level policies SHALL deny the operation even if an application query omitted its owner filter

#### Scenario: Unscoped privileged access
- **WHEN** a normal request path lacks a user-scoped database identity
- **THEN** the request path SHALL NOT use a role that bypasses row-level policies

### Requirement: Private production object storage
Production record files SHALL be stored in a non-public Supabase Storage bucket under owner-scoped object keys.

#### Scenario: Upload a medical file
- **WHEN** an authenticated user uploads a file to an owned record
- **THEN** the service SHALL store the object under a key scoped to that user, profile, and record
- **AND** stored metadata SHALL reference the private object without exposing a public URL

#### Scenario: Cross-user object request
- **WHEN** a user attempts to access an object outside their ownership scope
- **THEN** storage policy and application authorization SHALL deny access

#### Scenario: Missing production storage configuration
- **WHEN** production private storage is not configured
- **THEN** uploads SHALL fail closed without writing to local filesystem storage

### Requirement: Local adapter parity
Local development and tests SHALL retain adapters that implement the same application-facing persistence and private-storage contracts.

#### Scenario: Run locally
- **WHEN** the service runs in the local environment
- **THEN** it MAY use SQLite and local private storage without requiring Supabase data services
- **AND** API response contracts SHALL remain compatible with production
