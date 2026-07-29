## 1. Reconcile Active Change Boundaries

- [ ] 1.1 Update the Supabase data-boundary plan to use stable account-and-ingestion object keys, include private download, and apply RLS to every new owner-scoped table before its conflicting storage tasks proceed.
- [ ] 1.2 Update the production-extraction-provider plan to emit patient evidence, unreviewed observations, and review-required memory candidates instead of marking every normalized item pending.
- [ ] 1.3 Update the queue-backed-worker plan so one claimed job targets one finalized logical document and one attempt, including ordered multi-image input.
- [ ] 1.4 Evaluate and record the first supported image/PDF formats, size/page limits, extraction fixtures, and safe failure behavior.
- [ ] 1.5 Evaluate and record account-local patient-name normalization, profile aliases, confidence thresholds, and ambiguous-match fixtures.

## 2. Accounts, Onboarding, Profiles, and Consent

- [ ] 2.1 Add migration-backed application accounts, authentication-identity mapping, onboarding progress, versioned consent evidence, and a uniqueness constraint for one `self` profile per account.
- [ ] 2.2 Add age and reported time plus original/normalized weight and unit fields with validation and migration coverage.
- [ ] 2.3 Implement Google and email/password registration, email verification, verified sign-in, sign-out, safe retries, and idempotent account activation.
- [ ] 2.4 Implement resumable onboarding that creates or reuses `self`, captures health context, and records explicit empty conditions or medications.
- [ ] 2.5 Implement user-attested condition and medication provenance and immediate trusted-memory creation.
- [ ] 2.6 Implement versioned account-level consent checks and snapshots for extraction and personal-memory Chat dispatch.
- [ ] 2.7 Add authorization, validation, duplicate-activation, onboarding-resume, consent-gating, and two-account isolation tests for every requirement in account onboarding, family profiles, and access control.

## 3. Staged Logical Document Ingestion

- [ ] 3.1 Add migration-backed ingestion, ordered part, source provenance, orthogonal lifecycle, assignment evidence, consent snapshot, and stable private-object identity.
- [ ] 3.2 Implement single-image/PDF and camera-capture receipt through the staged private-upload contract.
- [ ] 3.3 Implement ordered multi-image assembly that finalizes exactly one logical document atomically.
- [ ] 3.4 Implement optional user context, immutable original filename, mutable display filename, upload completion, and safe partial-upload cleanup.
- [ ] 3.5 Adapt extraction dispatch so only upload-complete logical documents with accepted consent create one attempt-aware job.
- [ ] 3.6 Implement account-local patient matching in which one confident extracted match replaces the provisional selection and ambiguous or unmatched results become `needs_assignment`.
- [ ] 3.7 Implement manual pending-assignment resolution without AI-created profiles and publish derived data only after assignment resolves.
- [ ] 3.8 Add supported, multipart, partial, unsupported, oversized, no-consent, match, mismatch, ambiguous, manual-resolution, authorization, and retry tests for every medical-record and ingestion requirement.

## 4. Extraction, Observations, and Reviewed Memory

- [ ] 4.1 Extend the normalized extractor contract with processing method, patient evidence, metric observations, candidate-memory items, and page/source provenance.
- [ ] 4.2 Implement text, OCR/vision, and hybrid logical-document processing through the provider-neutral extraction boundary.
- [ ] 4.3 Add migration-backed observations with original and normalized values/units, ranges, dates, optional body-system classification, source locations, attempt identity, confidence, and quality state.
- [ ] 4.4 Implement automatic observation publication only after successful extraction and resolved assignment, with retry supersession that prevents duplicate active values.
- [ ] 4.5 Implement observation correction, exclusion, source-report reads, and longitudinal profile/metric queries.
- [ ] 4.6 Replace field-wide review with explicit candidate-memory review in which default selection has no trust effect until submit, selected items confirm, edits preserve provenance, and unchecked items become ignored.
- [ ] 4.7 Update memory generation to include reviewed candidates and user-attested facts, exclude observations, and preserve stable or superseded citations when decisions change.
- [ ] 4.8 Update record-review completion so only pending candidate-memory items block completion.
- [ ] 4.9 Add processing-mode, patient-evidence, output-classification, atomic-result, observation, retry, correction, exclusion, review, user-attestation, citation, and cross-account tests for every extraction, observation, and memory requirement.

## 5. Feed, Drive, and Report Management

