## Context

The MVP was implemented before OpenSpec and documented through nine ADRs. Those ADRs mixed durable architectural decisions with implementation status. The migration keeps their rationale here, makes current behavior authoritative in `openspec/specs/`, and moves unfinished work into active changes.

## Goals / Non-Goals

**Goals:**

- Preserve the decisions behind the current backend.
- Establish testable living specs for implemented behavior.
- Make incomplete production work visible as future changes.

**Non-Goals:**

- Change APIs, persistence, extraction behavior, or deployment configuration.
- Claim that Supabase persistence, a production extraction provider, a durable queue, or Alembic migrations already exist.

## Decisions

### Private medical data by default

Every resource is owned by a user and application queries include that owner. Missing and unowned resources produce the same not-found response. Files are stored below a private root and their internal paths are not returned by the API. Explicit sharing remains out of scope.

### Human review before medical memory

AI output is untrusted until a user confirms or edits it. Pending, ignored, and incorrect fields cannot update memory or appointment context. Memory facts retain links to the source record and extracted field so derived information stays auditable.

### FastAPI and separate API schemas

FastAPI provides authenticated HTTP routes and upload handling, Pydantic defines request and response contracts, and Uvicorn runs the ASGI service. API schemas remain separate from SQLAlchemy models so persistence details do not leak into the client contract.

### SQLAlchemy relational model

Profiles, records, files, extraction jobs, extracted fields, memory facts, appointments, checklist items, and appointment reviews use SQLAlchemy ORM models. SQLite and metadata creation support local development and tests. Production schema evolution is deferred to the `add-database-migrations` change.

### Supabase as the intended production boundary

Supabase JWT verification is implemented for production authentication. Supabase Postgres, private object storage, and row-level security are intentionally tracked by the `adopt-supabase-data-boundary` change rather than described as current behavior.

### Provider-neutral extraction contract

Application services depend on an internal extractor interface that returns a document type, raw output, and structured fields. The current mock implementation supports deterministic local development. A real OCR or model adapter is deferred to `add-production-extraction-provider`.

### Raw and structured extraction storage

The job retains raw provider output while individual normalized fields hold reviewable values, confidence, source references, and confirmation status. This costs additional storage but preserves auditability and future reprocessing options.

### Explicit extraction jobs

Extraction has queued, extracting, ready, and failed states rather than being modeled as an opaque upload side effect. Local execution can run inline or through a single-job worker. Durable queue-backed processing is deferred to `add-queue-backed-extraction-worker`.

## Risks / Trade-offs

- Local filesystem storage is private only within the local deployment boundary -> replace it before production with the planned private object storage adapter.
- Application-level ownership checks do not protect direct database access -> add database row-level security in the production data boundary change.
- The mock extractor is not suitable for real medical documents -> keep it limited to local development and tests.
- Metadata-based schema creation is not a production migration strategy -> introduce Alembic before production database rollout.

## Migration Plan

This baseline requires no runtime migration. Future changes start from the living specs and update them through OpenSpec deltas. The former `docs/adr/` files are removed after their decisions are represented here or in active changes.

## Open Questions

- Which production document extraction provider meets privacy, accuracy, latency, and cost requirements?
- Which durable queue and worker runtime fit the deployment platform?
- What retention and deletion policy should apply to raw extraction output?
