# Review Checkpoint

Status: 2B onboarding and the web onboarding client implemented and locally verified; hosted CI evidence open
Updated: 2026-09-03
Reviewer: Codex
Baseline commit: 8a1e0bd662cc231532c5b91248819e9294c4f8cb
2A implementation state: Current uncommitted worktree; no reviewed implementation commit yet

## Reviewed Scope

- Reconciled proposal, design, delta specs, tasks, and journeys around authenticated web uploads with immutable `direct_file` or `camera` provenance; email, WhatsApp, and other connectors are post-V1.
- Fixed exact-only patient assignment, four extraction trust classes, literal source-cited `documented_condition_candidate` output, `confirm`/`edit`/`ignore` review, and the separation between metric observations and trusted memory.
- Reconciled the selected pdfplumber/Textract/Bedrock Mumbai pipeline, API-mediated private storage, logical-document queue policy, deletion cancellation, account-level consent snapshot, ZDR, and rollout quality gates across all three dependent changes.
- Reviewed the fail-closed condition-safety implementation at the exact baseline commit. It removes mock keyword-to-condition inference; admits only the built-in mock's closed set of baseline non-condition fields; omits unknown, condition-shaped, and non-built-in extractor fields; persists a sanitized safety summary instead of provider raw output; returns generic provider failures; rejects review of unsupported rows; and excludes untrusted condition facts from memory and appointment reads.
- Implemented the always-on AI boundary and removal of date of birth from profile metadata while preserving source-linked date of birth in document patient evidence, and reconciled the living `family-profiles` and `medical-records` specs with the resulting code.
- Recorded four product decisions and propagated them through the proposal, design, delta specs, tasks, implementation plan, and journeys: AI processing is always on, document extraction may retain source-linked date of birth without using it for assignment, profiles carry no date of birth and keep reported age as their only age context, and an unmatched patient name always becomes `needs_assignment`.
- Locked broad, non-diagnostic age/weight input and freshness policy: age 0–130 whole completed years, weight 0.5–500 normalized kilograms, exact decimal `lb × 0.45359237` conversion, reported-date display, and non-blocking refresh after one calendar year for age and six calendar months for weight.
- Established revision `20260721_0001` as the sole fresh-install schema for this release. Removed the second revision, audit/inventory services, schema markers, operational evidence workflow, runtime historical-row paths, and their tests.
- Reviewed the remaining 2A engineering mechanics: declared PostgreSQL driver, frozen dependency lock, Ruff, mypy, branch-coverage, SQLite/PostgreSQL fresh-schema checks, strict OpenSpec CI, and the test-client deprecation fix.
- Implemented resumable onboarding derived from persisted rows, one reusable `self` profile, explicit empty condition and medication declarations, and user-attested trusted memory (tasks 2.4 and 2.5).
- Added independently controlled default-off feature flags for web ingestion, extraction, observations, Feed/Drive, and Chat, and gated the shipped surfaces on them.
- Selected React, TypeScript, and Vite for `apps/web`, scaffolded the client, and added a CI job that type checks, lints, tests, and builds it from a locked dependency set.
- Implemented the sign-up and onboarding journey in the client, driven by `GET /account/onboarding` so the resume point comes from the service rather than a client-side counter, and recorded the remaining web work as tasks 10.5 through 10.15.

## Resume From

- Commit the integrated 2A worktree, review that exact commit, and require hosted CI evidence, including PostgreSQL migration and API/worker startup coverage.
- Finish task 2.3 registration, verification, sign-in, and sign-out, which onboarding now assumes but does not provide.
- Keep task 7.3 open until Feed/Drive and Chat exist to enable and disable; their flags are declared but gate no route yet.
- Keep task 2.7 open until the full authorization, validation, and isolation matrix covers every account-onboarding, family-profile, and access-control requirement.
- Publish the backend OpenAPI document and generate or validate the typed client under `contracts/` (task 10.6). Until then `apps/web/src/api/types.ts` mirrors `apps/api/app/schemas.py` by hand and can drift silently.
- Add a profile health-context read endpoint (task 10.7). The client cannot show a previously recorded age and weight on a resumed session because no endpoint returns them.
- Keep the future condition-candidate path disabled until the structured source contract and literal-span validation land behind default-off controls.
- No operational database inventory, data review, or row transformation is required for 2A. Provision an empty database and apply the declared current head.

