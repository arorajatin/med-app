## Context

The backend resides in `apps/api`, while the V1 user interface resides in `apps/web`. It maps authenticated identities to application accounts, derives onboarding progress from account-owned profile data, stages authenticated logical-document uploads, creates extraction jobs, and rebuilds memory from trusted facts. Aggregate Feed, dynamic Drive, conversations, private download, and record deletion remain pending. Native clients are deferred to separate V2 changes and their future `apps/ios` and `apps/android` homes are not scaffolded in V1.

Baseline commit `8a1e0bd662cc231532c5b91248819e9294c4f8cb` adds a fail-closed condition-safety boundary. The built-in mock may persist only the closed set of baseline non-condition fields; every condition-shaped or unknown field, every field from another extractor implementation, and unrestricted provider raw output are omitted before persistence. Extraction, review, memory, and appointment reads expose only that permitted baseline. This is the current safety boundary, not the source-cited `documented_condition_candidate` contract designed below.

Three active changes own production Postgres/private storage/RLS, the selected production extraction pipeline, and durable queue dispatch. Their planning artifacts are reconciled with this design around Mumbai storage, stable ingestion-based object keys, immutable logical-document attempts, four trust classes, and bounded retention.

## Goals / Non-Goals

**Goals:**

- Represent the first-release single-manager family model without preventing a later household membership model.
- Separate upload, assignment, extraction, and review state.
- Route reports using account-local patient matching without allowing AI output to cross ownership boundaries or silently create people.
- Store report measurements automatically while keeping them untrusted and outside medical memory and Chat.
- Extract condition text that a prescription or lab report explicitly states, retain its exact source, and require review before trusted use.
- Preserve stable provenance for reviewed memory, metrics, Feed, Drive, Chat citations, retries, corrections, and deletion.
- Reuse provider-neutral extraction, private storage, durable worker, migration, and RLS patterns.
- Keep the V1 client in `apps/web` and the server and workers in `apps/api`, without introducing native-client implementation into this change.
- Keep V1 clinical-document storage, queues, OCR, and model processing in `ap-south-1` Mumbai.

**Non-Goals:**

- Implement delegated family-member identities, invitations, or profile grants.
- Implement longitudinal charts or automatically treat an interpretation of an unreviewed observation as a medical fact.
- Infer, classify for users, or rule out a condition from medication identity, dosage, lab values, ranges, symptoms, or any other implicit association.
- Select a conversational model or external search provider.
- Implement document ingestion through email, Amazon SES, WhatsApp, or any other external connector. External connector ingestion requires a separate post-V1 change covering provider selection, account linking, authentication, source authorization, grouping, replay protection, and regional review.
- Add Chat side effects, post-creation AI-processing controls, arbitrary family-relationship graphs, public links, account export, or account deletion.

## Decisions

### Introduce an application account above authentication identities

Map each verified authentication identity to one application account. Keep Google and email/password identity details in the authentication boundary and never persist passwords in application tables. The account owns profiles and every private derived resource.

Create onboarding progress idempotently and enforce a unique `self` profile per account. Age and weight are reported observations with `reported_at`; they are not timeless demographics or clinical assessments. Reported age is a whole number of completed years from 0 through 130 inclusive. Weight accepts a positive decimal in `kg` or `lb` only when its unrounded normalized value is from 0.5 through 500 kilograms inclusive. Retain the entered decimal and unit unchanged. Normalize pounds with the exact conversion `1 lb = 0.45359237 kg` using decimal arithmetic, without binary floating point, intermediate rounding, or independently rounded pound boundaries; presentation rounding never overwrites the stored values.

Display the latest accepted age and weight with their reported dates and never silently increment age or derive either value. A reported age becomes due for a non-blocking refresh one calendar year after `reported_at`; a reported weight becomes due after six calendar months. A stale value remains visible with its reported date and a refresh prompt until replaced by a newly reported value. These deliberately broad limits and cadence are input-quality and recency controls only: the product does not label an accepted value healthy, unhealthy, plausible, or diagnostic. Conditions and medications typed by the manager use explicit `user_attested` provenance rather than pretending to originate in a report.

