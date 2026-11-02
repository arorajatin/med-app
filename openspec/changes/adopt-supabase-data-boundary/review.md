# Review Checkpoint

Status: Upload/DB/Storage implementation locally verified; hosted provisioning blocked on credentials
Updated: 2026-09-18
Reviewer: Codex (implementation)
Baseline commit: cb664196041ab958a8c59b5e0c0166877da72cc6 (working-tree changes are uncommitted)

## Reviewed Scope

- Implemented the upload/storage slice: private Supabase source adapter, verified remote size/hash, account-scoped request transactions, non-bypass roles, ownership foreign keys on every current private table, and private bucket policies.
- The baseline deployed on 2026-09-18 includes the PostgreSQL boundary functions and an independent durable failed-upload cleanup intent. The cleanup workload claims opaque IDs, fences stale uploads, retries deletion, and preserves committed sources.
- Hosted upload success commits metadata and a queued extraction job before returning. Feed exposes completed uploads immediately in All Family. A provisional member hint does not place an upload in a resolved member view.
- Added fail-closed startup, a fresh-project provisioning command, and `scripts/dev.py --hosted-data`. Normal API/worker paths do not receive owner/service-role credentials. Hosted extraction remains disabled; mock extraction cannot run on hosted data.
- Provisioning uses an accepted legacy HS256 secret only in protected database configuration. Hosted upload and private/signed-read checks verified its acceptance on the selected project; it is not a substitute for asymmetric user-token verification.
- Eight complete tasks are checked, including private bucket policies and direct-client Storage denial now verified against the hosted service. Broader tasks that also require extraction, report deletion/retention, hosted evidence, or AWS resources remain open. No change has been archived.

## Resume From

1. The updated database password works. The target Singapore project now has the application baseline, private Storage bucket, access policies, protected signing configuration, and separate API/cleanup logins. Runtime files are under the ignored `.context/supabase/runtime` directory with mode `0600`.
2. The initial Storage setup rejected a grant to reserved `supabase_storage_admin`. Removed that grant and retained the documented `authenticator` membership. The guarded `--resume --apply` completed the empty, unconfigured baseline without rerunning migrations.
3. Finish hosted readiness evidence before enabling public uploads: full access-policy coverage, cleanup failure/retry, encryption controls and an actual backup/restore drill. Synthetic in-process API tests use fixture identities; they do not prove Google sign-in or browser behavior. Admission remains disabled and no readiness check has been marked passed automatically.
4. Start the local UI using the generated runtime environment and `--hosted-data`. The meditrail.app demo deployed on 2026-10-01 uses local SQLite and file storage, not this hosted boundary; no production web/API host is configured. Full production extraction, patient resolution through extraction, report deletion/retention, AWS resources and their gates remain unfinished.

## Tests Run

| Date | Command | Result | Notes |
| --- | --- | --- | --- |
| 2026-08-01 | `openspec status --change adopt-supabase-data-boundary --json` | Not run | The `openspec` executable is not installed in this workspace environment. |
| 2026-08-01 | `npx --yes @fission-ai/openspec@1.6.0 validate adopt-supabase-data-boundary --strict` | Pass | Change is valid after planning reconciliation. |
| 2026-08-01 | `npx --yes @fission-ai/openspec@1.6.0 validate --all --strict` | Pass | All 11 current specs and changes passed; 0 failed after cross-change reconciliation. |
| Not run | Implementation and integration suites | Not run | Implementation has not started. |
| 2026-08-10 | `npx --yes @fission-ai/openspec@1.6.0 validate adopt-supabase-data-boundary --strict` | Pass | The final API-mediated web-upload boundary change is valid. |
| 2026-08-10 | `npx --yes @fission-ai/openspec@1.6.0 validate --all --strict` | Pass | All 11 current specs and changes passed; 0 failed. |
| 2026-09-09 | `npx --yes @fission-ai/openspec@1.6.0 validate adopt-supabase-data-boundary --strict`; `npx --yes @fission-ai/openspec@1.6.0 validate --all --strict` | Pass | The change and all 11 specs and changes remain valid after the capability rename. Requirements, scenarios, and task state are unchanged. |
| 2026-09-17 | `BOUNDARY_TEST_ADMIN_URL=<disposable-loopback-uri> uv run --frozen --package med-app-backend pytest -c apps/api/pyproject.toml --cov=app --cov-config=apps/api/pyproject.toml --cov-report=term-missing -q` | Pass | 328 tests; 93.14% coverage. Includes 12 real PostgreSQL policy/API/cleanup checks and SQLite migration round trips. Output: `.context/supabase/backend-validation.txt`. |
| 2026-09-17 | `.context/supabase/storage_rest_smoke.py` against task-owned local PostgreSQL and Supabase Storage containers | Pass | Actual Storage REST writes, verified bytes, private/signed reads, client denial and repeated deletion; synthetic fixtures only. |
| 2026-09-17 | Ruff lint/format; mypy; web typecheck/lint/test/build/contracts; OpenSpec `validate --all --strict` | Pass | 108 web tests; 11 OpenSpec items. No dependency or lockfile changes. |
| 2026-09-17 | Provisioning read-only preflight using `.context/supabase/provision.env` | Blocked | Required hosted credentials were absent at this checkpoint; resolved on 2026-09-18. |
| 2026-09-18 | Provisioning preflight, `--apply`, then guarded `--resume --apply` | Pass after correction | Deployed `20260721_0001`, private bucket/policies and restricted workload logins. Removed the rejected reserved-role grant; baseline was not rerun. |
| 2026-09-18 | Focused provisioning, configuration, cleanup, Storage and Feed suites; Ruff; mypy | Pass | 98 tests passed; lint/format checks passed; type checks passed for 34 source files. Resume refusal cases cover unexpected tables/revision, existing rows/configuration, login-enabled roles and an unsafe boundary. |

