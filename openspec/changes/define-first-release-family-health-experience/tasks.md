## 0. Immediate Condition-Safety Baseline

- [x] 0.1 Remove association-based mock condition output; fail closed before persistence for every generic, condition-shaped, or unknown extractor field; expose only permitted baseline fields to memory, review, and appointment paths; and add keyword, filename, unsafe-provider, and unsupported-field regression tests.
- [x] 0.2 Establish revision `20260721_0001` as the sole fresh-install schema baseline; remove historical-data inventory, transformation, and historical database paths; and verify API and worker startup only at the declared current head.

## 1. Reconcile Active Change Boundaries

- [ ] 1.1 Implement the reconciled Supabase boundary with `ap-south-1`, stable account-and-ingestion object keys, private download, and RLS for every web-upload source, extraction, and owner-scoped table.
- [ ] 1.2 Implement the reconciled production-extraction contract with pdfplumber, Textract, Bedrock Mistral Large 3, four output classes, required source references, and zero-data-retention preflight.
- [ ] 1.3 Implement the reconciled queue-worker contract so one claimed job targets one immutable logical document and atomic attempt, including ordered multi-image input and Textract callbacks.
- [ ] 1.4 Enforce PDF/JPEG/PNG input, 15,000,000-byte logical-document, 20-page/part, 10,000,000-byte image, and 10,000-pixel image-dimension ceilings with stable safe failures.
- [ ] 1.5 Implement Unicode NFKC/case-folded exact full-name or explicit-alias matching with contradictory-DOB and ambiguous-match blocking; do not add fuzzy automatic matching.

## 2. Accounts, Onboarding, Profiles, and Consent

- [ ] 2.1 Add migration-backed application accounts, authentication-identity mapping, onboarding progress, versioned consent evidence, and a uniqueness constraint for one `self` profile per account.
- [ ] 2.2 Add age and reported time plus original/normalized weight and unit fields with validation and migration coverage.
- [ ] 2.3 Implement Google and email/password registration, email verification, verified sign-in, sign-out, safe retries, and idempotent account activation.
- [ ] 2.4 Implement resumable onboarding that creates or reuses `self`, captures health context, and records explicit empty conditions or medications.
- [ ] 2.5 Implement user-attested condition and medication provenance and immediate trusted-memory creation.
- [ ] 2.6 Implement versioned account-level consent checks and snapshots for extraction and personal-memory Chat dispatch without another consent prompt for each document, condition candidate, or Chat message.
- [ ] 2.7 Add authorization, validation, duplicate-activation, onboarding-resume, consent-gating, and two-account isolation tests for every requirement in account onboarding, family profiles, and access control.

## 3. Staged Logical Document Ingestion

- [ ] 3.1 Add migration-backed ingestion, ordered part, canonical immutable `IngestionSource`, orthogonal lifecycle, assignment evidence, consent snapshot, and stable private-object identity.
- [ ] 3.2 Implement validated single-image/PDF and camera-capture receipt through route-stamped `direct_file` and `camera` private-upload contracts.
- [ ] 3.3 Implement ordered multi-image assembly that finalizes exactly one logical document atomically.
- [ ] 3.4 Implement optional user context, immutable original filename, mutable display filename, upload completion, and safe partial-upload cleanup.
- [ ] 3.5 Adapt extraction dispatch so only upload-complete logical documents with accepted consent create one attempt-aware job.
- [ ] 3.6 Implement account-local patient matching in which exactly one normalized full-name or explicit-alias match with no contradictory DOB replaces the provisional selection and every other result becomes `needs_assignment`.
- [ ] 3.7 Implement manual pending-assignment resolution without AI-created profiles and publish derived data only after assignment resolves.
- [ ] 3.8 Add supported, multipart, partial, MIME-sniffing, encrypted, corrupt, oversized, route-controlled source-channel, client-override rejection, no-consent, exact-match, contradictory-DOB, ambiguous, manual-resolution, authorization, and retry tests for every medical-record and ingestion requirement.

## 4. Extraction, Observations, and Reviewed Memory

- [ ] 4.1 Extend the normalized extractor contract with `native_text`/`textract_ocr`, routing reason, patient evidence, document-metadata candidates, metric observations, prescription-memory candidates, literal `documented_condition_candidate` items, and required `SourceReference` values.
- [ ] 4.2 Implement the all-pages native PDF gate with pdfplumber, whole-document Textract fallback, Textract-only image processing, and schema-constrained Bedrock Mistral Large 3 normalization in Mumbai.
- [ ] 4.3 Implement source-linked document-metadata review so confirmation/edit can drive report date, issuer, type, or generated display name, ignore leaves it untrusted, and an explicit rename always wins.
- [ ] 4.4 Add migration-backed observations with original and normalized values/units, ranges, dates, optional body-system classification, source locations, attempt identity, confidence, and quality state.
- [ ] 4.5 Implement automatic observation publication only after successful extraction and resolved assignment, with retry supersession that prevents duplicate active values.
- [ ] 4.6 Implement observation correction, exclusion, source-report reads, and longitudinal profile/metric queries.
- [ ] 4.7 Replace field-wide review with explicit prescription candidate-memory review in which default selection has no trust effect until submit, selected items confirm, edits preserve provenance, and unchecked items become ignored.
- [ ] 4.8 Implement documented-condition review with the label `Condition written in this document — verify before saving`, exact source text/page display, and mandatory `confirm`, `edit`, or `ignore`; preserve original and replacement provenance and never preselect the candidate.
- [ ] 4.9 Update memory generation to include reviewed prescription candidates, confirmed or edited documented conditions, and user-attested facts; exclude observations and pending or ignored conditions; and preserve stable or superseded Chat, Drive, and appointment citations when decisions change.
- [ ] 4.10 Update record-review completion so only pending candidate-memory items block completion and metric observations never do.
- [ ] 4.11 Add native-gate, whole-PDF fallback, provider-region, ZDR, patient-evidence, four-class output, source-reference, atomic-result, transient/terminal retry, retention/deletion, metadata/observation/memory review, citation, and cross-account tests, including proof that medications, dosages, lab values/ranges/flags, symptoms, optional upload context, and general medical associations cannot create a condition candidate.
- [ ] 4.12 Build approved de-identified English digital-PDF, scan, photo, multi-page-lab, and prescription fixtures; gate rollout on zero false assignments, 99.5% exact lab tuple precision, 99.5% source-page accuracy, zero unanchored published values, 95% prescription-candidate precision, and zero documented-condition candidates whose cited source text does not literally name the condition.

