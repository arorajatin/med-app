# Chat Journey

## Goal

Answer questions for one selected family member using trusted personal memory and attributed external information.

## Journey

1. The account manager opens Chat.
2. Before starting or reopening a conversation, the account manager explicitly selects one owned family profile; the app does not silently default to `self`, even when it is the only profile.
3. The app starts a new conversation or opens retained history scoped to that profile.
4. The account manager asks a question.
5. The assistant retrieves only that person's reviewed or user-attested medical memory.
6. The assistant may retrieve current external information when personal memory alone is insufficient.
7. The response distinguishes personal-record evidence from general external information.
8. A personal claim retains its memory and source-report citation when one exists.
9. External factual support includes the actual site links used when available.
10. If reviewed personal evidence is absent, the assistant states that limitation rather than inventing a personal fact.
11. The completed response and its citations become part of private retained conversation history.

## Context and trust rules

- One conversation never combines private context from different family profiles.
- A confirmed or edited `documented_condition_candidate` may be used as a reviewed condition fact and cites both its source report and the exact source text location. An edited value also preserves the originally documented text in its review provenance.
- Pending or ignored documented-condition candidates are not personal evidence.
- Unreviewed metric observations are not trusted personal-memory evidence in the first release.
- Medications, dosages, lab values, ranges, flags, symptoms, and general medical associations never justify an inferred personal condition.
- External retrieval minimizes direct personal identifiers and unrelated private medical context.
- The product contract remains the same when a supported model or retrieval provider changes.
- A missing provider configuration fails closed rather than sending private context to an unintended fallback.

## Failure behavior

- A generation or retrieval failure is shown as failed or retryable, not as a completed answer.
- External-source failure never results in a fabricated link.
- Session or authorization failure does not expose retained history.

## First-release boundary

Chat answers questions only. It does not create appointments, reminders, messages, or other side effects.
