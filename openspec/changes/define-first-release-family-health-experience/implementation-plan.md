# V1 Implementation Execution Plan

This plan turns the approved V1 requirements into dependency-ordered delivery slices. Each numbered
step should land as a small, independently tested change. Unfinished behavior stays behind a
default-off feature flag, and an umbrella OpenSpec task is checked only when all of its acceptance
criteria are complete.

## 0. Stop unsafe condition inference

1. Remove the mock rules that turn kidney, creatinine, liver, SGPT, or SGOT keywords into a
   condition.
2. Allow only known baseline non-condition field types through the extraction persistence boundary.
   Omit generic `condition`, `diagnosis`, `documented_condition_candidate`, and every unknown field
   type until the structured V1 contract exists.
3. Exclude legacy generic condition fields from trusted-memory rebuilding and downstream appointment
   evidence.
4. Add regression cases for medication-only text, lab values/ranges/flags, symptoms, organ words,
   filenames, explicit diagnosis labels without source validation, and unknown provider field types.
5. If production data exists, inventory and quarantine legacy condition rows and their derived memory
   before enabling the new candidate path. Complete that backfill under task 7.2.

Exit gate: no current extractor output can create or restore a trusted condition fact.

This safety slice supports tasks 4.11 and 7.2 but does not complete either broad task.

## 1. Lock the V1 condition policy

The approved repository specs use literal transcription plus explicit review. V1 does not infer,
diagnose, classify, rule out, or estimate the severity of a condition, and it contains no
non-life-threatening condition allowlist.

1. Keep this literal-only boundary consistent in the proposal, design, specs, tasks, journeys, model
   schema and prompt, server validation, UI wording, and tests.
2. Call the output `Condition written in this document`, not an inferred or clinician-confirmed
   diagnosis.
3. Keep the candidate pending until the account manager confirms, edits, or ignores it.
4. Treat any future severity-based display policy or condition allowlist as a separate reviewed
   OpenSpec change.

If a later change introduces an allowlist, the model must never decide whether an ailment is
life-threatening. That change must define an accountable owner, version, effective date, matching
rules, audit history, and fail-closed behavior.

## 2. Add release controls and the core data boundary

1. Add independently controlled feature flags for web ingestion, extraction, observations,
   Feed/Drive, and Chat (task 7.3 foundation). Keep task 7.3 open until expand-and-contract
   compatibility paths exist across all slices.
2. Implement application accounts, authentication-identity mapping, onboarding progress, consent
   evidence, and one unique `self` profile (task 2.1).
3. Add reported age and unit-aware weight fields with migration coverage (task 2.2).
4. Add ingestion aggregates, ordered parts, lifecycle states, assignment evidence, consent snapshots,
   and stable object identities (task 3.1).
5. Backfill existing owners into accounts without inventing consent (task 7.1).

Exit gate: forward migration succeeds, two accounts remain isolated, and all unfinished features are
off by default.

## 3. Scaffold the V1 web client and API contract

1. Select and scaffold the web framework under `apps/web`.
2. Publish the backend OpenAPI document and generate or validate a typed web client under
   `contracts`.
3. Add authenticated routing, session restoration, error handling, and a minimal application shell.
4. Add explicit web tasks to `tasks.md`; the current task list does not fully describe frontend
   scaffolding or screens. Cover authentication/verification/sign-out, onboarding and family
   profiles, every upload mode and error state, Feed and assignment, all review screens with source
   display, observation correction and retrieval, Drive, rename/download/delete, Chat history and
   citations, generated-client drift checks, and web end-to-end tests.

Exit gate: the web app can authenticate against a local API and render a protected empty shell.

## 4. Deliver the first web-upload walking skeleton

1. Accept one PDF, JPEG, or PNG selected in the browser.
2. Send the bytes through the authenticated API; the browser must not upload directly to storage.
3. Validate detected type and the single-file limits, then store the file under an opaque private
   account-and-ingestion key (partial tasks 1.4 and 3.4).
4. Mark the logical document upload complete only after storage and metadata commit together.
5. Preserve optional user context, immutable original filename, and a separate mutable display
   filename.
6. Show the completed item in an account-owned Feed with processing disabled (task 5.1 slice).
   Keep task 5.1 open until resolved and `needs_assignment` states plus processing states exist.
