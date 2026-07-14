# ADR 0009: Use Alembic Migrations

## Status

Accepted

## Implementation Status

Not started. Alembic is not configured yet, and schema creation still relies on SQLAlchemy metadata.

## Context

The backend currently uses SQLAlchemy metadata creation for local convenience. That is not enough for production schema evolution as the product adds auth, consent, extraction, memory, appointments, and future integrations.

## Decision

Use Alembic for database schema migrations.

`Base.metadata.create_all()` may remain only for local or test convenience until migrations are wired in. Production databases should be changed through explicit Alembic migrations.

## Consequences

Schema changes become reviewable, repeatable, and safer across local, staging, and production. The next implementation step should add Alembic configuration and an initial migration for the current models.
