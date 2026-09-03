# Family Health App User Journeys

These documents define the agreed first-release experience for one account manager handling medical reports for `self` and multiple family members.

## Application locations

- `apps/web` is the only V1 client interface.
- `apps/api` contains the V1 backend API and background-processing entry points.
- `apps/ios` and `apps/android` are planned V2 client locations and are not scaffolded in V1.

## First-release scope

- One person signs in and owns the entire family space.
- Family profiles do not have independent login access.
- Feed aggregates upload-complete reports across the family.
- Chat and direct Upload begin with a selected family profile.
- Drive exposes the family collection and becomes person-scoped before showing groups.
- V1 accepts only authenticated web uploads, stamped as `direct_file` or `camera` by `apps/api`.
- Web upload supports camera capture, one image or PDF, and multiple ordered images as one report.
- Email and WhatsApp intake are post-V1 ideas that require separate OpenSpec changes before implementation.
- AI consent is collected once for the account and is required; the first release has no AI-disabled mode.
- Deterministic report measurements are captured automatically as source-linked observations.
- Extracted document metadata, prescription candidates, and conditions literally written in a document require review before trusted use.
- Chat uses reviewed personal memory plus attributed external information and retains history.
- The account manager can download, rename, and delete owned reports.

## Core concepts

- **Account manager**: the only authenticated person in the first release.
- **Family profile**: the medical-data context for `self` or another managed person.
- **Staged ingestion**: private document receipt before patient assignment and extraction finish.
- **Upload complete**: every required source part and its metadata have been stored successfully.
- **Ingestion source**: immutable `direct_file` or `camera` provenance stamped by the authenticated upload route.
- **Document metadata candidate**: an extracted date, issuer, type, or display-name suggestion that requires confirmation or edit.
- **Metric observation**: a deterministic value linked to its source report; it is automatically stored but remains unreviewed and outside medical memory.
- **Prescription candidate**: a medication or instruction literally written in a prescription that requires submitted review.
- **Documented condition candidate**: condition text literally present in a prescription or lab report, retained with its exact source reference and left pending for `confirm`, `edit`, or `ignore`. Medication details, measurements, abnormal flags, symptoms, and general medical associations never create a condition candidate by themselves.
- **Medical memory**: reviewed or user-attested semantic health facts that may ground profile summaries and Chat.

## Report flow

```text
Select a profile and upload through apps/web
        ↓
apps/api validates and privately stores the upload
        ├─ source: direct_file or camera
        └─ upload complete ─────────────────────▶ Feed
        ↓
Extract patient evidence and report content
        ↓
Resolve one existing family profile
        ├─ unresolved ──────────────────────────▶ Needs assignment
        └─ resolved ────────────────────────────▶ Profile report collection
                ├─ deterministic measurements ─▶ Metric observations (unreviewed)
                ├─ prescription candidates ────▶ Review submit ─▶ Medical memory
                └─ documented condition candidates
                        ├─ confirm or edit ──────▶ Medical memory
                        └─ ignore ───────────────▶ No trusted memory
```

Resolving assignment only connects a report to a profile. It does not confirm document metadata, prescription candidates, or documented condition candidates.

## Journey index

- [App UX](app-ux.md)
- [Sign-up and onboarding](sign-up.md)
- [Profile and family management](profile-and-family.md)
- [Report upload and assignment](doc-upload.md)
- [Extraction and memory review](extraction-review.md)
- [Feed](feed.md)
- [Drive](drive.md)
- [Chat](chat.md)
- [Medical metrics](medical-metrics.md)
- [Report management](report-management.md)
- [Roadmap](roadmap.md)

## Trust boundary

A checked-by-default prescription candidate is not trusted merely because it is displayed. Trust begins when the account manager submits the review. A documented condition becomes trusted only after `confirm` or `edit`; a pending or ignored condition cannot ground Chat, Drive grouping, or other downstream use. Automatically captured metrics remain unreviewed observations even though they have no approval gate, and they are not personal-memory evidence for Chat.
