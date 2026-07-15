## Why

The service currently creates tables from SQLAlchemy metadata at startup. That is convenient locally but cannot review, order, or safely roll out production schema changes.

## What Changes

- Add Alembic configuration tied to the existing SQLAlchemy metadata.
- Create and verify an initial migration for the current relational model.
- Make production startup require an explicitly migrated database.
- Keep a documented local and test bootstrap path.
- Add migration verification to automated tests.

This change does not move data to Supabase or alter product-facing API behavior.

## Capabilities

### New Capabilities

- `database-schema-management`: Repeatable creation and evolution of the relational schema.

### Modified Capabilities

None.

## Impact

Affected areas include `app/database.py`, `app/models.py`, application startup, dependencies, deployment commands, and database tests. This change is a prerequisite for `adopt-supabase-data-boundary`.
