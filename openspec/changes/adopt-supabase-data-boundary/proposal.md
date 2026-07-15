## Why

Production authentication already verifies Supabase access tokens, but records still use SQLite and local files. Sensitive medical data needs durable managed persistence, private object storage, and ownership enforcement below the application layer before production use.

## What Changes

- Run production relational persistence on Supabase Postgres after migrations are in place.
- Add row-level ownership policies for every user-owned table.
- Introduce a storage abstraction and a Supabase private-bucket implementation.
- Store uploads under owner-scoped object keys without public access.
- Keep SQLite and filesystem adapters for local development and tests.
- Add cross-user policy tests that prove direct data isolation.

This change does not add sharing, public links, mobile direct uploads, or a retention policy.

## Capabilities

### New Capabilities

- `production-data-boundary`: Production Postgres, private object storage, and defense-in-depth ownership enforcement.

### Modified Capabilities

None. Existing API-level ownership and upload behavior remain unchanged.

## Impact

Affected areas include database configuration, request-scoped sessions, storage dependencies, upload persistence, Supabase SQL policies, secrets, deployment, and integration tests. `add-database-migrations` must land first.
