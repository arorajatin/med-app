# Review Checkpoint

Status: 2A fresh-schema mechanics implemented and locally verified; hosted CI evidence open
Updated: 2026-08-12
Reviewer: Codex
Baseline commit: 8a1e0bd662cc231532c5b91248819e9294c4f8cb
2A implementation state: Current uncommitted worktree; no reviewed implementation commit yet

## Reviewed Scope

- Reconciled proposal, design, delta specs, tasks, and journeys around authenticated web uploads with immutable `direct_file` or `camera` provenance; email, WhatsApp, and other connectors are post-V1.
- Fixed exact-only patient assignment, four extraction trust classes, literal source-cited `documented_condition_candidate` output, `confirm`/`edit`/`ignore` review, and the separation between metric observations and trusted memory.
- Reconciled the selected pdfplumber/Textract/Bedrock Mumbai pipeline, API-mediated private storage, logical-document queue policy, deletion cancellation, account-level consent snapshot, ZDR, and rollout quality gates across all three dependent changes.
- Reviewed the fail-closed condition-safety implementation at the exact baseline commit. It removes mock keyword-to-condition inference; admits only the built-in mock's closed set of baseline non-condition fields; omits unknown, condition-shaped, and non-built-in extractor fields; persists a sanitized safety summary instead of provider raw output; returns generic provider failures; rejects review of unsupported rows; and excludes untrusted condition facts from memory and appointment reads.
- Locked broad, non-diagnostic age/weight input and freshness policy: age 0–130 whole completed years, weight 0.5–500 normalized kilograms, exact decimal `lb × 0.45359237` conversion, reported-date display, and non-blocking refresh after one calendar year for age and six calendar months for weight.
- Established revision `20260721_0001` as the sole fresh-install schema for this release. Removed the second revision, audit/inventory services, schema markers, operational evidence workflow, runtime historical-row paths, and their tests.
- Reviewed the remaining 2A engineering mechanics: declared PostgreSQL driver, frozen dependency lock, Ruff, mypy, branch-coverage, SQLite/PostgreSQL fresh-schema checks, strict OpenSpec CI, and the test-client deprecation fix.

## Resume From

- Commit the integrated 2A worktree, review that exact commit, and require hosted CI evidence, including PostgreSQL migration and API/worker startup coverage.
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
| 2026-08-12 | Local live PostgreSQL smoke | Not available | Docker is stopped and no local PostgreSQL server is installed; the hosted CI job runs the fresh-schema upgrade, API/worker startup, check, and teardown. |

## Open Findings

- Hosted CI has not run for the current uncommitted worktree; a reviewed commit and hosted result remain release evidence.
- Application accounts and later V1 migrations, production infrastructure, provider contracts, privacy approvals, and later runtime quality gates remain unimplemented and untested.
- Databases created by prototype builds are outside this release contract. If such data must be retained, that requires a separately authorized and designed import project; it is not part of 2A.

## Session History

- 2026-07-29: Elicited first-release and roadmap decisions, created planning artifacts and user journeys, passed strict change/all validation, and recorded the cross-change implementation entry point.
- 2026-08-01: Completed initial source/OCR/extraction decisions and cross-change reconciliation.
- 2026-08-10: Removed email/SES ingestion from V1, restricted intake to authenticated web uploads, replaced condition inference with literal source-cited documented conditions, reconciled all dependent artifacts and journeys, and passed strict all-change validation.
- 2026-08-12: Locked age/weight ranges and freshness cadence, added engineering quality gates, and established a single fresh-install schema with no historical-data handling.
