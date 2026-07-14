# ADR 0004: Use SQLAlchemy Models

## Status

Accepted

## Implementation Status

Implemented. The current persistence model is defined with SQLAlchemy ORM models.

## Context

The backend needs relational data for profiles, records, files, extraction jobs, extracted fields, memory facts, appointments, checklist items, and reviews.

## Decision

Use SQLAlchemy ORM models as the backend persistence model.

Keep API schemas separate from persistence models using Pydantic request and response schemas.

## Consequences

The app can run locally on SQLite and move toward Postgres/Supabase for production. Schema changes must be handled through migrations once Alembic is added.

Keeping API schemas separate from ORM models avoids leaking internal storage details into the mobile contract.
