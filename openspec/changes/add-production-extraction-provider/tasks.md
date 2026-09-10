## 1. Contract and Platform Preconditions

- [ ] 1.1 Add provider-neutral logical-document, processing-method, four-class extraction, prescription and `documented_condition_candidate` memory subtypes, component-provenance, and `SourceReference` types without exposing AWS response shapes to service code.
- [ ] 1.2 Add validated configuration for `pdfplumber`, Textract in `ap-south-1`, and Bedrock model `mistral.mistral-large-3-675b-instruct`; fail closed on another region, model, missing resource, or incomplete secret.
- [ ] 1.3 Provision or document customer-controlled Mumbai KMS, S3 `OutputConfig`, SNS, and SQS resources, including private access policy and 24-hour staging lifecycle rules.
- [ ] 1.4 Add Bedrock ZDR preflight and IAM/SCP enforcement for `data_retention_mode: none`; keep the production feature disabled until privacy and residency approval is recorded.
- [ ] 1.5 Define safe terminal and retryable failure codes shared with the queue-worker change and ensure payloads and telemetry contain no medical content.

## 2. Logical-Document Processing

- [ ] 2.1 Validate upload completion, authenticated route provenance, supported composition/family/language, and all [logical-document limits](specs/document-extraction/spec.md#requirement-bounded-logical-document-inputs) before provider submission.
- [ ] 2.2 Implement `pdfplumber` page inspection and the complete native-text gate for token count, printable-character ratio, coordinate bounds, and raster coverage.
- [ ] 2.3 Route the complete PDF to Textract when any nonblank page fails; route every image and ordered image set through Textract while preserving part order and logical pages.
- [ ] 2.4 Implement asynchronous Textract document analysis with layout, tables, and forms, persist a provider-neutral layout stream, and delete staging input/output after persistence.
- [ ] 2.5 Record `native_text | textract_ocr`, routing reason, input composition, component versions, request IDs, configuration hashes, and timings on every attempt.

## 3. Structured Extraction and Publication Boundaries

- [ ] 3.1 Invoke Bedrock Mistral Large 3 with normalized layout and stable source IDs only; exclude account profiles, aliases, authentication email, and other unrelated account or patient-matching context.
- [ ] 3.2 Validate all four [trust classes and memory subtypes](specs/document-extraction/spec.md#requirement-explicit-extraction-trust-classes), including literal patient-subject conditions and every omission/no-inference rule; optional upload context cannot supply clinical evidence.
- [ ] 3.3 Implement [source-reference validation](design.md#constrain-model-input-and-output) and [condition-span validation](design.md#use-four-explicit-trust-classes), preserving candidate omission versus whole-attempt rejection.
- [ ] 3.4 Integrate the first-release [account-local assignment service](../define-first-release-family-health-experience/design.md#treat-direct-upload-selection-as-provisional-patient-context) with production patient evidence.
- [ ] 3.5 Enforce each trust class's [publication and review boundary](specs/document-extraction/spec.md#requirement-explicit-extraction-trust-classes).
- [ ] 3.6 Commit raw component output, normalized items, source references, provenance, and statuses atomically while preserving prior committed and reviewed output on failure.

## 4. Privacy, Retention, and Operations

- [ ] 4.1 Enforce authenticated account ownership before native extraction or provider invocation, and prohibit production fallback to the mock, another provider, or cross-region inference.
- [ ] 4.2 Encrypt and restrict successful native/Textract and Bedrock raw output until report deletion; cascade report deletion through raw output, normalized results, and source references.
- [ ] 4.3 Delete Textract staging objects promptly after persistence or rejection and verify the 24-hour lifecycle backstop; retain failed-attempt safe envelopes for 30 days only.
- [ ] 4.4 Add metrics and logs using the [content-free observability contract](design.md#keep-observability-content-free).
- [ ] 4.5 Integrate the queue worker's [canonical retry policy](../add-queue-backed-extraction-worker/design.md#apply-one-exact-automatic-retry-policy) without narrowing its failure classes.

## 5. Verification and Rollout

- [ ] 5.1 Add contract tests for configuration fail-closed behavior, region and ZDR checks, mock-environment restrictions, provider response changes, and absence of PHI in payloads, logs, and metrics.
- [ ] 5.2 Add routing fixtures for eligible authenticated `direct_file`/`camera` digital PDFs, a PDF with one deficient page, blank pages, scans, photographs, ordered image sets, non-web ingress, encrypted/corrupt/oversized inputs, and unsupported languages and document families.
- [ ] 5.3 Test every [trust-class scenario](specs/document-extraction/spec.md#requirement-explicit-extraction-trust-classes) and source-validation rule in 3.3, plus atomic partial failure, retry supersession, and raw-output deletion.
- [ ] 5.4 Add assignment fixtures for exact names, explicit aliases, Unicode/whitespace/case variants, duplicate names, absent matches, and cross-account isolation.
- [ ] 5.5 Build and version the de-identified English evaluation corpus and verify every [precision and provenance gate](design.md#gate-rollout-on-precision-and-provenance).
- [ ] 5.6 Verify staging and production flags stay disabled until privacy, Mumbai residency, ZDR, Supabase migration/RLS, and quality gates pass; document gradual enablement, cost controls, and no-fallback rollback.
- [ ] 5.7 Run the backend test suite and strict OpenSpec validation.
- [ ] 5.8 Complete implementation review and finalize `review.md` with the reviewed commit, test evidence, findings, and resume state.
