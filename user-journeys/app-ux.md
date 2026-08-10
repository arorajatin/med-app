# App UX Journey

## Goal

Provide predictable access to the family health collection while keeping family-member context explicit.

The V1 interface lives in `apps/web` and communicates with `apps/api`. Native clients under the planned `apps/ios` and `apps/android` locations are V2 work and are not scaffolded for V1.

## Primary navigation

```text
Feed | Chat | Upload | Drive | Profile
```

Upload is the central primary action.

## Launch journey

1. A signed-out person is directed to sign in or create an account.
2. A verified account that has not completed onboarding resumes onboarding.
3. A fully onboarded account enters Feed.
4. Persistent navigation exposes all five primary areas.
5. Returning from a detail view restores the prior tab, ordering, and selected family profile when applicable.

## Family-context rules

- Feed is account-wide and does not inherit one active family profile.
- Chat requires an explicit profile selection before a conversation starts and never silently selects `self`.
- Direct Upload requires a provisional selected profile before capture or file choice.
- Drive selects `self` automatically when it is the only profile; otherwise it requires a profile selection before displaying report groups.
- Profile exposes account information and all managed family profiles.
- No profile-scoped view may retrieve another profile's private memory or observations.

## Cross-tab report behavior

1. A report becomes Feed-eligible as soon as private upload completes.
2. Extraction, assignment, and review states appear independently.
3. A report needing profile assignment can be opened from Feed but cannot appear in Drive, metrics, memory, or Chat evidence.
4. Once assignment resolves, the report becomes available in that person's Drive, but assignment alone does not confirm or trust any extracted candidate.
5. Deterministic measurements may publish as unreviewed observations after assignment; document metadata, prescription candidates, and documented condition candidates follow their separate review rules.
6. A renamed report uses the current display filename consistently across Feed, Drive, and report details.
7. A deleted report disappears from all current views immediately.

## Common states

- Empty areas explain the next useful action.
- Loading and background-processing states do not appear as completed results.
- Failed operations expose a safe retry path when retry is valid.
- Session expiry returns the person to authentication without exposing cached private data.
- Offline or provider failure is distinguishable from an empty medical history.