7. Add cross-account, partial-upload, corrupt-content, MIME-spoof, and oversize tests.

Tasks 1.4, 3.4, 5.1, and their umbrella test tasks remain open after this walking skeleton. Multipart,
per-image dimensions, assignment states, cleanup, and the remaining matrix arrive later.

Exit gate: one user can upload and see one private file; another user receives a not-found response;
no AI provider is called.

## 5. Complete onboarding, consent, and web intake

1. Implement Google plus verified email/password registration, verification, sign-in, sign-out, safe
   retries, and idempotent account activation (task 2.3).
2. Implement resumable onboarding, idempotent `self` creation, health context, and explicit empty
   conditions/medications (task 2.4).
3. Capture versioned account-level AI consent once and snapshot it on extraction work. Keep task 2.6
   open until personal-memory Chat dispatch is also consent-gated.
4. Add browser-camera uploads with route-stamped `camera` provenance (finish task 3.2).
5. Add ordered multi-image logical documents (task 3.3).
6. Finish upload cleanup and the relevant task 3.8 test matrix.

Exit gate: every V1 web input mode produces one immutable logical document with private provenance;
email, WhatsApp, iOS, and Android remain absent.

## 6. Introduce the normalized extraction contract

1. Replace free-form extracted fields with the four classes: `patient_evidence`,
   `document_metadata_candidate`, `metric_observation`, and `memory_candidate` (task 4.1).
2. Define a structured `SourceReference` containing source part, one-based page, exact text span,
   native word or Textract block IDs, and normalized polygon.
3. Define the `documented_condition_candidate` memory subtype with original literal text, pending
   status, attempt identity, and immutable source provenance.
4. Use a deterministic fake provider first. Keep the generic legacy `condition` type prohibited.
5. Dispatch only upload-complete, consented logical documents as attempt-aware jobs (task 3.5).
6. Validate the complete normalized result before inserting any derived row.

Keep task 4.1 open through step 7, where the condition subtype's literal-reference rules become
executable and tested.

Exit gate: a fake extraction attempt either commits one fully source-valid result or publishes
nothing.

## 7. Implement literal documented-condition validation

1. Add and approve explicit assertion-context and patient-subject requirements in the OpenSpec
   artifacts before coding them; the current specs do not yet cover negation, uncertainty, or another
   person's family history.
2. Accept a candidate only from a supported prescription or lab report.
3. Resolve its source reference against immutable extracted text/layout.
4. Require the candidate value to be copied from the cited span; never translate, expand an
   abbreviation, or map it to a different diagnosis.
5. Omit medication-, dosage-, measurement-, range-, flag-, symptom-, filename-, upload-context-, or
   general-knowledge associations.
6. Omit negated, ruled-out, screening, family-history, uncertain, and non-patient statements in V1;
   omission is safer than a false candidate.
7. Apply the locked literal-only V1 policy from step 1.
8. Keep every accepted candidate pending and unselected.

Exit gate: held-out negative fixtures produce zero condition candidates, and every positive fixture
has an exact resolvable source span.

## 8. Resolve patient assignment before publication

1. Add profile-alias persistence/management, then implement Unicode NFKC/case-folded exact full-name
   and explicit-alias matching (task 1.5).
2. Resolve only one account-local match with no contradictory DOB (task 3.6).
3. Send unmatched, ambiguous, fuzzy-only, or contradictory results to `needs_assignment`.
4. Add manual assignment without creating an AI-generated profile and publish eligible staged data
   after resolution (task 3.7).
5. Publish no profile-scoped observation or candidate before assignment resolves.

Exit gate: two-account and ambiguous-name tests prove that derived data cannot reach the wrong
profile.

## 9. Build observations, review, and trusted memory

1. Add source-linked, attempt-aware metric observations (task 4.4).
2. Add document-metadata review, including trusted issuer/type/date/name effects and explicit-rename
   precedence (task 4.3).
3. Add prescription medication/instruction candidate review (task 4.7).
4. Add documented-condition `confirm`, `edit`, or `ignore` review with the exact label and source
   display (task 4.8). Never preselect it.
5. Preserve original and replacement values, reviewer, time, source record, candidate, and source
   reference. A source reference supports only the original document text, never a user's edited
   replacement.
6. Add basic observation publication, correction, exclusion, source-report reads, and longitudinal
   profile/metric queries (tasks 4.5 and 4.6). Keep task 4.5 open until durable retry supersession is
   proven in step 10.