This leaves room for multiple linked authentication identities without relying on one immutable `login_mode`. The future delegated-access change can introduce household memberships and profile grants without turning a family profile into a login identity.

### Identify a profile without a date of birth

A family profile carries no date of birth and no year of birth. Reported age with its `reported_at` date is the only age context stored on the profile. That is enough for profile display and for understanding the person's health information, and it keeps a directly identifying date out of profile metadata. Uploaded source documents and source-linked patient evidence may still retain a date of birth. Patient matching uses names and explicit aliases only.

### Treat account creation as authorization for required AI processing

AI processing is inherent to the product. Creating an account authorizes document extraction and use of reviewed personal memory in Chat, and signup must state that boundary clearly. The application stores no separate consent row, onboarding has no consent step, and ingestions and provider requests carry no repeated consent snapshot or prompt. Post-creation processing controls are deferred to a separate change.

### Stage ingestion before creating a profile-bound report

Do not make `profile_id` a prerequisite for receiving private content. Introduce an account-owned ingestion aggregate:

```text
Upload:      receiving ──▶ complete | failed
Assignment:  provisional ──▶ resolved | needs_assignment
Extraction:  queued ──▶ extracting ──▶ ready | failed
Review:      not_required | pending ──▶ reviewed
```

The aggregate contains ordered source parts, immutable source provenance, optional user context, provisional profile, and lifecycle timestamps. `SourceChannel` is exactly `direct_file` or `camera`. A single image/PDF is one part; a multi-image report has ordered parts and finalizes atomically as one logical document.

Each `IngestionSource` retains account, channel, receipt time, authenticated actor identity, source-part ordinal, original filename, detected MIME type, byte count, SHA-256, and grouping identity. The authenticated file-upload and browser-camera routes stamp their own channel from route context; clients cannot choose or override it. Completed source provenance is immutable.

Feed and owned report detail expose the route-stamped source channel. An original upload filename is never treated as the document issuer: issuer, report date, and display-name suggestions are review-required document metadata extracted from the source itself.

Feed eligibility depends only on upload completion. Profile-scoped Drive, observations, memory, and Chat evidence require resolved assignment. This avoids overloading one record status with independent state dimensions.

Use stable account plus ingestion/record object keys, not provisional profile IDs. `adopt-supabase-data-boundary` uses the same stable key contract so assignment and reassignment never move a private object.

### Treat direct-upload selection as provisional patient context

Extraction emits literal patient-name evidence with an optional patient identifier, optional date of birth when present in the document, confidence, and a required source reference. The extracted date of birth remains document evidence; it is not copied to a profile and is not an assignment input. Matching runs only against profiles and explicit aliases owned by the same account:

- Normalize candidate and stored names with Unicode NFKC, case-folding, trimming, and whitespace collapse without dropping name tokens.
- One exact full-name or explicit-alias match resolves only when exactly one owned profile matches, even if it differs from the direct-upload selection.
- No exact match or more than one exact match becomes `needs_assignment`. The provisional selection alone never resolves a document.
- The system never queries other accounts or creates a family profile solely from extracted output.

Retain the provisional selection, extracted value, confidence, match version, resolved profile, and resolver for audit. Publish observations and candidate memory only after assignment resolves. Future correction or reassignment must move every profile-scoped derived row transactionally and rebuild active projections.

Fuzzy, scored, phonetic, or cross-account matching is not permitted in V1. Confidence is retained for audit and evaluation but cannot relax the exact-match rule.

### Split extraction output into four trust classes

Keep raw provider output and normalized source references, then classify normalized items as:

1. `patient_evidence` for assignment;
2. `document_metadata_candidate` for document type, report date, issuer, and display-name suggestions;
3. `metric_observation` for literal lab-report values;
4. `memory_candidate` for literal prescription medications and instructions plus conditions explicitly written in the source document.