## Tests Run

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-07-29 | `openspec status --change define-first-release-family-health-experience` | Pass | Proposal, specs, design, and tasks are complete. |
| 2026-08-10 | `npx --yes @fission-ai/openspec@1.6.0 validate --all --strict` | Pass | All current specs and changes passed after the web-only and literal-condition reconciliation. |
| 2026-08-12 | `uv lock --check` | Pass | The lock matches backend and development dependency declarations. |
| 2026-08-12 | Baseline-aware Ruff lint and format checks | Pass | All non-layout lint passed; import and formatter output contained no nonblank changes relative to the checked-in files. |
| 2026-08-12 | `mypy --config-file apps/api/pyproject.toml apps/api/app` | Pass | No issues in 21 source files. |
| 2026-08-12 | `pytest -c apps/api/pyproject.toml --cov=app --cov-config=apps/api/pyproject.toml --cov-report=term-missing` | Pass | 23 tests passed; 84.68% branch coverage exceeded the 84% gate. |
| 2026-08-12 | SQLite `alembic upgrade head`, `check`, and `downgrade base` | Pass | The empty database upgraded only to `20260721_0001`, matched model metadata, and returned to an empty schema. |
| 2026-08-12 | PostgreSQL offline `alembic upgrade head --sql` | Pass | DDL generation contained only the sole declared revision. |
| 2026-08-12 | `npx --yes @fission-ai/openspec@1.6.0 validate --all --strict` | Pass | All 11 current specs and changes passed; 0 failed. |
| 2026-08-12 | Active-tree terminology/symbol scan and `git diff --check` | Pass | No removed historical-data symbols or whitespace errors remain. |
| 2026-09-02 | `ruff check --ignore I001`, `mypy --config-file apps/api/pyproject.toml apps/api/app` | Pass | No lint findings; no type issues in 23 source files. |
| 2026-09-02 | `pytest -c apps/api/pyproject.toml --cov=app --cov-report=term-missing` | Pass | 47 tests passed; 89.48% branch coverage exceeded the 84% gate, including the profile-versus-patient-evidence date-of-birth boundary. |
| 2026-09-02 | SQLite `alembic upgrade head`, `check`, and `downgrade base` | Pass | The amended `20260721_0001` baseline matched model metadata after profile date-of-birth removal and the non-null consent snapshot. |
| 2026-09-02 | `npx --yes @fission-ai/openspec@1.6.0 validate --all --strict` | Pass | All 11 specs and changes passed. |
| 2026-09-03 | `ruff check --ignore I001`, `ruff format --diff` on changed files, `mypy --config-file apps/api/pyproject.toml apps/api/app` | Pass | No lint findings; changed files already formatted; no type issues in 24 source files. |
| 2026-09-03 | `pytest -c apps/api/pyproject.toml --cov=app --cov-report=term` | Pass | 75 tests passed; 93.10% branch coverage exceeded the 84% gate, including onboarding resume, attested memory, and feature-flag cases. |
| 2026-09-03 | SQLite `alembic upgrade head` and `check` | Pass | The amended `20260721_0001` baseline matched model metadata after the profile declaration timestamps and attested-identity column. |
| 2026-09-03 | `npm run typecheck`, `npm run lint`, `npm run test`, `npm run build` in `apps/web` | Pass | No type or lint findings; 34 tests across 6 files passed; the production build succeeded. |
| 2026-09-03 | Live onboarding journey against a local API on a fresh SQLite database | Pass | Consent, self profile, age and weight, an attested condition, and an explicit empty medication declaration drove onboarding from `not_started` to `completed`, and the attested condition read back with `user_attested` provenance. |
| 2026-08-12 | Local live PostgreSQL smoke | Not available | Docker is stopped and no local PostgreSQL server is installed; the hosted CI job runs the fresh-schema upgrade, API/worker startup, check, and teardown. |

## Open Findings

