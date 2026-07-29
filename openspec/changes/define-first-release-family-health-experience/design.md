## Context

The current backend maps an authenticated subject directly to `user_id`, requires a family profile before record creation, stores AI consent on each record, creates extraction jobs per file, and rebuilds memory by deleting and recreating report-derived facts. It has no application account/onboarding state, staged multi-part ingestion, patient matching, metric observations, external connectors, aggregate Feed, dynamic Drive, conversations, private download, or record deletion.

Three active changes already own production Postgres/private storage/RLS, a real extraction provider, and durable queue dispatch. This design depends on those boundaries and must reconcile their assumptions about profile-based object keys, one-file jobs, and review of every provider field.

## Goals / Non-Goals

**Goals:**

- Represent the first-release single-manager family model without preventing a later household membership model.
- Separate upload, assignment, extraction, and review state.
- Route reports using account-local patient matching without allowing AI output to cross ownership boundaries or silently create people.
- Store report measurements automatically while keeping them untrusted and outside medical memory and Chat.
- Preserve stable provenance for reviewed memory, metrics, Feed, Drive, Chat citations, retries, corrections, and deletion.
- Reuse provider-neutral extraction, private storage, durable worker, migration, and RLS patterns.

**Non-Goals:**

- Implement delegated family-member identities, invitations, or profile grants.
- Implement longitudinal charts or interpret unreviewed observations.
- Select a specific extraction model, conversational model, search provider, email mechanism, or WhatsApp mechanism.
- Add Chat side effects, AI-consent revocation, arbitrary family-relationship graphs, public links, account export, or account deletion.

## Decisions

### Introduce an application account above authentication identities

Map each verified authentication identity to one application account. Keep Google and email/password identity details in the authentication boundary and never persist passwords in application tables. The account owns profiles and every private derived resource.

Create onboarding progress idempotently and enforce a unique `self` profile per account. Age and weight are reported observations with `reported_at`; weight retains its original value/unit and a normalized kilogram value. Conditions and medications typed by the manager use explicit `user_attested` provenance rather than pretending to originate in a report.

This leaves room for multiple linked authentication identities without relying on one immutable `login_mode`. The future delegated-access change can introduce household memberships and profile grants without turning a family profile into a login identity.

### Store versioned account consent and snapshot it on AI work

Store consent evidence with account, actor, accepted scope, policy version, and timestamp. The presented scope covers document extraction and sending reviewed personal memory to Chat. Every ingestion and conversation provider request snapshots the governing consent evidence.

The absence of accepted consent prevents provider dispatch but does not prevent private file storage. Direct uploads without extraction resolve to their user-selected profile; external imports without a preselection require manual assignment. Revocation behavior is deliberately deferred, while the schema remains capable of adding a later revocation timestamp and policy.

### Stage ingestion before creating a profile-bound report

Do not make `profile_id` a prerequisite for receiving private content. Introduce an account-owned ingestion aggregate:

```text
Upload:      receiving ──▶ complete | failed
Assignment:  provisional ──▶ resolved | needs_assignment
Extraction:  queued ──▶ extracting ──▶ ready | failed
Review:      not_required | pending ──▶ reviewed
```

The aggregate contains ordered source parts, source channel, optional user context, provisional profile, consent snapshot, external deduplication key, and lifecycle timestamps. A single image/PDF is one part; a multi-image report has ordered parts and finalizes atomically as one logical document.

Feed eligibility depends only on upload completion. Profile-scoped Drive, observations, memory, and Chat evidence require resolved assignment. This avoids overloading one record status with independent state dimensions.

Use stable account plus ingestion/record object keys, not provisional profile IDs. This must be reconciled with `adopt-supabase-data-boundary` before its private-storage tasks commit profile-bearing keys.

### Treat direct-upload selection as provisional patient context

Extraction emits patient-name evidence with normalized value, confidence, and source location. Matching runs only against profiles and aliases owned by the same account:

