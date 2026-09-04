## Why

The mock extractor is deterministic for tests but cannot process real scans, photographs, or varied medical documents. Production extraction needs a fixed India-resident pipeline, deterministic OCR routing, auditable source references, and explicit trust boundaries before implementation can begin.

## What Changes

- Add a production pipeline that uses `pdfplumber` for eligible machine-readable PDFs, Amazon Textract for OCR and layout, and Amazon Bedrock Mistral Large 3 (`mistral.mistral-large-3-675b-instruct`) for schema-constrained extraction. Textract, Bedrock, and all staging resources run only in `ap-south-1`.
- Process one immutable logical document per attempt. V1 accepts unencrypted PDF, JPEG, and PNG inputs containing an English-language lab report or prescription only after an authenticated `direct_file` or `camera` web-upload route completes the logical document.
- Apply a whole-PDF native-text gate: if any nonblank page fails the gate, route the entire PDF through Textract. Images and ordered image sets always use Textract.
- Normalize successful output into `patient_evidence`, `document_metadata_candidate`, `metric_observation`, and `memory_candidate` trust classes instead of treating every extracted value as review-gated memory. A memory candidate may contain prescription instructions or a `documented_condition_candidate` copied only from condition text literally present in the submitted prescription or lab report.
- Require every normalized item to cite a validated `SourceReference`; reject an attempt atomically when its output is malformed, incomplete, or cites nonexistent source content.
- Keep profile matching outside the provider. A date of birth may be extracted as source-linked patient evidence, but it is not copied to a profile or used for matching. Only an exact, account-local name or alias match may resolve automatically.
- Enforce the governing account-level consent snapshot without a per-document or per-condition prompt, Bedrock zero-data-retention eligibility, encrypted raw-output retention until report deletion, redacted observability, and fixture-based rollout gates including zero documented-condition candidates without literal cited condition text.

This change does not auto-confirm document metadata, prescription facts, or documented conditions; diagnose or infer conditions from medication details, lab observations, symptoms, or general medical knowledge; add external-connector ingestion; use extracted content for fuzzy identity matching; or remove the mock provider from local and test environments. Documented conditions begin pending and require `confirm`, `edit`, or `ignore`. Durable queue dispatch and worker recovery are specified by `add-queue-backed-extraction-worker`.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `document-extraction`: Select the production extraction pipeline, define authenticated web-upload logical-document routing and source references, separate extraction trust classes, extract only literally documented conditions, and require atomic, privacy-safe processing.

## Impact

Affected areas include `apps/api/app/ai/`, authenticated logical-document assembly, extractor dependency selection, AWS and Bedrock configuration, secrets and IAM policy, extraction transaction boundaries, encrypted raw-result storage, fixtures, monitoring, and operating cost. This change depends on the first-release family-health change for the general trust-class, profile-assignment, and publication boundaries. The queue-worker change consumes this adapter and owns durable dispatch and retry execution. Production enablement requires both changes plus the Supabase-boundary change's Mumbai-resident application storage and RLS.
