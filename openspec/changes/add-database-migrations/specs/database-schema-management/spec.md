## ADDED Requirements

### Requirement: Versioned database schema
The project SHALL define ordered database migrations as the authoritative way to create and evolve persistent schemas outside tests.

#### Scenario: Bootstrap an empty database
- **WHEN** the migration command upgrades an empty supported database to the latest revision
- **THEN** it SHALL create the schema required by the current SQLAlchemy models

#### Scenario: Upgrade an older database
- **WHEN** a supported database is behind the latest revision
- **THEN** the migration command SHALL apply each pending revision in order
- **AND** it SHALL record the resulting revision

### Requirement: Explicit production migration
Production application startup SHALL NOT silently create or alter database tables from ORM metadata.

#### Scenario: Start against a migrated database
- **WHEN** the service starts in production against the expected schema revision
- **THEN** startup SHALL proceed without mutating the schema

#### Scenario: Deploy a schema change
- **WHEN** a release includes a database schema change
- **THEN** deployment SHALL run the reviewed migration explicitly before code depends on the new schema

### Requirement: Migration verification
Every schema migration SHALL be testable against an isolated database before deployment.

#### Scenario: Verify the migration chain
- **WHEN** automated migration tests run
- **THEN** they SHALL upgrade an empty database to the latest revision
- **AND** the resulting tables, columns, indexes, and constraints SHALL match the expected model contract

#### Scenario: Reverse a reversible revision
- **WHEN** a revision is marked reversible and its downgrade is tested
- **THEN** Alembic SHALL return the database to the prior revision without an unhandled error