- One sufficiently confident existing-profile match resolves to that profile, even if it differs from the direct-upload selection.
- No match or multiple plausible matches becomes `needs_assignment`.
- External intake begins without a provisional profile and follows the same matching rule.
- The system never queries other accounts or creates a family profile solely from extracted output.

Retain the provisional selection, extracted value, confidence, match version, resolved profile, and resolver for audit. Publish observations and candidate memory only after assignment resolves. Future correction or reassignment must move every profile-scoped derived row transactionally and rebuild active projections.

The exact normalization and confidence threshold are configurable evaluation results rather than product-spec constants.

### Split extraction output into three trust classes

Keep raw provider output and normalized source references, then classify normalized items as:

1. `patient_evidence` for assignment;
2. `metric_observation` for literal report values;
3. `memory_candidate` for conditions, medications, follow-ups, and inferred insights.

Metric observations store decimal or categorical original value, original unit, optional canonical value/unit, reference range, observed date, optional body-system classification, source report/page/location, extraction attempt, confidence, and quality state. They publish automatically after assignment but remain `unreviewed_extracted`, are correctable/excludable, and are never trusted medical memory or Chat evidence.

Memory candidates are selected by default in the client, but selection has no trust effect until the manager submits review. On submit, selected candidates become confirmed, edited candidates retain original and replacement values, and unchecked candidates become ignored.

Use stable/versioned memory facts or explicit supersession instead of destructive delete-and-recreate behavior so Chat and appointment citations remain resolvable.

### Make retries attempt-aware and idempotent

One extraction job targets one complete logical document, not one physical image part. Every published observation and candidate retains an attempt identity. Retry stages a new result set, supersedes matching active observations rather than duplicating them, preserves prior review decisions where safe, and commits one atomic normalized result.

Update `add-production-extraction-provider` so only memory and trusted-metadata candidates require review; patient evidence and observations remain untrusted but use their own workflows. Update `add-queue-backed-extraction-worker` to claim logical-document attempts.

### Build Feed and Drive as account-owned query projections

Feed queries all upload-complete ingestions for the account. It supports:

- upload completion descending; or
- trusted report date descending, followed by undated items.

Stable IDs break timestamp ties. A completed `needs_assignment` item appears in Feed with an attention state but nowhere profile-scoped.

Drive first resolves one profile when the account has multiple profiles, then computes virtual month or reviewed-condition groups. It does not create or move storage folders. Condition groups use reviewed memory linked to reports; a report may appear in multiple groups while the source file remains singular.

### Separate original identity from display naming

Retain immutable original filenames and object identities. Store a mutable display filename for Feed, Drive, and report detail. Extraction may propose a descriptive name only from trusted metadata; an explicit user rename wins over later generated suggestions.

Download authorizes ownership at request time and either streams the private object or issues a narrowly scoped, short-lived private read result without returning a public URL or internal key.

Delete immediately tombstones the report and revokes read access, stops pending work, then uses idempotent cleanup/outbox processing to purge private objects and derived fields, observations, and report-derived active memory. Existing Chat citations retain only a non-PHI `source unavailable` tombstone.

### Use one ingestion contract for direct, email, and WhatsApp sources

Connector adapters translate authorized source deliveries into the staged-ingestion contract. Store account ownership, connector/source type, safe external identifiers, receipt time, attachment identity, and an idempotency key. Do not use filename alone for deduplication.

Connector secrets stay in an appropriate encrypted secret boundary and never enter API responses or queue payloads. Unsupported or incomplete deliveries remain failure events and never appear as completed Feed items.

The email and WhatsApp mechanisms are provider-specific implementation choices; the product contract requires authorization, private account association, supported attachment intake, status visibility, and replay safety.

### Give Chat independent provider and retrieval boundaries

Do not reuse the extraction interface for Chat. Define separate conversational-model and external-retrieval ports. Each conversation has immutable account/profile scope and ordered messages with pending, complete, or failed state.

