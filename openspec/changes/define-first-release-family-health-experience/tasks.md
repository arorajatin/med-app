The checkbox definitions below are the canonical implementation checklist. Use this dependency order for delivery; tasks within a phase may proceed in parallel when their direct prerequisites are satisfied. `review.md` records the actual resume point when implementation pauses.

1. **Completed safety and client baseline:** 0.1-0.2, 2.4-2.5, 2.8, 9.3, and 10.1-10.5.
2. **Account and profile foundation:** 2.1-2.3, 2.7, 7.1, 10.6-10.8, and 10.16.
3. **Logical-document ingestion:** 1.4, 3.1-3.5, 3.8, and 10.9.
4. **Normalized extraction and assignment:** 1.5, 3.6-3.7, and 4.1.
5. **Observations, review, records, Feed, and Drive:** 4.3-4.10, 5.1-5.7, 7.2, and 10.10-10.12.
6. **Production data, extraction, and worker integration:** 1.1-1.3, 4.2, and 4.11-4.12. Implement the specialized changes in the cross-change order documented in `openspec/README.md`.
7. **Chat:** 6.1-6.6 and 10.13.
8. **Release verification:** 7.4-7.5, 9.1-9.2, 9.4, and 10.14-10.15.
9. **Post-V1 proposals:** 8.1-8.6; these are outside the V1 implementation path but must move to separate changes before this change can archive.

## 0. Immediate Condition-Safety Baseline

- [x] 0.1 Remove association-based mock condition output; fail closed before persistence for every generic, condition-shaped, or unknown extractor field; expose only permitted baseline fields to memory, review, and appointment paths; and add keyword, filename, unsafe-provider, and unsupported-field regression tests.
- [x] 0.2 Establish revision `20260721_0001` as the sole fresh-install schema baseline; remove historical-data inventory, transformation, and historical database paths; and verify API and worker startup only at the declared current head.

## 1. Reconcile Active Change Boundaries

- [ ] 1.1 Implement the reconciled Supabase boundary with `ap-south-1`, stable account-and-ingestion object keys, private download, and RLS for every web-upload source, extraction, and owner-scoped table.
- [ ] 1.2 Implement the reconciled production-extraction contract with pdfplumber, Textract, Bedrock Mistral Large 3, four output classes, required source references, and zero-data-retention preflight.
- [ ] 1.3 Implement the reconciled queue-worker contract so one claimed job targets one immutable logical document and atomic attempt, including ordered multi-image input and Textract callbacks.
- [ ] 1.4 Enforce PDF/JPEG/PNG input, 15,000,000-byte logical-document, 20-page/part, 10,000,000-byte image, and 10,000-pixel image-dimension ceilings with stable safe failures.
- [ ] 1.5 Implement Unicode NFKC/case-folded exact full-name or explicit-alias matching with ambiguous-match blocking; do not match on date of birth and do not add fuzzy automatic matching.

## 2. Accounts, Onboarding, and Profiles

- [ ] 2.1 Add migration-backed application accounts, authentication-identity mapping, onboarding progress, and a uniqueness constraint for one `self` profile per account.
- [ ] 2.2 Add age and reported time plus original/normalized weight and unit fields with validation and migration coverage.
- [ ] 2.3 Implement Google and email/password registration, email verification, verified sign-in, sign-out, safe retries, and idempotent account activation.
- [x] 2.4 Implement resumable onboarding that creates or reuses `self`, captures health context, and records explicit empty conditions or medications.
- [x] 2.5 Implement user-attested condition and medication provenance and immediate trusted-memory creation.
- [ ] 2.7 Add authorization, validation, duplicate-activation, onboarding-resume, and two-account isolation tests for every requirement in account onboarding, family profiles, and access control.
- [x] 2.8 Remove date of birth and year of birth from the profile schema, API, and every profile display; keep reported age as the profile's only age context; preserve optional source-linked date of birth in patient evidence without using it for assignment; and cover the boundary with schema and API tests.

## 3. Staged Logical Document Ingestion

