## Why

The current user-journey drafts describe the application's tabs and a partial upload path, but they do not define a coherent first-release contract for onboarding, family-member routing, web-based document intake, reviewed insights, longitudinal metrics, document organization, or grounded chat. This change turns the agreed journeys into testable product behavior while preserving the boundary between unreviewed extraction, reviewed medical memory, and profile-scoped access.

## What Changes

- Add Google and email/password onboarding for one account holder, automatically create the account holder's `self` profile, capture initial health context, and record account-level AI-processing consent.
- Keep the first release single-manager: one authenticated account owns and manages every family profile. Record delegated family-member login and self-upload as a roadmap follow-up.
- Expand document intake through the authenticated web app to camera capture, a single image or PDF, and a multi-image document, with immutable `direct_file` or `camera` provenance.
- Deliver the V1 client from `apps/web` against the backend in `apps/api`; reserve unscaffolded `apps/ios` and `apps/android` homes for separate V2 native-client changes.
- Require Upload and Chat to begin with a selected family profile while allowing exactly matched extracted patient evidence to select a different existing profile. Ambiguous, contradictory, or unmatched identity remains pending and cannot update metrics or memory.
- Separate deterministic lab measurements from medical memory. Measurements are stored automatically as untrusted, source-linked observations. Literal prescription medication and instruction candidates require explicit review. A lab report or prescription may also produce a `documented_condition_candidate` only when the submitted document literally states the condition and the extraction cites that exact text and location. V1 never deduces a condition from a medication, measurement, reference range, symptom, or general medical association. A documented condition becomes trusted memory only after the account manager confirms or edits it.
- Add a two-mode aggregate Feed ordered by upload date or report date and include only documents whose upload completed.
- Add person-scoped dynamic Drive organization by month or condition, with date-sorted reports and rename support.
- Add provider-neutral, profile-scoped Chat grounded in reviewed memory, with conversation history and external-source links when outside information is used.
- Add authenticated download, display-name rename, and cascading deletion for owned reports and their derived data.
- Add complete user-journey documents for the first-release app shell and each primary flow.
- **BREAKING** Replace per-record AI-processing consent selection with an account-level consent captured during onboarding and snapshotted on each ingestion.

Explicit non-goals for this change:

- Separate login or direct self-upload access for family members; this remains a roadmap change.
- The interactive family-member → body-system → metric trend visualization; this change creates the observation contract needed by that future experience.
- AI-consent revocation, family sharing, clinician access, public file links, arbitrary family-relationship graphs, chat-initiated actions or reminders, medical diagnosis, condition inference from medications, lab values, ranges, symptoms, or other implicit associations, selection of a Chat model provider, or document ingestion through email, Amazon SES, WhatsApp, or any other external connector. External connector ingestion requires a separate post-V1 change.

This change affects medical-data privacy, AI trust, and consent. It retains owner isolation and private files, keeps automatically extracted measurements and unconfirmed documented-condition candidates out of trusted medical memory, requires explicit review for document metadata, prescription memory, and literally documented condition candidates, and restricts V1 storage and processing to `ap-south-1` Mumbai.

## Capabilities

### New Capabilities

- `account-onboarding`: Google and email/password signup, verification, account creation, first-run health context, and account-level AI consent.
- `metric-observations`: Automatic, auditable storage and retrieval of deterministic report measurements without treating them as reviewed medical memory.
- `record-feed`: Account-wide completed-upload browsing with upload-date and report-date ordering.
- `record-organization`: Person-scoped dynamic organization of reports by month or reviewed condition.
- `conversational-assistant`: Provider-neutral, profile-scoped conversations grounded in reviewed memory with external-source attribution and retained history.

### Modified Capabilities

- `access-control`: Extend private owner isolation to accounts, conversations, observations, organization views, and staged web uploads.
- `family-profiles`: Automatically create `self`, capture age and unit-aware weight, accept user-attested conditions and medications, and support the single-manager family context.
- `medical-records`: Replace per-record consent with account-level consent, support first-release input modes, stage safe patient assignment, and add download, rename, and delete behavior.
- `document-extraction`: Use native PDF text or Amazon Textract plus Bedrock Mistral Large 3 to produce patient evidence, document-metadata candidates, deterministic observations, reviewable prescription-memory candidates, and documented-condition candidates copied only from condition text literally present in the submitted prescription or lab report with auditable references.
- `reviewed-medical-memory`: Add preselected-but-explicit review of prescription medication and instruction candidates, require confirmation or edit before a literally documented condition becomes trusted, accept user-attested onboarding facts, and exclude unreviewed metric observations and unconfirmed documented-condition candidates.

## Impact

The change affects the V1 client in `apps/web`, the backend in `apps/api`, authentication and onboarding APIs, account/profile persistence, consent records, authenticated web-upload sessions, private storage, record and extraction schemas, patient matching, metric-observation tables and queries, documented-condition review and reviewed-memory rebuilding, aggregate listing, dynamic organization queries, conversation storage, model/provider abstractions, private download delivery, cascading deletion, migrations, and automated authorization, safety, and lifecycle tests. Native clients under future `apps/ios` and `apps/android` paths are outside this change.

It overlaps with the active Supabase data-boundary, production-extraction-provider, and queue-backed-worker changes. Implementations must reuse their Mumbai private storage, selected production extraction adapters, and durable logical-document job boundaries rather than introducing parallel infrastructure.
