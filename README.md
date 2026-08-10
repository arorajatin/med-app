# Family Health App

Product monorepo for a private-by-default family medical-records application.

## Repository layout

```text
apps/
  api/        FastAPI backend and workers
  web/        V1 web client home; framework not selected yet

contracts/    Shared API-contract documentation and generated-client boundary
infra/        Supabase and AWS infrastructure definitions
openspec/     Product specifications and proposed changes
user-journeys/ First-release and roadmap journeys
```

Native clients are planned for V2 at `apps/ios/` and `apps/android/`. They are documented but not
scaffolded yet, so the repository does not contain empty native projects.

## Backend setup

Run backend commands from the repository root. The root is a uv workspace and the existing Python
distribution remains named `med-app-backend`.

```bash
uv sync --package med-app-backend --extra dev
uv run --package med-app-backend alembic -c apps/api/alembic.ini upgrade head
uv run --package med-app-backend uvicorn app.main:app --reload
```

Local settings are read from the root `.env`. Start from [.env.example](.env.example) when creating
one. Local defaults use SQLite, private filesystem storage, development authentication, and the mock
extraction provider.

Useful checks:

```bash
uv run --package med-app-backend --extra dev pytest -c apps/api/pyproject.toml
uv run --package med-app-backend alembic -c apps/api/alembic.ini check
uv run --package med-app-backend python -m app.worker once
npx --yes @fission-ai/openspec@1.6.0 validate --all --strict
```

Backend-specific notes are in [apps/api/README.md](apps/api/README.md). Product behavior and planned
work remain rooted in [openspec/README.md](openspec/README.md).