- [ ] 3.1 Add migration-backed ingestion, ordered part, canonical immutable `IngestionSource`, orthogonal lifecycle, assignment evidence, and stable private-object identity.
- [ ] 3.2 Implement validated single-image/PDF and camera-capture receipt through route-stamped `direct_file` and `camera` private-upload contracts.
- [ ] 3.3 Implement ordered multi-image assembly that finalizes exactly one logical document atomically.
- [ ] 3.4 Implement optional user context, immutable original filename, mutable display filename, upload completion, and safe partial-upload cleanup.
- [ ] 3.5 Adapt extraction dispatch so every authenticated, account-owned, upload-complete logical document creates one attempt-aware job.
- [ ] 3.6 Implement account-local patient matching in which exactly one normalized full-name or explicit-alias match replaces the provisional selection and every other result, including no match, becomes `needs_assignment`.
- [ ] 3.7 Implement manual pending-assignment resolution without AI-created profiles and publish derived data only after assignment resolves.
- [ ] 3.8 Add supported, multipart, partial, MIME-sniffing, encrypted, corrupt, oversized, route-controlled source-channel, client-override rejection, exact-match, unmatched, ambiguous, manual-resolution, authorization, and retry tests for every medical-record and ingestion requirement.

## 4. Extraction, Observations, and Reviewed Memory

- [ ] 4.1 Extend the normalized extractor contract with `native_text`/`textract_ocr`, routing reason, patient evidence, document-metadata candidates, metric observations, prescription-memory candidates, literal `documented_condition_candidate` items, affirmative patient-subject assertion validation, and required `SourceReference` values.
- [ ] 4.2 Implement the all-pages native PDF gate with pdfplumber, whole-document Textract fallback, Textract-only image processing, and schema-constrained Bedrock Mistral Large 3 normalization in Mumbai.
- [ ] 4.3 Implement source-linked document-metadata review so confirmation/edit can drive report date, issuer, type, or generated display name, ignore leaves it untrusted, and an explicit rename always wins.
- [ ] 4.4 Add migration-backed observations with original and normalized values/units, ranges, dates, optional body-system classification, source locations, attempt identity, confidence, and quality state.
- [ ] 4.5 Implement automatic observation publication only after successful extraction and resolved assignment, with retry supersession that prevents duplicate active values.
- [ ] 4.6 Implement observation correction, exclusion, source-report reads, and longitudinal profile/metric queries.
- [ ] 4.7 Replace field-wide review with explicit prescription candidate-memory review in which default selection has no trust effect until submit, selected items confirm, edits preserve provenance, and unchecked items become ignored.
- [ ] 4.8 Implement documented-condition review with the label `Condition written in this document — verify before saving`, exact source text/page display, and mandatory `confirm`, `edit`, or `ignore`; preserve original and replacement provenance and never preselect the candidate.
- [ ] 4.9 Update memory generation to include reviewed prescription candidates, confirmed or edited documented conditions, and user-attested facts; exclude observations and pending or ignored conditions; and preserve stable or superseded Chat, Drive, and appointment citations when decisions change.
- [ ] 4.10 Update record-review completion so only pending candidate-memory items block completion and metric observations never do.
- [ ] 4.11 Add native-gate, whole-PDF fallback, provider-region, ZDR, patient-evidence, four-class output, source-reference, atomic-result, transient/terminal retry, retention/deletion, metadata/observation/memory review, citation, and cross-account tests, including proof that medications, dosages, lab values/ranges/flags, symptoms, optional upload context, general medical associations, negation, rule-out, screening, uncertainty, family history, and non-patient statements cannot create a condition candidate.
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
- [ ] 6.6 Add selected-profile, cross-profile denial, no-evidence, pending/ignored-evidence, external attribution, de-identification, provider failure, history, deletion-citation, and two-account isolation tests for every conversational-assistant requirement.

## 7. Migration and Rollout

- [ ] 7.1 Create application accounts and profiles only through the registration and onboarding flows defined in section 2; do not add historical-data import paths.
- [ ] 7.2 Verify a fresh database begins without extracted fields or memory facts and that all new derived data enters through the V1 observation and reviewed-memory contracts.
- [ ] 7.4 Verify all new ownership constraints and RLS policies against local and disposable Supabase environments with two-account direct-data tests.
- [ ] 7.5 Exercise fresh database bootstrap, current-head startup, deployment rollback, and tombstone cleanup without losing private data or audit provenance.

