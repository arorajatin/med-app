## Why

The current user-journey drafts describe the application's tabs and a partial upload path, but they do not define a coherent first-release contract for onboarding, family-member routing, external intake, reviewed insights, longitudinal metrics, document organization, or grounded chat. This change turns the agreed journeys into testable product behavior while preserving the boundary between unreviewed extraction, reviewed medical memory, and profile-scoped access.

## What Changes

- Add Google and email/password onboarding for one account holder, automatically create the account holder's `self` profile, capture initial health context, and record account-level AI-processing consent.
- Keep the first release single-manager: one authenticated account owns and manages every family profile. Record delegated family-member login and self-upload as a roadmap follow-up.
- Expand document intake to camera capture, a single image or PDF, a multi-image document, authorized email intake, and authorized WhatsApp intake.
- Require Upload and Chat to begin with a selected family profile while allowing a confidently extracted patient name to select a different existing profile. Ambiguous or unmatched identity remains pending and cannot update metrics or memory.
- Separate deterministic report measurements from medical memory. Measurements are stored automatically as untrusted, source-linked observations; candidate insights and medications require an explicit review submission before they become trusted memory.
- Add a two-mode aggregate Feed ordered by upload date or report date and include only documents whose upload completed.
- Add person-scoped dynamic Drive organization by month or condition, with date-sorted reports and rename support.
- Add provider-neutral, profile-scoped Chat grounded in reviewed memory, with conversation history and external-source links when outside information is used.
- Add authenticated download, display-name rename, and cascading deletion for owned reports and their derived data.
- Add complete user-journey documents for the first-release app shell and each primary flow.
- **BREAKING** Replace per-record AI-processing consent selection with an account-level consent captured during onboarding and snapshotted on each ingestion.

Explicit non-goals for this change:

- Separate login or direct self-upload access for family members; this remains a roadmap change.
- The interactive family-member → body-system → metric trend visualization; this change creates the observation contract needed by that future experience.
- AI-consent revocation, family sharing, clinician access, public file links, arbitrary family-relationship graphs, chat-initiated actions or reminders, medical diagnosis, or selection of a specific extraction or chat model provider.

This change affects medical-data privacy, AI trust, and consent. It retains owner isolation and private files, keeps automatically extracted measurements out of trusted medical memory, and requires explicit review for AI-derived insights and medications.

## Capabilities

### New Capabilities

- `account-onboarding`: Google and email/password signup, verification, account creation, first-run health context, and account-level AI consent.
- `metric-observations`: Automatic, auditable storage and retrieval of deterministic report measurements without treating them as reviewed medical memory.
- `record-feed`: Account-wide completed-upload browsing with upload-date and report-date ordering.
- `record-organization`: Person-scoped dynamic organization of reports by month or reviewed condition.
- `external-record-ingestion`: Authorized email and WhatsApp document intake with provenance, deduplication, and family-profile assignment.
- `conversational-assistant`: Provider-neutral, profile-scoped conversations grounded in reviewed memory with external-source attribution and retained history.

### Modified Capabilities

- `access-control`: Extend private owner isolation to accounts, conversations, observations, connector state, organization views, and staged ingestion.
- `family-profiles`: Automatically create `self`, capture age and unit-aware weight, accept user-attested conditions and medications, and support the single-manager family context.
- `medical-records`: Replace per-record consent with account-level consent, support first-release input modes, stage safe patient assignment, and add download, rename, and delete behavior.
- `document-extraction`: Produce patient identity, deterministic observations, and reviewable insight/medication candidates with auditable provenance.
- `reviewed-medical-memory`: Add preselected-but-explicit review of candidate insights and medications, accept user-attested onboarding facts, and exclude unreviewed metric observations.

## Impact

The change affects authentication and onboarding APIs, account/profile persistence, consent records, upload sessions, private storage, record and extraction schemas, patient matching, metric-observation tables and queries, reviewed-memory rebuilding, aggregate listing, dynamic organization queries, connector credentials and ingestion workers, conversation storage, model/provider abstractions, private download delivery, cascading deletion, migrations, and automated authorization and lifecycle tests.

It overlaps with the active Supabase data-boundary, production-extraction-provider, and queue-backed-worker changes. Implementations must reuse their private storage, provider-neutral extraction, and durable job boundaries rather than introducing parallel infrastructure.
