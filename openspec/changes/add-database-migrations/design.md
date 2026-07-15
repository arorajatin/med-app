## Context

`Base.metadata.create_all()` currently runs during FastAPI lifespan startup and worker startup. It handles first-run SQLite setup but does not provide a production change history or a controlled upgrade path. The relational model already has enough tables and indexes that an explicit baseline is warranted.

## Goals / Non-Goals

**Goals:**

- Make Alembic the authoritative production schema mechanism.
- Generate a reviewed initial revision from the current models.
- Prove the complete migration chain on an isolated database.
- Retain a low-friction test bootstrap where it remains useful.

**Non-Goals:**

- Move persistence from SQLite to Supabase Postgres.
- Add row-level security or storage policies.
- Change existing API schemas.

## Decisions

### Use Alembic with the existing metadata

Configure Alembic's target metadata from `app.database.Base` and import the model module in the migration environment. This keeps migration autogeneration aligned with the ORM while still requiring generated revisions to be reviewed.

### Check in a full initial revision

The initial migration will create the current tables, foreign keys, and indexes. Automated tests will upgrade a new SQLite database to head. Postgres verification can be added with the Supabase boundary when a test Postgres service exists.

### Separate schema migration from application startup

Production startup will not call `create_all()`. Local development and tests may retain an explicit convenience bootstrap, but the code path must be gated so production cannot depend on it.

### Handle existing databases deliberately

Existing developer databases can be recreated or stamped only after verifying that their schema matches the initial revision. Stamping an unknown production database is not an acceptable migration strategy.

## Risks / Trade-offs

- Autogeneration can omit semantic intent or produce unsafe operations -> review every revision and test the generated schema.
- SQLite and Postgres differ in DDL behavior -> add Postgres migration coverage before the production database rollout.
- Gating `create_all()` may break undocumented local flows -> document the bootstrap command and cover startup modes in tests.

## Migration Plan

1. Add Alembic and the initial revision without changing production startup.
2. Verify empty-database upgrade and model compatibility in tests.
3. Add an explicit migration command to deployment instructions.
4. Disable metadata creation in production startup.

Rollback uses the prior application version plus the revision's tested downgrade when the schema change is reversible. Destructive future migrations require their own backup and rollback plan.

## Open Questions

- Should CI add a temporary Postgres service in this change or in the Supabase boundary change?
- Should local startup auto-upgrade, or should developers run the same explicit command as production?
