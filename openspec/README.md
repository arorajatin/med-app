# Specifications And Roadmap

OpenSpec separates deployed truth from proposed work. Do not document unfinished behavior in the living specs.

## Current Capabilities

- [Access control](specs/access-control/spec.md)
- [Family profiles](specs/family-profiles/spec.md)
- [Medical records](specs/medical-records/spec.md)
- [Document extraction](specs/document-extraction/spec.md)
- [Reviewed medical memory](specs/reviewed-medical-memory/spec.md)
- [Appointment preparation](specs/appointment-preparation/spec.md)

The [baseline archive](changes/archive/2026-07-14-baseline-medical-records-backend/design.md) preserves the decisions formerly recorded as ADRs and explains which production concerns remain deferred.

## Proposed Roadmap

The sequence below reflects current technical dependencies, not a release commitment.

| Sequence | Change | Outcome | Depends On |
| --- | --- | --- | --- |
| 1 | [Add database migrations](changes/add-database-migrations/proposal.md) | Versioned Alembic schema management | Current SQLAlchemy model |
| 2 | [Adopt Supabase data boundary](changes/adopt-supabase-data-boundary/proposal.md) | Postgres, private Storage, and row-level ownership | Database migrations |
| 3 | [Add production extraction provider](changes/add-production-extraction-provider/proposal.md) | Real OCR or model-backed document extraction | Provider evaluation and privacy approval |
| 4 | [Add queue-backed extraction worker](changes/add-queue-backed-extraction-worker/proposal.md) | Durable asynchronous dispatch, retries, and recovery | Database migrations and queue selection |

## Change Workflow

1. Propose a kebab-case change with `openspec new change <name>` or the repository-local `openspec-propose` Codex skill.
2. Review `proposal.md`, delta specs, `design.md`, and `tasks.md` before code changes begin.
3. Implement from `tasks.md` and mark completed items with `- [x]`.
4. Run `openspec validate <name> --strict` and the relevant automated tests.
5. Sync the delta specs into `openspec/specs/`, then archive the completed change.

Useful commands:

```bash
openspec list
openspec show <change>
openspec status --change <change>
openspec validate --all --strict
openspec archive <change>
```

Run `openspec update` after upgrading the OpenSpec CLI to refresh the generated Codex skills. Review generated changes before committing them.