Patient evidence is used only for account-local assignment. Document metadata requires account-manager confirmation or edit before it can drive trusted report-date ordering, issuer display, or a generated display name. V1 never deduces a condition, diagnosis, follow-up, or clinical interpretation from medication identity, dosage, lab values, ranges, symptoms, or general medical knowledge. It may create a `documented_condition_candidate` memory-candidate subtype only when the submitted prescription or lab report affirmatively states that the patient has the literally named condition. Negated or ruled-out conditions, screening statements, uncertainty, family history, and statements about someone other than the patient are omitted.

V1 has no condition-severity classification or non-life-threatening-condition allowlist. Any future allowlist requires a separate reviewed change with a human-owned, versioned policy, effective dates, audited matching rules, and fail-closed behavior. The model never decides whether a condition is life-threatening.

Metric observations store decimal or categorical original value, original unit, optional canonical value/unit, reference range, observed date, optional body-system classification, source report/page/location, extraction attempt, confidence, and quality state. They publish automatically after assignment but remain `unreviewed_extracted`, are correctable/excludable, and are never trusted medical memory or Chat evidence. A measurement cannot support creation of a condition candidate unless the document separately states that condition in literal text.

Prescription memory candidates retain medication name, strength, dosage form, dose, route, frequency, duration, and literal instructions when present. They are selected by default in the client, but selection has no trust effect until the manager submits review. On submit, selected candidates become confirmed, edited candidates retain original and replacement values, and unchecked candidates become ignored.

A documented-condition candidate retains the exact extracted condition text, the exact cited text span and page/location, extraction attempt, and confidence. The client presents it as **Condition written in this document — verify before saving** and requires an explicit `confirm`, `edit`, or `ignore` decision. Confirmation retains the literal value; an edit retains both original and replacement values; ignored candidates remain outside trusted memory, Chat evidence, and Drive condition groups.

Use stable/versioned memory facts or explicit supersession instead of destructive delete-and-recreate behavior so Chat and appointment citations remain resolvable.

Every normalized item has at least one `SourceReference` containing source part, logical page, native word or Textract block identifiers, text span, and normalized bounding polygon. Each documented-condition candidate must cite the exact source span that contains the condition itself; a medication name, measurement, abnormal flag, symptom, or generic association is not a valid condition reference. Missing, fabricated, inferred, or unresolved condition text invalidates that candidate. Successful raw native/Textract output and Bedrock response are encrypted, hidden from routine APIs, and retained until report deletion for audit; provider staging copies are deleted promptly.

The baseline gate remains in force until this structured contract, resolvable source-span validation, protected raw-output storage, negative fixtures, and reviewed enablement evidence all land together. The future candidate path must replace the gate atomically with the source-validating contract; widening the baseline field allowlist is prohibited. Generic `condition`, `diagnosis`, and other condition-shaped field types remain invalid.

### Select the V1 document-processing path deterministically

V1 accepts English-language, unencrypted PDF, JPEG, and PNG documents and extracts only lab reports and prescriptions. Product ceilings are 15,000,000 bytes per logical document, 20 pages or parts, 10,000,000 bytes per image, and 10,000 pixels per image dimension. A valid but unsupported medical-document family remains privately stored with `unsupported_document_type` and publishes no derived data.

Use `pdfplumber` for a PDF only when every nonblank page opens successfully, contains at least 20 positioned word tokens, contains at least 99 percent printable extracted characters, keeps every token bounding box inside the page, and contains no raster image covering 50 percent or more of the page. If any page fails, route the whole PDF to Amazon Textract; never mix native and OCR pages in one attempt. JPEG/PNG and ordered image sets always use Textract. Record `processing_method` as `native_text` or `textract_ocr` plus the routing reason.