| 2026-09-18 | `.context/supabase/hosted_smoke.py` and `HOSTED_SECURITY_CHECK=1` run | Pass after probe correction | Real hosted PDF/PNG/JPEG uploads, byte-exact private/signed downloads, signed-link expiry, direct-client denial, queued Feed state, account isolation, connection restart, invalid multipart rejection and cleanup. Initial probe incorrectly expected 422 instead of 415; corrected run passed. All fixture rows/objects removed. Redacted report: `.context/supabase/hosted-verification.json`. |

## Open Findings

- Hosted provisioning completed on 2026-09-18 in the user-authorized Singapore project (`ap-southeast-1`). Public upload admission remains disabled while readiness evidence is incomplete.
- Local Storage REST tests used `storage-api:v1.0.6`. The 2026-09-18 hosted checks additionally verified compatibility with the target service and its HS256 signing configuration. They use synthetic in-process identities and do not establish Google/browser authentication or full production readiness.
- Source downloads are supported by the adapter, but no new download route was added. Protected extraction raw-output storage and its dedicated worker role are still pending.
- Failed-upload reconciliation is implemented. Complete report deletion and retention are not; the broader production rollout remains gated by the OpenSpec requirements.
- Baseline `20260721_0001` is now deployed and frozen. Use forward migrations for all further schema changes; never stamp or downgrade the hosted project to match an amended baseline.

## Session History

- 2026-08-01: Reconciled planning artifacts for the complete V1 data boundary; implementation remains pending from task 1.1.
- 2026-08-10: Removed email/SES connector storage from V1, defined authenticated API-mediated uploads with direct-to-storage denial, retained Mumbai Textract staging and deletion controls, and passed strict validation.
- 2026-09-09: Renamed the added capability from `production-data-boundary` to `private-data-boundary` so the name states product behavior rather than a deployment environment, matching the project convention that capability names describe stable behavior. Delta spec content is unchanged.

- 2026-09-17: Implemented and reviewed the upload/storage slice against the working tree. Full backend suite with real PostgreSQL: 328 passed, 93.14% branch-aware coverage. Web: 108 tests passed; typecheck, lint, contract check and production build passed using Node 24.18.0. Ruff lint/format and mypy passed; all 11 OpenSpec items passed strict validation. Default Node failed to load the local Rolldown native binding; using the supported installed Node resolved it without changing dependencies. Provisioning was not attempted beyond its missing-credential preflight.
- 2026-09-17: Final guard rejects connection-query overrides of the attested host; all 30 configuration tests passed, followed by Ruff and mypy. Task-owned PostgreSQL/Storage containers and network were removed after verification. The protected provisioning file and test evidence remain under `.context/supabase`.

- 2026-09-18: Updated the durable Supabase region, examples, tests and OpenSpec to Singapore per user instruction; extraction remains disabled pending separate AWS/provider-region review. Live Storage accepted a 60-second HS256 anon token and rejected an invalid-signature control. Downloaded the provider CA to `.context/supabase/prod-ca-2021.crt`, configured `sslrootcert`, removed the unsupported `pgbouncer` URI option, and verified database TLS; password authentication is the remaining credential blocker. Redacted evidence: `.context/supabase/credential-verification.json`. Backend suite: 333 passed, 12 PostgreSQL tests skipped (disposable server not running); after two additional region-rejection cases, all 53 focused configuration/provisioning/cleanup tests passed. Ruff, formatting, mypy and all 11 strict OpenSpec validations passed.

- 2026-09-18: Updated credentials passed. Provisioned the Singapore target, corrected the reserved-role grant, and resumed setup after verifying the empty baseline. Hosted PDF/PNG/JPEG upload, Storage access/expiry, Feed state/isolation/persistence and failed-upload cleanup checks passed; all synthetic rows and objects were removed. No public API was started, no Google login was simulated as verified authentication evidence, and admission/attestation gates remain disabled/pending. Eight of 29 tasks are complete.