- [ ] 5.1 Implement account-wide Feed queries for upload-complete records, including resolved and attention-required items plus processing state.
- [ ] 5.2 Implement stable newest-first upload-date and trusted-report-date ordering, undated placement, tie-breaking, and cursor pagination.
- [ ] 5.3 Implement Drive profile selection and virtual month, undated, reviewed-condition, and uncategorized projections without duplicating files.
- [ ] 5.4 Implement user display-name rename while preserving original filename and object identity.
- [ ] 5.5 Implement authorized private download without public URLs or storage-key disclosure.
- [ ] 5.6 Implement immediate report tombstoning, work cancellation, derived-data invalidation, idempotent private-object purge, and non-PHI citation tombstones.
- [ ] 5.7 Add Feed inclusion/order/pagination, Drive grouping, rename, download, delete, cleanup retry, citation tombstone, and two-account isolation tests for every Feed, organization, and report-management requirement.

## 6. Email and WhatsApp Ingestion

- [ ] 6.1 Select privacy-approved email and WhatsApp intake mechanisms and document credential storage, delivery identity, attachment grouping, and operational limits.
- [ ] 6.2 Add migration-backed account connector state, import events, safe source provenance, and unique external idempotency keys with RLS.
- [ ] 6.3 Implement authorized email PDF/image and ordered multi-image intake through the shared staged-ingestion contract.
- [ ] 6.4 Implement authorized WhatsApp PDF/image and ordered multi-image intake through the shared staged-ingestion contract.
- [ ] 6.5 Implement safe connector failure visibility, unsupported-content handling, replay idempotency, and assignment resolution without preselection.
- [ ] 6.6 Add connector authorization, credential secrecy, supported import, partial import, duplicate delivery, same-filename distinct delivery, consent, assignment, failure, and cross-account tests for every external-ingestion requirement.

## 7. Provider-Neutral Conversational Assistant

- [ ] 7.1 Add migration-backed profile-scoped conversations, ordered messages, lifecycle state, personal citations, fetched-web citations, and provider/model snapshots with RLS.
- [ ] 7.2 Define independent provider-neutral conversational-model and external-retrieval interfaces with fail-closed configuration.
- [ ] 7.3 Implement immutable selected-profile scope and retrieval of only reviewed or user-attested memory, excluding pending candidates and unreviewed observations.
- [ ] 7.4 Implement external retrieval with minimized identifiers, clear personal-versus-external attribution, persisted fetched links, and no fabricated citations.
- [ ] 7.5 Implement retained history, safe generation failure/retry, and source-unavailable behavior after report deletion.
- [ ] 7.6 Add selected-profile, cross-profile denial, no-evidence, pending-evidence, consent, external attribution, de-identification, provider failure, history, deletion-citation, and two-account isolation tests for every conversational-assistant requirement.

## 8. Migration and Rollout

- [ ] 8.1 Backfill application accounts for existing authenticated owners and link existing profiles without inferring account-level consent from legacy per-record booleans.
- [ ] 8.2 Backfill or classify legacy extracted test results and memory facts without silently representing them as verified observations.
- [ ] 8.3 Add expand-and-contract compatibility paths and independently controlled feature flags for staged ingestion, observations, Feed/Drive, connectors, and Chat.
- [ ] 8.4 Verify all new ownership constraints and RLS policies against local and disposable Supabase environments with two-account direct-data tests.
- [ ] 8.5 Exercise forward migration, compatibility reads, rollback, tombstone cleanup, and re-enable paths without losing private data or audit provenance.

## 9. Follow-up Roadmap

- [ ] 9.1 Propose delegated family-member access covering invitations, independent login, profile claiming, grants, the original manager's continuing rights, consent ownership, audit history, revocation, and family members uploading their own reports.
- [ ] 9.2 Propose interactive longitudinal exploration from family member to body system to metric timeline, including analyte aliases, canonical units, reference ranges, observation corrections, accessibility, and source-report drill-down.
- [ ] 9.3 Record separate follow-up changes for AI-consent revocation, Chat actions/reminders, account export/deletion, and any full family-relationship graph.

## 10. Verification and Review

- [ ] 10.1 Build a requirement-to-automated-test traceability matrix covering every added, modified, and removed requirement in this change.
- [ ] 10.2 Run the complete unit, API, migration, worker, connector-contract, provider-contract, private-storage, RLS, and end-to-end journey test suites and record results in `review.md`.
- [x] 10.3 Run `openspec validate define-first-release-family-health-experience --strict` and resolve every validation finding.
- [ ] 10.4 Complete final privacy, AI-trust, consent, deletion, cross-profile isolation, and rollback review; this task SHALL remain incomplete until `review.md` contains the reviewed commit, scope, test results, resolved or accepted findings, and final resume or completion state.
