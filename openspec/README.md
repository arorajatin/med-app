# Specifications And Roadmap

OpenSpec separates deployed truth from proposed work. Do not document unfinished behavior in the living specs.

## Current Capabilities

- [Access control](specs/access-control/spec.md)
- [Family profiles](specs/family-profiles/spec.md)
- [Medical records](specs/medical-records/spec.md)
- [Document extraction](specs/document-extraction/spec.md)
- [Reviewed medical memory](specs/reviewed-medical-memory/spec.md)
- [Appointment preparation](specs/appointment-preparation/spec.md)
- [Database schema management](specs/database-schema-management/spec.md)

The [baseline archive](changes/archive/2026-07-14-baseline-medical-records-backend/design.md) preserves the decisions formerly recorded as ADRs and explains which production concerns remain deferred.

## Active Change Delivery Order

The first-release change is the product umbrella and remains active while its specialized production changes land. The stages below describe contract and implementation dependencies, not a requirement to archive the complete umbrella change first. Stages 2A and 2B may proceed in parallel after Stage 1; production enablement still requires both.

| Stage | Change or slice | Outcome | Depends On |
| --- | --- | --- | --- |
| 1 | [First-release foundation](changes/define-first-release-family-health-experience/tasks.md) | Account, profile, logical-document, extraction-class, assignment, and review contracts with local/test adapters | Current living capabilities and database schema management |
| 2A | [Adopt Supabase data boundary](changes/adopt-supabase-data-boundary/proposal.md) | Production Postgres, private Storage, and row-level ownership | Stage 1 account and ingestion schemas |
| 2B | [Add production extraction provider](changes/add-production-extraction-provider/proposal.md) | Real OCR/model adapter and source-valid normalized output | Stage 1 extraction contract, provider evaluation, and privacy approval |
| 3 | [Add queue-backed extraction worker](changes/add-queue-backed-extraction-worker/proposal.md) | Durable asynchronous dispatch, Textract continuation, retries, and recovery | Stage 1 job contract, Stage 2A production boundary, Stage 2B provider phase contract, and queue selection |
| 4 | [Complete the first-release experience](changes/define-first-release-family-health-experience/tasks.md) | Feed, Drive, Chat, production integration, and release verification | The applicable Stage 2 and 3 capabilities |

Delivery order is separate from archive order. A specialized change may be implemented and reviewed while the umbrella remains active, but it must not archive a `MODIFIED` requirement before the change that adds or owns that requirement. For the current `document-extraction` deltas, archive `define-first-release-family-health-experience` before `add-production-extraction-provider`, then archive `add-queue-backed-extraction-worker`. The independent `adopt-supabase-data-boundary` capability may archive as soon as its own implementation and review are complete.

## Change Workflow

1. Propose a kebab-case change with `openspec new change <name>` or the repository-local `openspec-propose` Codex skill.
2. Review `proposal.md`, delta specs, `design.md`, and `tasks.md` before code changes begin.
3. Implement from `tasks.md` and mark completed items with `- [x]`.
4. Keep the change's `review.md` current during code review and testing.
5. Run `openspec validate <name> --strict` and the relevant automated tests.
6. Sync the delta specs into `openspec/specs/`, then archive the completed change.

Keep cross-change delivery and archive order in this roadmap, dependency reasoning in each change's `design.md`, the canonical within-change order and checklist in `tasks.md`, and the actual next resume point in `review.md`. Specifications define behavior and do not carry implementation order. Do not create a parallel implementation-plan file.

## Review Checkpoints

Every active change has a `review.md` based on [the review checkpoint template](templates/review-checkpoint.md). It is the durable handoff between review sessions; `tasks.md` remains the implementation checklist.

Before stopping a partial review session:

1. Record the exact commit being reviewed so later code drift is visible.
2. List reviewed files, symbols, requirements, or task numbers.
3. Record each test command and its result.
4. Capture unresolved findings with severity and ownership.
5. State the next file, symbol, scenario, or task where review should resume.
6. Append a dated session-history entry instead of replacing earlier context.

Set the checkpoint to `Complete` only after review findings are resolved or explicitly accepted, required tests are recorded, and the final review task is checked. Extra `review.md` files are project artifacts: OpenSpec ignores them during spec validation but preserves them with the change when it is archived.

Useful commands:

```bash
openspec list
openspec show <change>
openspec status --change <change>
openspec validate --all --strict
openspec archive <change>
```

Run `openspec update` after upgrading the OpenSpec CLI to refresh the generated Codex skills. Review generated changes before committing them.