## 5. Feed, Drive, and Report Management

- [ ] 5.1 Implement account-wide Feed queries for upload-complete records, including resolved and attention-required items plus processing state.
- [ ] 5.2 Implement stable newest-first upload-date and trusted-report-date ordering, undated placement, tie-breaking, and cursor pagination.
- [ ] 5.3 Implement Drive profile selection and virtual month, undated, trusted-condition, and uncategorized projections without duplicating files; condition groups SHALL use only report-linked user-attested conditions or confirmed or edited documented-condition candidates.
- [ ] 5.4 Implement user display-name rename while preserving original filename and object identity.
- [ ] 5.5 Implement authorized private download without public URLs or storage-key disclosure.
- [ ] 5.6 Implement immediate report tombstoning, work cancellation, derived-data invalidation, idempotent private-object purge, and non-PHI citation tombstones.
- [ ] 5.7 Add Feed inclusion/order/pagination, Drive grouping, rename, download, delete, cleanup retry, citation tombstone, and two-account isolation tests for every Feed, organization, and report-management requirement.

## 6. Provider-Neutral Conversational Assistant

- [ ] 6.1 Add migration-backed profile-scoped conversations, ordered messages, lifecycle state, personal citations, fetched-web citations, and provider/model snapshots with RLS.
- [ ] 6.2 Define independent provider-neutral conversational-model and external-retrieval interfaces with fail-closed configuration.
- [ ] 6.3 Implement immutable explicitly selected profile scope and retrieval of only reviewed or user-attested memory, excluding pending or ignored documented conditions, all other pending candidates, and unreviewed observations.
- [ ] 6.4 Implement external retrieval with minimized identifiers, clear personal-versus-external attribution, persisted fetched links, and no fabricated citations.
- [ ] 6.5 Implement retained history, safe generation failure/retry, and source-unavailable behavior after report deletion.
- [ ] 6.6 Add selected-profile, cross-profile denial, no-evidence, pending/ignored-evidence, consent, external attribution, de-identification, provider failure, history, deletion-citation, and two-account isolation tests for every conversational-assistant requirement.

## 7. Migration and Rollout

- [ ] 7.1 Create application accounts and profiles only through the registration and onboarding flows defined in section 2; do not add historical-data import paths.
- [ ] 7.2 Verify a fresh database begins without extracted fields or memory facts and that all new derived data enters through the V1 observation and reviewed-memory contracts.
- [ ] 7.3 Add independently controlled feature flags for staged web ingestion, observations, Feed/Drive, production extraction, and Chat.
- [ ] 7.4 Verify all new ownership constraints and RLS policies against local and disposable Supabase environments with two-account direct-data tests.
- [ ] 7.5 Exercise fresh database bootstrap, current-head startup, feature-disable rollback, tombstone cleanup, and re-enable paths without losing private data or audit provenance.

## 8. Follow-up Roadmap

- [ ] 8.1 Propose delegated family-member access covering invitations, independent login, profile claiming, grants, the original manager's continuing rights, consent ownership, audit history, revocation, and family members uploading their own reports.
- [ ] 8.2 Propose interactive longitudinal exploration from family member to body system to metric timeline, including analyte aliases, canonical units, reference ranges, observation corrections, accessibility, and source-report drill-down.
- [ ] 8.3 Propose post-V1 email ingestion in a separate OpenSpec change; decide provider, account/address linking, sender authorization, spoofing and replay protection, attachment grouping, provenance, consent, assignment, deletion, retention, and India-residency controls there rather than in V1.
- [ ] 8.4 Propose post-V1 WhatsApp ingestion covering provider approval, account/phone linking, webhook authentication, sender authorization, consent, message grouping, encrypted phone provenance, idempotency, and India-residency review.
- [ ] 8.5 Propose V2 native clients under `apps/ios` and `apps/android`, including authentication, generated API contracts, upload/camera UX, local-data security, and profile isolation; do not scaffold them in V1.
- [ ] 8.6 Record separate follow-up changes for AI-consent revocation, Chat actions/reminders, account export/deletion, and any full family-relationship graph.

## 9. Verification and Review

- [ ] 9.1 Build a requirement-to-automated-test traceability matrix covering every added, modified, and removed requirement in this change.
- [ ] 9.2 Run the complete unit, API, migration, worker, web-upload-contract, provider-contract, private-storage, RLS, and end-to-end journey test suites and record results in `review.md`.
- [x] 9.3 Run strict change and all-change OpenSpec validation after reconciliation and resolve every validation finding.
- [ ] 9.4 Complete final privacy, AI-trust, consent, deletion, cross-profile isolation, and rollback review; this task SHALL remain incomplete until `review.md` contains the reviewed commit, scope, test results, resolved or accepted findings, and final resume or completion state.
