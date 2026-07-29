# Family Health App User Journeys

These documents define the agreed first-release experience for one account manager handling medical reports for `self` and multiple family members.

## First-release scope

- One person signs in and owns the entire family space.
- Family profiles do not have independent login access.
- Feed aggregates upload-complete reports across the family.
- Chat and direct Upload begin with a selected family profile.
- Drive exposes the family collection and becomes person-scoped before showing groups.
- Direct input supports camera capture, one image or PDF, and multiple ordered images as one report.
- Authorized email and WhatsApp ingestion use the same private report pipeline.
- AI consent is collected once for the account.
- Deterministic report measurements are captured automatically as source-linked observations.
- AI-derived conditions, medications, follow-ups, and insights require submitted review before entering medical memory.
- Chat uses reviewed personal memory plus attributed external information and retains history.
- The account manager can download, rename, and delete owned reports.

## Core concepts

- **Account manager**: the only authenticated person in the first release.
- **Family profile**: the medical-data context for `self` or another managed person.
- **Staged ingestion**: private document receipt before patient assignment and extraction finish.
- **Upload complete**: every required source part and its metadata have been stored successfully.
- **Metric observation**: a deterministic value linked to its source report; it is automatically stored but remains unreviewed and outside medical memory.
- **Candidate memory**: an AI-derived condition, medication, follow-up, or insight that requires submitted review.
- **Medical memory**: reviewed or user-attested semantic health facts that may ground profile summaries and Chat.

## Report flow

```text
Capture or import
        ↓
Private upload completes ───────────────────────▶ Feed
        ↓
Extract patient evidence and report content
        ↓
Resolve one existing family profile
        ├─ unresolved ──────────────────────────▶ Needs assignment
        ├─ deterministic measurements ──────────▶ Metric observations
        └─ semantic candidates ─▶ Review submit ▶ Medical memory
```

## Journey index

- [App UX](app-ux.md)
- [Sign-up and onboarding](sign-up.md)
- [Profile and family management](profile-and-family.md)
- [Report upload and assignment](doc-upload.md)
- [Extraction and memory review](extraction-review.md)
- [Feed](feed.md)
- [Drive](drive.md)
- [Chat](chat.md)
- [Email and WhatsApp ingestion](external-ingestion.md)
- [Medical metrics](medical-metrics.md)
- [Report management](report-management.md)
- [Roadmap](roadmap.md)

## Trust boundary

A checked-by-default candidate is not trusted merely because it is displayed. Trust begins when the account manager submits the review. Automatically captured metrics remain unreviewed observations even though they have no approval gate; they are not personal-memory evidence for Chat.