- Hosted CI has not run for the current uncommitted worktree; a reviewed commit and hosted result remain release evidence.
- Application accounts and later V1 migrations, production infrastructure, provider contracts, privacy approvals, and later runtime quality gates remain unimplemented and untested.
- Task 2.6 remains open. Onboarding now requires consent before it can complete, but an account may still upload as soon as it accepts consent without finishing the remaining steps, and Chat dispatch is not consent-gated because Chat does not exist.
- The web client's sign-in screen accepts a bearer token directly because task 2.3 has no registration, verification, or sign-in endpoints yet. This is a development affordance, not the V1 journey, and task 10.5 tracks replacing it.
- The client's weight range check uses binary floating point, while the service uses exact decimal arithmetic. The service remains the authority, so a value at the exact boundary may be reported differently by the two; the client's job is only to catch obvious mistakes early.
- Databases created by prototype builds are outside this release contract. If such data must be retained, that requires a separately authorized and designed import project; it is not part of 2A.

## Session History

- 2026-07-29: Elicited first-release and roadmap decisions, created planning artifacts and user journeys, passed strict change/all validation, and recorded the cross-change implementation entry point.
- 2026-08-01: Completed initial source/OCR/extraction decisions and cross-change reconciliation.
- 2026-08-10: Removed email/SES ingestion from V1, restricted intake to authenticated web uploads, replaced condition inference with literal source-cited documented conditions, reconciled all dependent artifacts and journeys, and passed strict all-change validation.
- 2026-08-12: Locked age/weight ranges and freshness cadence, added engineering quality gates, and established a single fresh-install schema with no historical-data handling.
- 2026-09-02: Applied four product decisions across the planning artifacts. AI processing is never disabled, so consent acceptance gates onboarding and an upload without governing consent is rejected rather than stored. Profiles drop date of birth entirely and keep reported age as their only age context (new task 2.8). Document extraction may retain a source-linked date of birth, but assignment does not use it. An unmatched patient name always becomes `needs_assignment`; a provisional selection never resolves a document on its own.
- 2026-09-02: Implemented the decisions that touch shipped code. `_receive_ingestion` now rejects an upload with HTTP 403 before storing any bytes when the account has no consent evidence, always creates the extraction job, and never auto-resolves the provisional profile, so explicit assignment is the only path to a record. Removed `Profile.date_of_birth` from the model, schemas, and the `20260721_0001` baseline while retaining `PatientEvidence.date_of_birth` in the extractor contract, persistence model, schema, and API. Made `Ingestion.consent_evidence_id` non-null. Replaced the stored-without-extraction test with a rejection test and synced the living `family-profiles` and `medical-records` specs.
- 2026-09-02: Resolved review findings by scoping the date-of-birth restriction to profile metadata, explicitly allowing source-linked date of birth in patient evidence, and stating that V1 has neither consent revocation nor account deletion instead of presenting deletion as an available stop-processing control. Added patient-evidence retention coverage; all 47 backend tests, schema checks, static checks, and 11 strict OpenSpec validations pass.
- 2026-09-03: Implemented the 2B onboarding slice. `GET /account/onboarding` derives progress from the rows each step leaves behind and names the first outstanding step, so status cannot drift from the data. `PUT /account/onboarding/self-profile` creates or reuses the account's one `self` profile, and `POST /profiles` now answers 409 rather than failing on the unique index. `PUT /profiles/{id}/attested-conditions` and `.../attested-medications` declare the complete current set, supersede the previous set, and record an empty declaration as an answered step through new `conditions_declared_at` and `medications_declared_at` columns. Declared entries become `user_attested` memory facts carrying the attesting identity. Memory reads now decide on provenance, not category alone: a condition the account manager typed is trusted while a document-derived condition stays blocked. Added five default-off slice flags and gated upload, assignment, extraction dispatch, the extraction job routes, and observation publication on them.
- 2026-09-03: Selected React, TypeScript, and Vite and built the web onboarding journey against the new endpoints. The wizard opens at `next_step` and re-reads onboarding state after each step, so a reload or a corrected earlier answer resumes from the service's own view. Client validation mirrors the age, weight, and declaration rules while the service stays authoritative and its `detail` message is shown on rejection. Verified the request shapes against a live API on a fresh database, not only against mocked responses. Added a `web-quality` CI job and recorded the remaining client work, including the generated-client drift check and the missing health-context read endpoint, as tasks 10.5 through 10.15.
