# ADR 0001: Private By Default Medical Data

## Status

Accepted

## Implementation Status

Partial. Local ownership checks exist, but production Supabase JWT verification, RLS, and private Supabase storage are not implemented yet.

## Context

The product stores sensitive medical records for users and their family members. The first backend already models all profiles, records, files, extraction jobs, memory facts, and appointments as user-owned data.

## Decision

Medical data is private by default.

Every user-owned resource must be scoped by `user_id`, and profile/record/file access must require ownership. Uploaded files must not be exposed through public URLs.

## Consequences

Ownership checks are required in API routes and service helpers. Local development can use simple dev auth, but production must replace it with real token verification before launch.

Future sharing features need explicit consent and their own decision record.
