# API Contracts

This directory is the shared boundary between the backend and web, iOS, and Android clients.

- `openapi.json` is the backend's OpenAPI document, exported from `apps/api`.
- `api.ts` holds the TypeScript types generated from that document. Do not edit it by hand.

## Regenerating after a backend change

```bash
uv run --frozen --package med-app-backend python apps/api/scripts/export_openapi.py
cd apps/web && npm run contracts:generate
```

## How drift is caught

- `apps/api/tests/test_api_contract.py` fails when `openapi.json` no longer matches the API.
- `npm run contracts:check` in `apps/web` fails when `api.ts` was not regenerated from `openapi.json`.
- `apps/web/src/api/contract.ts` fails the web type check when the hand-written types in
  `apps/web/src/api/types.ts` stop agreeing with the generated contract.

CI runs all three, so a backend change that skips the regeneration step cannot merge silently.
