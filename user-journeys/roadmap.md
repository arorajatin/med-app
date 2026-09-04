# User-Journey Roadmap

## Delegated family-member access and self-upload

Create a follow-up OpenSpec change allowing a managed family member to become an authenticated user and upload their own reports.

That change must define:

- invitation and acceptance;
- linking an identity to an existing managed profile;
- manager, contributor, and viewer permissions;
- whether the original account manager retains access;
- independent uploads into the same profile;
- audit history and access revocation;
- duplicate-account and duplicate-profile reconciliation;
- migration from direct account ownership to household membership and profile grants.

The future user must never impersonate the original manager.

## Interactive body-system trends

Create a follow-up experience for:

```text
Family member → body system, such as liver → metric → change over time
```

That change must define:

- metric-name normalization across laboratories;
- canonical and original units;
- reference ranges that vary by laboratory or patient context;
- body-system classification;
- corrected, excluded, retried, and deleted observations;
- confidence and missing-data presentation;
- accessible tables and graphs;
- source-report drill-down from every plotted point.

Graphs use report-linked metric observations, not medical-memory prose.

## Native iOS and Android clients

`apps/ios` and `apps/android` are planned V2 locations and remain unscaffolded in V1. Create a separate OpenSpec change before building either native client so its scope, shared API contract, authentication, privacy controls, and upload behavior are agreed first.

## Email and WhatsApp report ingestion

Email and WhatsApp intake are excluded from V1. Create and approve a separate post-V1 OpenSpec change for each channel before accepting reports through it.

Each future change must decide the user journey, account and source authorization, supported report formats, report grouping, provider and security approach, privacy and residency requirements, profile assignment, provenance, deletion, failure handling, duplicate delivery, and testing. V1 makes no commitment to a provider, inbound-address scheme, phone-linking method, or transport design.

## Other deferred journeys

- Chat-created actions, reminders, or appointments
- Account export, retention controls, and account deletion
- A full relationship graph among family members
- Multiple independent reports in one direct-upload batch
- Family or clinician sharing
