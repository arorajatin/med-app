# ADR 0005: Use Supabase Production Boundary

## Status

Accepted

## Implementation Status

Partial. Supabase JWT verification is wired for production auth. The code still uses SQLite and local file storage; Supabase Postgres, private Storage, and RLS policy setup are pending.

## Context

The MVP needs authentication, Postgres storage, private file storage, and ownership enforcement without building all infrastructure from scratch.

## Decision

Use Supabase as the production boundary for auth, Postgres, private storage, and row-level ownership rules.

Keep local development runnable with SQLite, local private storage, and dev auth.

## Consequences

Current local adapters are development conveniences, not the final production implementation. Before production, the backend needs Supabase JWT verification, Supabase private storage integration, and database migrations targeting Postgres.
