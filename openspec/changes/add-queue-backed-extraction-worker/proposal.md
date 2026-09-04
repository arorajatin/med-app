## Why

Production extraction is slower than an HTTP upload, includes an asynchronous Textract branch, and can be rate-limited or interrupted. Inline execution and a polling command cannot durably coordinate a finalized multi-part report, recover an abandoned provider phase, or prevent a duplicate delivery from publishing duplicate medical output.

## What Changes

- Dispatch exactly one finalized logical document created by an authenticated `direct_file` or `camera` web-upload route, including its immutable ordered source-part manifest and governing account-level consent snapshot, through an Amazon SQS Standard queue in `ap-south-1` after the upload transaction commits.
- Run one atomic extraction attempt through explicit inspection, native-text or Textract, model extraction, normalization, and publication phases.
- Resume asynchronous Textract PDF work through a regional SNS-to-SQS callback path without holding a worker claim while the provider runs.
- Claim runnable phases atomically, use attempt-scoped idempotency, and supersede prior result sets only after a replacement commits successfully.
- Retry only transient failures, with three total attempts and persisted jittered delays based on 30 seconds and two minutes; keep terminal failures safe and observable.
- Keep queue payloads, callback messages, telemetry, and logs limited to opaque identifiers and non-PHI control metadata.
- Delete temporary provider objects promptly, retain successful encrypted output until report deletion, and make report deletion cancel pending work and cleanup idempotently.
- Keep deterministic fake dispatch and run-once adapters for local development and tests; production never falls back to inline or mock processing.

This change operationalizes the production extraction path selected by `add-production-extraction-provider`. It does not redefine the clinical extraction schema, document-ingestion authorization, or review workflow, and it does not add email, WhatsApp, or another external-connector intake path. V1 consent revocation remains deferred; report deletion still cancels pending work so deleted data cannot be recreated by a late delivery.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `document-extraction`: Add durable India-resident dispatch, immutable logical-document attempts, asynchronous Textract continuation, exact retry semantics, idempotent publication, interrupted-job recovery, and privacy-safe cleanup.

## Impact

Affected areas include authenticated logical-document finalization, extraction job and attempt persistence, transactional outbox delivery, SQS/SNS infrastructure, worker deployment, Textract callbacks, result publication, deletion cleanup, monitoring, and tests. This change depends on the first-release logical-document and job contracts, the production provider's phase contract, and the Supabase boundary's Mumbai-resident persistence and private storage. All queues, callback resources, worker compute, KMS keys, logs, and temporary objects remain in `ap-south-1`; no queue or log contains document content, extracted values, filenames, account contact data, profile data, or storage paths.
