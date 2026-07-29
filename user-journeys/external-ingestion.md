# Email and WhatsApp Ingestion Journey

## Goal

Import medical reports received outside the app through authorized account-owned sources.

## Connection

1. The account manager opens ingestion settings.
2. The account manager authorizes email or WhatsApp intake.
3. The app explains accepted attachments and that the account-level AI-processing choice applies.
4. The source displays an active, failed, or attention-required connection state without exposing credentials.

The exact connector mechanisms are implementation decisions. The journey requires secure account association, visible state, replay protection, and private attachment handling.

## Incoming report

1. A supported PDF, image, or ordered multi-image report arrives through an active source.
2. The service associates the delivery with the owning account.
3. The service privately stores every required source part.
4. The item becomes upload complete only after storage succeeds.
5. The item appears in Feed with email or WhatsApp provenance.
6. Because external intake has no preselected family profile, extraction attempts patient matching when account AI consent permits.
7. One confident existing-profile match resolves assignment automatically.
8. Unknown or ambiguous identity produces `Needs assignment`.
9. The account manager assigns unresolved intake to an existing profile.
10. Assigned reports continue through metric publication and candidate-memory review.

## Replay and failure behavior

- A replay of the same source delivery and attachment resumes or returns the existing ingestion instead of creating a duplicate.
- Filename alone is never used as proof of duplication.
- Unsupported, incomplete, unauthorized, or failed deliveries do not appear as completed Feed reports.
- Without accepted AI consent, the source remains private and requires manual profile assignment.
- Connector credentials and raw unrelated message content never appear in client responses or queue payloads.