Textract runs in `ap-south-1` using layout, tables, and forms. Asynchronous PDF processing uses KMS-encrypted Mumbai S3 input/output, SNS completion, and SQS delivery with customer-controlled `OutputConfig`; staging/output is deleted immediately after persistence with a 24-hour lifecycle backstop. Queue and notification payloads carry opaque internal identifiers and object references, never document bytes or extracted text.

Normalize native or Textract text/layout into stable source blocks, then invoke Amazon Bedrock Mistral Large 3 model `mistral.mistral-large-3-675b-instruct` through its in-region Mumbai endpoint with schema-constrained output. The prompt contains document blocks and schema instructions, never the account's profile list; matching remains local. Production requires effective `data_retention_mode: none`, an IAM/SCP guard against relaxation, and a preflight proving the model permits zero-data-retention for the account. Otherwise extraction fails closed with no cross-region or alternate-provider fallback.

### Make retries attempt-aware and idempotent

One extraction job targets one complete immutable logical document, not one physical image part. Every published observation and candidate retains an attempt identity. Each attempt either commits raw output plus one complete validated normalized result or publishes nothing. Transient timeout, throttling, and provider 5xx failures receive at most three total attempts with jittered delays of 30 seconds and two minutes. Invalid input, unsupported document type, schema failure, or invalid source references are terminal. A retry stages a new result set, supersedes matching active observations rather than duplicating them, preserves prior review decisions where safe, and commits atomically.

Update `add-production-extraction-provider` so document metadata and memory candidates require review while patient evidence and observations remain untrusted in their own workflows. Update `add-queue-backed-extraction-worker` to claim immutable logical-document attempts and represent native parsing, Textract submission/callback, Bedrock structuring, and normalization phases.

Production extraction remains undeployed until provider privacy approval, Mumbai placement, Bedrock ZDR availability, migrations/RLS, and de-identified English fixtures pass. The approved held-out gate requires zero false automatic profile assignments, at least 99.5 percent exact precision for published lab analyte/value/unit/source-page tuples, at least 99.5 percent correct source-page attribution, zero unanchored or fabricated published observations, at least 95 percent precision for prescription memory candidates, and zero documented-condition candidates whose condition text is absent from the cited source span. Recall is reported but omission is safer than publishing an unsupported or inferred value and is not a blocking floor for V1.

### Build Feed and Drive as account-owned query projections

Feed queries all upload-complete ingestions for the account. It supports:

- upload completion descending; or
- trusted report date descending, followed by undated items.

Stable IDs break timestamp ties. A completed `needs_assignment` item appears in Feed with an attention state but nowhere profile-scoped.

Drive first resolves one profile when the account has multiple profiles, then computes virtual month or trusted-condition groups. It does not create or move storage folders. A condition group uses only a user-attested condition explicitly linked to the report or a confirmed or edited `documented_condition_candidate` extracted from that report. Pending or ignored candidates and conditions merely associated with medication details, lab observations, symptoms, or general knowledge create no group. A report may appear in multiple trusted groups while the source file remains singular.

### Separate original identity from display naming

Retain immutable original filenames and object identities. Store a mutable display filename for Feed, Drive, and report detail. Extraction may propose a descriptive name as a review-required metadata candidate; only a confirmed or edited candidate may become the generated display name, and an explicit user rename wins over later suggestions.

Download authorizes ownership at request time and either streams the private object or issues a narrowly scoped, short-lived private read result without returning a public URL or internal key.

Delete immediately tombstones the report and revokes read access, stops pending work, then uses idempotent cleanup/outbox processing to purge private objects and derived fields, observations, and report-derived active memory. Existing Chat citations retain only a non-PHI `source unavailable` tombstone.

### Give Chat independent provider and retrieval boundaries

Do not reuse the extraction interface for Chat. Define separate conversational-model and external-retrieval interfaces with replaceable adapters. Each conversation has immutable account/profile scope and ordered messages with pending, complete, or failed state.

Personal retrieval uses only reviewed or user-attested memory for the selected profile. External retrieval minimizes direct identifiers and unrelated medical context. Persist actual personal citations and fetched external URLs; never accept model-invented URLs as citations. Store provider/model/version snapshots for diagnostics while keeping API behavior provider-neutral.