7. Build memory only from user-attested facts and confirmed or edited candidates; exclude pending or
   ignored conditions and every unreviewed observation (tasks 4.9 and 2.5). Keep task 4.9 open until
   appointment, Drive, and Chat citation consumers preserve supersession correctly.
8. Mark record review complete only when no memory candidate remains pending; observations never
   block completion (task 4.10).
9. Quarantine or classify legacy extracted values and memory (task 7.2).

Exit gate: pending or ignored conditions cannot reach memory, appointments, Drive, or Chat; confirmed
or edited candidates retain full audit provenance.

## 10. Add production extraction and the durable worker

1. Implement the all-pages `pdfplumber` native-text gate and whole-document Textract fallback
   (task 4.2).
2. Implement Textract-only image processing and ordered multi-image input.
3. Add Bedrock Mistral Large 3 schema-constrained normalization in `ap-south-1` (task 1.2).
4. Add immutable logical-document attempts, callbacks, atomic persistence, and bounded retries
   (task 1.3).
5. Complete observation retry supersession without duplicate active values (finish task 4.5).
6. Enforce Mumbai resources, approved endpoints, KMS, staging cleanup, and zero-data-retention
   preflight.
7. Keep production extraction disabled until provider privacy approval and fixture gates pass.

Exit gate: transient failures retry safely, terminal failures publish nothing, and no medical data
leaves the approved boundary.

## 11. Finish Feed, Drive, and report controls

1. Add Feed ordering and cursor pagination (task 5.2).
2. Add display-name rename while preserving original identity (task 5.4).
3. Add authorized private download without keys or public URLs (task 5.5).
4. Add month and trusted-condition Drive projections only after reviewed condition provenance exists
   (task 5.3).
5. Add immediate tombstoning, work cancellation, derived-data invalidation, and object purge. Keep
   task 5.6 open until the conversation/citation schema in step 12 supports non-PHI citation
   tombstones.
6. Keep task 5.7 open until step 12 also tests deletion-citation behavior.

Exit gate: rename, download, grouping, deletion, and retry cleanup work without exposing or duplicating
private files.

## 12. Add Chat last

1. Add profile-scoped conversations, messages, citations, lifecycle state, and their RLS policies
   (task 6.1).
2. Add independent model and external-retrieval interfaces that fail closed (task 6.2).
3. Persist immutable explicit profile selection and retrieve only reviewed or user-attested memory for
   that profile (task 6.3).
4. Minimize identifiers in external retrieval, distinguish personal from external evidence, persist
   actual links, and reject fabricated citations (task 6.4).
5. Add safe failure/retry, retained history, and source-unavailable behavior (task 6.5).
6. Complete the consent, attribution, isolation, deletion, and provider-failure matrix (task 6.6).
7. Finish Chat-side consent snapshots in task 2.6, stable/superseded citation behavior in task 4.9,
   non-PHI report-deletion citation tombstones in task 5.6, and the remaining task 5.7 cases.

Exit gate: Chat cannot use pending conditions, unreviewed observations, another profile's memory, or
fabricated citations.

## 13. Run the production release gate

1. Complete every task 1.1 clause: Mumbai placement, stable account/ingestion object keys, private
   download, ownership constraints, and RLS for every final private table.
2. Finish the umbrella authorization and lifecycle matrices in tasks 2.7, 3.8, 4.11, 5.7, and 6.6.
3. Pass the de-identified extraction quality gates in task 4.12.
4. Verify RLS in local and disposable Supabase environments (task 7.4).
5. Exercise migration, rollback, tombstone cleanup, and re-enable paths (task 7.5).
6. Complete requirement-to-test traceability (task 9.1), record the full test run (task 9.2), rerun
   strict OpenSpec validation, and finish the privacy/AI-trust review (task 9.4).

Exit gate: every V1 requirement has automated evidence, all safety gates pass, and the final review
records the exact release commit.

## Outside the V1 critical path

Tasks 8.1 through 8.6 are follow-up proposals. Delegated family access, interactive metric charts,
email, WhatsApp, iOS, Android, consent revocation, Chat actions, and account export/deletion must remain
separate from the V1 implementation path. Before archiving this active change, either complete those
proposal-only tasks or move them into separately tracked roadmap changes so V1 completion is honest.
