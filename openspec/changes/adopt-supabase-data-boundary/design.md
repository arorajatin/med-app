## Context

The current service verifies Supabase JWTs but uses a process-wide SQLAlchemy session factory and `LocalPrivateStorage`. Application queries filter by `user_id`, which is necessary but does not protect against a missed filter or direct database access. Production storage must also avoid local disk and public object URLs.

## Goals / Non-Goals

**Goals:**

- Use Supabase Postgres and private Storage in production.
- Enforce ownership at both application and data layers.
- Keep the existing API contract and local developer experience.
- Fail closed when production data services are misconfigured.

**Non-Goals:**

- Add user-to-user sharing or clinician access.
- Add public or long-lived file links.
- Replace Supabase Auth token verification.
- Define record retention, export, or account deletion policy.

## Decisions

### Build on versioned migrations

This change depends on `add-database-migrations`. Supabase schema and policy SQL will be delivered through reviewed migrations rather than dashboard-only changes.

### Preserve application ownership checks

Existing `user_id` filters remain part of the service contract. Row-level security adds defense in depth; it does not replace explicit ownership checks or not-found behavior in the API.

### Do not bypass RLS in normal request paths

Request-scoped database access must make the verified Supabase user identity available to Postgres policies and use a role subject to RLS. A short implementation spike will choose between a user-scoped PostgREST path and transaction-local claims with direct SQLAlchemy access. Service-role credentials must be limited to audited administrative or migration paths.

### Introduce a private storage interface

Generalize the current local storage dependency to a small interface for saving and reading private objects. The Supabase adapter will use a private bucket and owner/profile/record-prefixed keys. The database may retain the existing storage-path field as an opaque object key.

### Keep uploads server-mediated

The current API continues to accept file bytes and enforce record ownership and size limits. Direct client uploads and signed download URLs require separate specs because they introduce new authorization and lifecycle behavior.

## Risks / Trade-offs

- Incorrect request claims could make RLS deny valid traffic or expose rows -> prove policies with two-user integration tests and avoid privileged request roles.
- Storage and database writes are not one transaction -> delete the object on metadata failure and add reconciliation visibility.
- Supabase integration tests require external services -> use a disposable local or CI Supabase stack and keep unit tests adapter-based.
- Local and production adapters can drift -> run a shared contract test suite against both.

## Migration Plan

1. Land database migrations and provision a non-production Supabase project.
2. Add schema policies and validate them with isolated users.
3. Add the storage interface and Supabase adapter behind environment configuration.
4. Migrate any production seed data and files with checksums before switching traffic.
5. Enable the production adapters and monitor denied operations and orphaned objects.

Rollback switches application traffic to the prior release only while the old data boundary remains available. Once production data exists only in Supabase, rollback must preserve and read that data rather than silently returning to SQLite or local files.

## Open Questions

- Which user-scoped database access approach best preserves SQLAlchemy usage while making `auth.uid()` reliable?
- Will files ever be downloaded through this backend, or should a separate signed-URL capability be proposed?
- What backup, retention, and deletion requirements apply to medical files and raw extraction output?
