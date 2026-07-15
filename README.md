# Medical Records Backend

Python/FastAPI backend for the medical records MVP. The first build focuses on:

- family profiles
- private record/file storage
- upload-to-extraction jobs
- review/confirmation of AI output
- living memory built only from confirmed facts
- appointment checklist generation from confirmed history

## Specifications And Roadmap

This repository uses [OpenSpec](openspec/README.md) as the source of truth for product behavior and planned changes:

- `openspec/specs/` describes capabilities implemented today.
- `openspec/changes/` contains proposed future work with specs, designs, and task checklists.
- `openspec/changes/archive/` preserves completed change history and architectural rationale.
- `openspec/config.yaml` supplies project context and safety rules to planning agents.

Repository-local Codex workflow skills are generated under `.codex/skills/`. OpenSpec's CLI requires Node.js 20.19 or newer:

```bash
npm install -g @fission-ai/openspec@latest
openspec list
openspec validate --all --strict
```

Review a change's `proposal.md`, delta specs, `design.md`, and `tasks.md` before implementation. Archive it only after its tasks are complete and its delta specs have been merged into the living specs.

## Local Setup

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload
```

Local development defaults to SQLite, local private file storage, a dev auth header, and a mock AI extraction provider.

Use either header for local auth:

```http
Authorization: Bearer user_123
X-User-Id: user_123
```

For production auth, set `DEV_AUTH_ENABLED=false` and `SUPABASE_URL=https://<project-ref>.supabase.co`. The backend will verify Supabase access tokens from:

```http
Authorization: Bearer <supabase-access-token>
```

This first Supabase checkpoint only adds JWT verification. Supabase Postgres, private Storage, and RLS policy setup are separate follow-up checkpoints.

## Important Safety Defaults

- Uploaded files are never exposed through public URLs.
- AI extraction is assistive and untrusted until reviewed.
- Only confirmed fields are written to the living medical memory.
- The mock provider exists for development and tests; production providers must implement the same internal extraction contract.

## Useful Commands

```bash
uv run pytest
uv run python -m app.worker once
```