## 8. Follow-up Roadmap

- [ ] 8.1 Propose delegated family-member access covering invitations, independent login, profile claiming, grants, the original manager's continuing rights, audit history, revocation, and family members uploading their own reports.
- [ ] 8.2 Propose interactive longitudinal exploration from family member to body system to metric timeline, including analyte aliases, canonical units, reference ranges, observation corrections, accessibility, and source-report drill-down.
- [ ] 8.3 Propose post-V1 email ingestion in a separate OpenSpec change; decide provider, account/address linking, sender authorization, spoofing and replay protection, attachment grouping, provenance, assignment, deletion, retention, and India-residency controls there rather than in V1.
- [ ] 8.4 Propose post-V1 WhatsApp ingestion covering provider approval, account/phone linking, webhook authentication, sender authorization, message grouping, encrypted phone provenance, idempotency, and India-residency review.
- [ ] 8.5 Propose V2 native clients under `apps/ios` and `apps/android`, including authentication, generated API contracts, upload/camera UX, local-data security, and profile isolation; do not scaffold them in V1.
- [ ] 8.6 Record separate follow-up changes for Chat actions/reminders, account export/deletion and post-creation processing controls, and any full family-relationship graph.

## 9. Verification and Review

- [ ] 9.1 Build a requirement-to-automated-test traceability matrix covering every added, modified, and removed requirement in this change.
- [ ] 9.2 Run the complete unit, API, migration, worker, web-upload-contract, provider-contract, private-storage, RLS, and end-to-end journey test suites and record results in `review.md`.
- [x] 9.3 Run strict change and all-change OpenSpec validation after reconciliation and resolve every validation finding.
- [ ] 9.4 Complete final privacy, AI-trust, account-creation terms, deletion, cross-profile isolation, and rollback review; this task SHALL remain incomplete until `review.md` contains the reviewed commit, scope, test results, resolved or accepted findings, and final resume or completion state.

## 10. V1 Web Client

- [x] 10.1 Scaffold `apps/web` on a selected framework with type checking, linting, unit tests, a production build, and a CI job that runs all four from a locked dependency set.
- [x] 10.2 Implement the resumable onboarding journey: the one `self` profile, age and weight with the entered unit, and explicit condition and medication declarations including an explicit empty answer, driven by `GET /account/onboarding` rather than a client-side step counter.
- [x] 10.3 Mirror the backend's age, weight, and declaration validation rules in the client so a person sees a problem before a round trip, while the service remains the authority and its rejection message is shown.
- [x] 10.4 Establish and end a session, restore it on reload, and sign out and clear it when the API rejects the credential.
- [x] 10.5 Implement Google sign-in through Supabase Auth with PKCE, session restore, background token refresh, sign-out, and safe handling of a cancelled or rejected redirect; remove the development token entry from the client.
- [ ] 10.16 Implement email and password registration, the verification-pending state, resend verification, and sign-in in the client once task 2.3 provides them.
- [ ] 10.6 Publish the backend OpenAPI document, generate or validate a typed client under `contracts/`, and add a drift check so the hand-mirrored types in `src/api/types.ts` cannot silently diverge.
- [ ] 10.7 Add a profile health-context read endpoint and show the latest recorded age and weight with their reported dates on a resumed session, including the non-blocking refresh prompt.
- [ ] 10.8 Implement family-profile creation and browsing screens.
- [ ] 10.9 Implement every upload mode and its error states, including direct file, camera capture, ordered multi-image documents, and size and type rejections.
- [ ] 10.10 Implement Feed, pending-assignment resolution, and processing state.
- [ ] 10.11 Implement the review screens with exact source display, including document metadata, prescription candidates, and documented-condition `confirm`, `edit`, or `ignore`.
- [ ] 10.12 Implement observation retrieval and correction, Drive projections, and report rename, download, and delete.
- [ ] 10.13 Implement Chat with retained history, personal and external citation attribution, and profile selection.
- [ ] 10.14 Add web end-to-end tests that run against a live backend, covering the onboarding journey, upload, review, and two-account isolation.
- [ ] 10.15 Complete an accessibility pass covering keyboard operation, focus management, form labelling, and error announcement across every screen.
