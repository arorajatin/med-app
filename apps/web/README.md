# Web Client

FamCare, the V1 web client, supports sign-up, onboarding, family profiles, and document upload. A
completed account opens a five-tab interface: Feed, Chat, Upload, Drive, and Profile. Upload is the
initial tab for this milestone; Profile keeps the existing health summary and family settings.

## Stack

React 19 with TypeScript, built by Vite, with `@supabase/supabase-js` for sign-in. Vitest and
Testing Library cover the flow. There is no router or data-fetching library yet; the onboarding
wizard is driven by the backend's own `GET /account/onboarding` state.

## Look and feel

FamCare should read as a home for a family's records rather than a medical console, so the interface
is warm: paper and sand surfaces, a calm sage for anything you act on, terracotta for warmth, and
Fraunces over Inter for type.

Styling is Tailwind CSS v4, configured entirely in [src/styles.css](src/styles.css). The `@theme`
block there defines *semantic* colours — `canvas`, `surface`, `line`, `ink`, `ink-soft`, `sage`,
`clay`, `honey`, `plum`, `alarm` — rather than raw palette steps. The dark theme re-declares those
same variables under `prefers-color-scheme`, which is why components carry no `dark:` variants:
`bg-surface text-ink` is already correct in both themes. Reach for a literal colour only where an
outside brand requires it, as the Google button does.

A small component layer in the same file covers what repeats everywhere — `.panel`, `.button` and
its variants, `.input`, `.field__*`, `.banner`, `.muted` — and layout stays in utilities on the
element. Navigation is a single element that renders as a bottom tab bar on a phone and a sidebar
from `lg` up, so no control is duplicated in the accessibility tree.

## Setup

Run these from `apps/web`. Use the Node version in the root `.nvmrc`; `nvm use` finds it
from this directory too. Reinstall the locked dependencies after switching Node versions.

```bash
nvm use
npm ci
npm run dev
```

The dev server proxies `/api` to the backend at `http://127.0.0.1:8000` and strips the prefix, so
the backend needs no CORS configuration. Point it elsewhere with `API_PROXY_TARGET`. A deployed
build calls the API directly through `VITE_API_BASE_URL`, which then needs CORS on the API.

Start the backend first, from the repository root:

```bash
uv run --package med-app-backend uvicorn app.main:app --reload
```

Useful checks:

```bash
npm run typecheck
npm run lint
npm run test
npm run build
```

## Signing in

Google is the only way in, and that is a product decision rather than only a dashboard setting.
Supabase Auth brokers the OAuth exchange, the browser receives a Supabase access token, and the API
verifies that token's signature, issuer, audience, and expiry against the project's published keys.
It then reads the sign-in method from the provider-controlled `app_metadata` claim and refuses
anything other than Google with a 403, before any account is created. Email and password sign-in is
a roadmap item.

The flow uses PKCE, so an authorization code comes back on the redirect and is exchanged for a
session; no access token is ever placed in the URL. The Supabase client persists and refreshes the
session, and every API request asks it for a current token rather than reusing one captured earlier.

Set up before it works:

1. Copy [.env.example](.env.example) to `.env` and fill in `VITE_SUPABASE_URL` and
   `VITE_SUPABASE_ANON_KEY`. Both are publishable and ship in the bundle.
2. In the Supabase dashboard, enable the Google provider under Authentication, Providers, and give
   it a Google OAuth client ID and secret from the Google Cloud console.
3. Add the app's origin, such as `http://localhost:5173`, to Authentication, URL Configuration,
   Redirect URLs. The client asks to return to `window.location.origin`.
4. Run the backend with `DEV_AUTH_ENABLED=false` so it verifies real Supabase tokens.

Development authentication is for backend work only. With `DEV_AUTH_ENABLED=true` the API takes the
bearer value as a literal user id, so a Supabase token would become the account key and every token
refresh would look like a different person.

## How onboarding works

The backend derives progress from the rows each step leaves behind, so the client never tracks its
own step counter:

1. `GET /account/onboarding` returns `next_step` and `completed_steps`, and the wizard opens at
   `next_step`. Reloading mid-flow resumes at the same place.
2. Each step calls its own endpoint, then re-reads onboarding state to decide where to go next.
3. A finished step can be corrected from the summary; that reuses the same endpoints, and the
   `self` profile is updated rather than duplicated.

Client-side validation mirrors the backend rules so a person sees the problem before a round trip:
whole years 0–130 for age, a weight that normalizes to 0.5–500 kg in the unit they entered, and an
explicit "none" answer for conditions or medications, which submits an empty list rather than
skipping the step. The server remains the authority; its `detail` message is shown when it rejects
a request.

## Contract

`src/api/types.ts` still mirrors the response models in `apps/api/app/schemas.py` by hand, because
the hand-written types narrow some strings the backend declares as plain text. It can no longer
drift silently: `src/api/contract.ts` checks it against the generated types in `contracts/api.ts`
during `npm run typecheck`, and `npm run contracts:check` fails when `contracts/api.ts` was not
regenerated from the backend's OpenAPI document. See [contracts/README.md](../../contracts/README.md).

## Uploading a report

Choose a family profile first, then select one PDF, one JPEG/PNG image, multiple images of one
report, or capture pages with the camera. Image pages can be previewed, reordered, removed, and
retaken before submission. File selection and camera capture use separate API routes so the
service controls source provenance. Clear the document to switch between those input modes.

The browser sends ordered multipart files to the authenticated API with a current access token.
It never writes directly to storage. Progress measures transport; upload completion is shown
only after the API confirms that every source part and its extraction job were saved together.
The receipt shows upload, extraction, and assignment separately. Upload drafts survive tab
switches but are not persisted across reloads or sign-out. Camera streams stop when capture
closes, the tab is hidden, or the account signs out. Camera capture needs browser permission and
a secure context (HTTPS or localhost); file selection remains available if capture is unavailable.

Limits are 15,000,000 bytes per report, 20 PDF pages or image parts, 10,000,000 bytes per image,
and 10,000 pixels per image dimension. The API detects the actual file format, parses PDFs and
images, and rejects encrypted, empty, corrupt, unsupported, and oversized sources. Optional
report names allow 260 characters and notes allow 4,000. Notes remain separate from source evidence.

## Known gaps

- Google sign-in was enabled and verified end to end on 2026-09-07. The upload browser smoke
  test uses a synthetic development identity; real-device camera permissions remain a release check.
- Feed, Drive, and Chat show placeholders. Assignment and review screens belong to later milestones.
- Production OCR and automatic patient matching remain pending. The local mock can read digital
  PDF text but performs no image OCR; an upload receipt does not imply reviewed health information.
