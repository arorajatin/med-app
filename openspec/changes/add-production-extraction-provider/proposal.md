## Why

The mock extractor is deterministic for tests but cannot process real scans, images, or varied medical documents. A production provider is needed without weakening the existing consent and human-review boundary.

## What Changes

- Evaluate and select a provider that meets privacy, accuracy, latency, and cost constraints.
- Implement a production adapter behind the existing extractor contract.
- Support OCR or vision input for the allowed medical document formats.
- Normalize provider output into the existing reviewable field model with source context.
- Make extraction attempts atomic so failed output cannot leak into review or memory.
- Add redacted observability, fixtures, and provider contract tests.

This change does not auto-confirm medical facts, diagnose conditions, or remove the mock provider from local tests.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `document-extraction`: Add production provider selection, real document processing, and atomic failure behavior.

## Impact

Affected areas include `app/ai/`, extractor dependency selection, configuration and secrets, extraction transaction boundaries, fixtures, monitoring, and operating cost. Medical-data privacy and AI trust are directly affected; explicit consent and manual review remain mandatory.
