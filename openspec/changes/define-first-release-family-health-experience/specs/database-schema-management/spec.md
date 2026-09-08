## MODIFIED Requirements

### Requirement: Fresh-install database schema
The project SHALL retain Alembic revision `20260721_0001` as the sole schema baseline and apply forward revision `20260908_0002` as the declared current head. The supported installation path SHALL begin with an empty database and SHALL NOT import or transform rows produced by prototype builds.

#### Scenario: Bootstrap an empty database
- **WHEN** the migration command upgrades an empty supported database to the declared head
- **THEN** it SHALL create the schema required by the current SQLAlchemy models
- **AND** it SHALL record revision `20260908_0002`

#### Scenario: Upgrade a supported baseline installation
- **WHEN** the explicit migration command runs against revision `20260721_0001`
- **THEN** it SHALL add owned profile aliases and attempt-linked assignment history with account ownership constraints
- **AND** it SHALL preserve existing account, profile, ingestion, and extraction rows

#### Scenario: Start against a non-current database
- **WHEN** the API or worker connects to a database whose recorded revision differs from the declared head
- **THEN** startup SHALL fail before serving requests or processing jobs
- **AND** the runtime SHALL NOT alter that database