Personal retrieval uses only reviewed or user-attested memory for the selected profile. External retrieval minimizes direct identifiers and unrelated medical context. Persist actual personal citations and fetched external URLs; never accept model-invented URLs as citations. Store provider/model/version snapshots for diagnostics while keeping API behavior provider-neutral.

Model generation and external retrieval are separately configurable so either can fail closed or be rolled back without changing conversation ownership or history.

### Extend database ownership and integrity below the API

Add migrations for accounts, consent evidence, onboarding/profile health context, ingestion aggregates and parts, assignment evidence, observations and correction history, connector state/import events, conversations/messages/citations, display naming, deletion state, and stable memory provenance.

Every new private table receives explicit account ownership, owner-aware foreign keys or constraints, RLS policy coverage, and two-account isolation tests. Eliminate pseudo-foreign-key paths that could leave cross-profile or orphaned derived data.

## Risks / Trade-offs

- Incorrect patient matching could place medical data under the wrong person → match only inside the account, require one high-confidence result, retain evidence, block publication when ambiguous, and support audited correction.
- OCR-derived numeric values can still be wrong → label observations unreviewed, retain page/source evidence, allow correction/exclusion, and exclude them from memory and Chat.
- Account-level consent could be interpreted more broadly over time → version the scope and snapshot it on every provider-bound operation.
- Multi-image reports increase upload and retry complexity → finalize an ordered logical document atomically before queue dispatch.
- Email and WhatsApp intake expand sensitive-data and replay exposure → use authorized account-bound adapters, minimal metadata, idempotency keys, private queues, and redacted logs.
- External Chat retrieval can leak identifiers or import misinformation → de-identify queries, separate external from personal evidence, retain actual links, and state unsupported conclusions.
- Hard deletion spans database, queue, storage, and citations → revoke synchronously, purge through idempotent cleanup, and retain only non-PHI tombstones.
- Age becomes stale and weight changes → retain reported dates and treat both as observations rather than timeless demographics.
- The change is large and overlaps active infrastructure work → land in dependency slices and update active deltas before their conflicting storage, provider, or queue tasks.

## Migration Plan

1. Reconcile the three active infrastructure changes with stable ingestion keys, logical-document jobs, classified extraction output, private download, and all new RLS tables.
2. Add account, consent, unique-`self`, profile health-context, and provenance structures using expand-only migrations.
3. Backfill one application account for each existing authenticated owner and link existing profiles without automatically inferring account consent from legacy record booleans.
4. Add staged ingestion and ordered parts; dual-read existing profile-bound records while new uploads use the staged path.
5. Adapt private storage and queue dispatch to stable logical-document identity.
6. Add account-local patient matching and block derived publication until assignment resolves.
7. Add observations, candidate-memory classification, stable facts, and retry supersession; migrate existing test-result fields without silently treating them as verified.
8. Add Feed, Drive, report download/rename/delete, connectors, and Chat in independently feature-flagged slices.
9. Validate migration results, owner constraints, RLS, private storage, cleanup, and cross-account isolation before enabling each slice.
10. After compatibility windows and successful backfills, remove obsolete per-record consent inputs and destructive memory-rebuild paths.

Rollback disables new entry points and provider dispatch, keeps new tables intact, and returns reads to the last compatible path. It MUST NOT drop ingested documents, consent evidence, observations, conversations, or audit provenance. Any rollback after deletion begins continues cleanup so tombstoned private content does not become accessible again.

## Open Questions

- Which supported image/PDF formats, size limits, and page limits pass provider evaluation?
- Which patient-name normalization, alias, and confidence policy meets the required matching accuracy?
- Which controlled metric/body-system vocabulary should populate optional observation classifications?
- Which email, WhatsApp, conversational-model, and external-retrieval adapters satisfy privacy, retention, latency, and cost constraints?
- Which product ranges and refresh cadence apply to reported age and weight?
