# Database Schema Management Specification

## Purpose

Define how the service creates and verifies the relational schema for a fresh installation without
mutating production schemas during application startup.

## Requirements

### Requirement: Fresh-install database schema
The project SHALL use Alembic revision `20260721_0001` as the sole schema baseline for this release.
The supported installation path SHALL begin with an empty database and SHALL NOT import or transform
rows produced by prototype builds.

#### Scenario: Bootstrap an empty database
- **WHEN** the migration command upgrades an empty supported database to the declared head
- **THEN** it SHALL create the schema required by the current SQLAlchemy models
- **AND** it SHALL record revision `20260721_0001`

#### Scenario: Start against a non-current database
- **WHEN** the API or worker connects to a database whose recorded revision differs from the declared head
- **THEN** startup SHALL fail before serving requests or processing jobs
- **AND** the runtime SHALL NOT alter that database

### Requirement: Explicit production migration
Production application startup SHALL NOT silently create or alter database tables from ORM metadata.

#### Scenario: Start against a current database
- **WHEN** the service starts in production against the declared schema revision
- **THEN** startup SHALL proceed without mutating the schema

#### Scenario: Deploy a schema change
- **WHEN** a future release includes a reviewed database schema change
- **THEN** deployment SHALL run its declared migration explicitly before code depends on the new schema

### Requirement: Migration verification
The fresh schema SHALL be testable against isolated SQLite and PostgreSQL databases before deployment.

#### Scenario: Verify the schema
- **WHEN** automated migration tests run against an empty database
- **THEN** they SHALL upgrade it to the declared head
- **AND** the resulting tables, columns, indexes, and foreign keys SHALL match the expected model contract
- **AND** API and worker startup SHALL succeed without runtime schema creation

#### Scenario: Rehearse disposable teardown
- **WHEN** the initial revision's downgrade is tested on a disposable database
- **THEN** Alembic SHALL return that database to an empty schema without an unhandled error
