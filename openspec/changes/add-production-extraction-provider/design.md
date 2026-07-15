## Context

`Extractor` already provides a provider-neutral input and output boundary, and `MockExtractor` proves the end-to-end flow. The current dependency raises HTTP 501 for any other provider. Real documents may require OCR, vision, multipage handling, and provider-specific source coordinates. They also contain sensitive health data and can return partially malformed output.

## Goals / Non-Goals

**Goals:**

- Add one production-ready provider without coupling service code to it.
- Preserve pending review, raw-output auditability, and source linkage.
- Fail atomically and expose safe operational diagnostics.
- Measure extraction quality against representative, de-identified fixtures.

**Non-Goals:**

- Automatically trust or diagnose from provider output.
- Support every document type or provider in the first adapter.
- Add durable queue infrastructure, which is tracked separately.
- Store raw medical content in logs or analytics.

## Decisions

### Select the provider through an evaluation gate

Before implementation, compare candidate providers on supported inputs, structured output, source references, regional processing, retention controls, contract terms, latency, and cost. Record the selection and rejected alternatives in this design.

### Keep the normalized extractor contract

Provider-specific request and response types remain inside the adapter. The adapter maps output to `DocumentExtraction` and `ExtractedDatum`. Extend the internal contract only for provider-neutral needs such as page or bounding-box references.

### Stage an attempt before committing it

Normalize and validate the complete provider response before publishing new fields. Use a transaction boundary or temporary attempt records so an exception cannot commit partial pending fields alongside a failed job.

### Keep the mock provider

The mock remains the default for fast, deterministic local and unit tests. Production configuration validation prevents selecting it outside allowed environments.

### Redact operational output

Metrics cover provider, document category, status, duration, retry class, and field counts. Logs exclude file bytes, raw response bodies, extracted values, and credentials. Restricted diagnostic access requires a separate operational policy.

## Risks / Trade-offs

- Provider output may look plausible while being wrong -> keep every field pending and measure against fixtures.
- Provider retention or regional processing may violate privacy requirements -> block selection until terms and configuration are approved.
- Large or multipage documents may exceed limits -> validate size and page constraints before submission and return a safe failure.
- Provider schema changes may break normalization -> pin API versions and run adapter contract tests.

## Migration Plan

1. Build a de-identified evaluation set and choose a provider.
2. Implement the adapter and configuration behind a non-production flag.
3. Compare output against fixtures and exercise failure paths.
4. Enable it in staging with redacted metrics.
5. Roll out production configuration gradually while retaining the mock only for local and tests.

Rollback disables the production provider and stops new extraction. It does not silently route production medical documents to the mock. Existing reviewed facts remain linked to their source attempts.

## Open Questions

- Which provider and region satisfy the required medical-data agreement?
- Which input formats and maximum page counts form the first supported set?
- How long may raw provider output be retained, and who may inspect it?
- What fixture-level accuracy thresholds are required before rollout?
