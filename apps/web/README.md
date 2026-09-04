# Web Client

The V1 web client. This first slice is the sign-up and onboarding journey: the one `self` profile,
age and weight, and user-attested conditions and medications.

## Stack

React 19 with TypeScript, built by Vite, with `@supabase/supabase-js` for sign-in. Vitest and
Testing Library cover the flow. There is no router or data-fetching library yet; the onboarding
wizard is driven by the backend's own `GET /account/onboarding` state.

## Setup

Run these from `apps/web`.

```bash
npm install
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

Google is the only way in. Supabase Auth brokers the OAuth exchange, the browser receives a Supabase
access token, and the API verifies that token's signature, issuer, audience, and expiry against the
project's published keys before mapping its subject to an application account.

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

`src/api/types.ts` mirrors the response models in `apps/api/app/schemas.py` by hand. Replace it with
a generated client once `contracts/` publishes one from the backend's OpenAPI document.

## Known gaps

- Email and password registration, verification, and sign-in are not built. Google is the only
  supported method, so the account-onboarding requirement covering email identities is unmet.
- The API has no read endpoint for profile health context, so a resumed session cannot show the age
  and weight recorded in an earlier visit. The summary offers to record them again instead.
- Feed, Upload, Drive, and Chat are not built here yet; onboarding ends on a summary.