Model generation and external retrieval are separately configurable so either can fail closed or be rolled back without changing conversation ownership or history.

### Extend database ownership and integrity below the API

Add migrations for accounts, onboarding/profile health context, ingestion aggregates and parts, assignment evidence, observations and correction history, documented-condition candidates and their review history, conversations/messages/citations, display naming, deletion state, and stable memory provenance.

Every new private table receives explicit account ownership, owner-aware foreign keys or constraints, RLS policy coverage, and two-account isolation tests. Eliminate pseudo-foreign-key paths that could leave cross-profile or orphaned derived data.

## Risks / Trade-offs

- Incorrect patient matching could place medical data under the wrong person → require exactly one normalized full-name or explicit-alias match inside the account, retain evidence, block publication otherwise, and support audited correction.
- OCR-derived numeric values can still be wrong → label observations unreviewed, retain page/source evidence, allow correction/exclusion, and exclude them from memory and Chat.
- OCR or model output could invent or misread a documented condition → require the condition words themselves in a resolvable source span, label the item as extracted from the document, require explicit confirmation or edit, and forbid medication-to-condition or lab-value-to-condition deductions.
- Required AI processing could surprise a new account holder → state it clearly during signup and provide no misleading AI-disabled path.
- Multi-image reports increase upload and retry complexity → finalize an ordered logical document atomically before queue dispatch.
- External Chat retrieval can leak identifiers or import misinformation → de-identify queries, separate external from personal evidence, retain actual links, and state unsupported conclusions.
- Hard deletion spans database, queue, storage, and citations → revoke synchronously, purge through idempotent cleanup, and retain only non-PHI tombstones.
- Age becomes stale and weight changes → retain and display reported dates, prompt after one calendar year or six calendar months respectively, and treat both as user-reported observations rather than timeless demographics or clinical classifications.
- The change is large and overlaps active infrastructure work → land in dependency slices and update active deltas before their conflicting storage, provider, or queue tasks.

## Migration Plan

This change targets fresh installations only. Revision `20260721_0001` is the sole schema baseline for the current release. Databases produced by prototype builds are not supported inputs, and this change adds no row inventory, data import, historical transformation, or parallel historical-data path.

1. Provision an empty PostgreSQL database in `ap-south-1` and apply the current Alembic head before any API or worker starts.
2. Reconcile the three active infrastructure changes with stable ingestion keys, logical-document jobs, classified extraction output, private download, and all new RLS tables.
3. Add account, unique-`self`, profile health-context, and provenance structures through reviewed forward migrations from the sole baseline.
4. Create accounts, profiles, ingestions, and derived data only through the V1 application flows.
5. Add staged ingestion and ordered parts as the only document-ingestion persistence path.
6. Adapt private storage and queue dispatch to stable logical-document identity.
7. Add account-local patient matching and block derived publication until assignment resolves.
8. Add observations, candidate-memory classification, source-cited documented-condition review, stable facts, and retry supersession for newly ingested documents.
9. Add Feed, Drive, report download/rename/delete, and Chat as independently deployable slices.
10. Validate `ap-south-1` placement, Bedrock ZDR, provider privacy approval, current-head startup, owner constraints, RLS, private storage, cleanup, held-out extraction quality, zero inferred condition output, and cross-account isolation before enabling each slice.

Rollback disables new entry points and provider dispatch while preserving data created by the current schema. Before production launch, a disposable installation may be recreated from the sole baseline. After launch, schema corrections move forward through a reviewed revision; the service never falls back to a build whose declared Alembic head differs from the database. Any rollback after deletion begins continues cleanup so tombstoned private content does not become accessible again.

## Open Questions

- Which controlled metric/body-system vocabulary should populate optional observation classifications?
- Which conversational-model and external-retrieval adapters satisfy privacy, retention, latency, and cost constraints?
