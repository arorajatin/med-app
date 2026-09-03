## 1. Contract and Platform Preconditions

- [ ] 1.1 Add provider-neutral logical-document, processing-method, four-class extraction, prescription and `documented_condition_candidate` memory subtypes, component-provenance, and `SourceReference` types without exposing AWS response shapes to service code.
- [ ] 1.2 Add validated configuration for `pdfplumber`, Textract in `ap-south-1`, and Bedrock model `mistral.mistral-large-3-675b-instruct`; fail closed on another region, model, missing resource, or incomplete secret.
- [ ] 1.3 Provision or document customer-controlled Mumbai KMS, S3 `OutputConfig`, SNS, and SQS resources, including private access policy and 24-hour staging lifecycle rules.
- [ ] 1.4 Add Bedrock ZDR preflight and IAM/SCP enforcement for `data_retention_mode: none`; keep the production feature disabled until privacy and residency approval is recorded.
- [ ] 1.5 Define safe terminal and retryable failure codes shared with the queue-worker change and ensure payloads and telemetry contain no medical content.

## 2. Logical-Document Processing

- [ ] 2.1 Accept only upload-complete logical documents with authenticated route-stamped `direct_file` or `camera` provenance, then validate unencrypted PDF/JPEG/PNG composition, English-language lab/prescription scope, 15,000,000-byte document size, 20-page/part count, 10,000,000-byte image size, and 10,000-pixel image dimensions before provider submission.
- [ ] 2.2 Implement `pdfplumber` page inspection and the complete native-text gate for token count, printable-character ratio, coordinate bounds, and raster coverage.
- [ ] 2.3 Route the complete PDF to Textract when any nonblank page fails; route every image and ordered image set through Textract while preserving part order and logical pages.
- [ ] 2.4 Implement asynchronous Textract document analysis with layout, tables, and forms, persist a provider-neutral layout stream, and delete staging input/output after persistence.
- [ ] 2.5 Record `native_text | textract_ocr`, routing reason, input composition, component versions, request IDs, configuration hashes, and timings on every attempt.

## 3. Structured Extraction and Publication Boundaries

- [ ] 3.1 Invoke Bedrock Mistral Large 3 with normalized layout and stable source IDs only; exclude account profiles, aliases, authentication email, and other unrelated account or patient-matching context.
- [ ] 3.2 Validate schema output into `patient_evidence`, `document_metadata_candidate`, `metric_observation`, prescription `memory_candidate`, and literal `documented_condition_candidate` items; omit unsupported values and prohibit condition inference from medications, lab evidence, symptoms, upload context, or general associations.
- [ ] 3.3 Resolve every `SourceReference` to its source part, logical page, native word or Textract block IDs, text span, and normalized polygon; require a documented-condition span to contain the condition itself, omit a semantically unsupported condition candidate, and reject the entire result on a missing, mismatched, unresolved, or fabricated citation.
- [ ] 3.4 Implement exact account-local assignment using NFKC, whitespace normalization, case folding, and explicit aliases; route every other result, including no match, to `needs_assignment`.
- [ ] 3.5 Enforce review semantics: metadata and prescription memory remain pending; documented conditions remain pending for `confirm`, `edit`, or `ignore` and become trusted only after confirmation or edit; lab observations publish only after resolved assignment as `unreviewed_extracted`; and patient evidence never becomes trusted memory.
- [ ] 3.6 Commit raw component output, normalized items, source references, provenance, and statuses atomically while preserving prior committed and reviewed output on failure.

## 4. Privacy, Retention, and Operations

- [ ] 4.1 Enforce the governing accepted account-level consent snapshot before native extraction or provider invocation without another per-document or per-condition prompt, and prohibit production fallback to the mock, another provider, or cross-region inference.
- [ ] 4.2 Encrypt and restrict successful native/Textract and Bedrock raw output until report deletion; cascade report deletion through raw output, normalized results, and source references.
- [ ] 4.3 Delete Textract staging objects promptly after persistence or rejection and verify the 24-hour lifecycle backstop; retain failed-attempt safe envelopes for 30 days only.
- [ ] 4.4 Add content-free metrics and logs for component, method, family, status, timing, retry class, page and item counts, request IDs, and safe failure codes.
- [ ] 4.5 Integrate the queue-worker's canonical transient/terminal classification and at-most-three-attempt policy, including persisted jitter around 30 seconds and two minutes, without defining a narrower provider-specific retry set.

## 5. Verification and Rollout

- [ ] 5.1 Add contract tests for configuration fail-closed behavior, region and ZDR checks, mock-environment restrictions, provider response changes, and absence of PHI in payloads, logs, and metrics.
- [ ] 5.2 Add routing fixtures for eligible authenticated `direct_file`/`camera` digital PDFs, a PDF with one deficient page, blank pages, scans, photographs, ordered image sets, non-web ingress, encrypted/corrupt/oversized inputs, and unsupported languages and document families.
- [ ] 5.3 Add normalization tests for all four trust classes, optional source-linked date of birth retained only in patient evidence, literal documented conditions, medications/labs/symptoms/general-association negative cases, missing literal values, semantically unsupported condition citations, fabricated or mismatched source references, atomic partial failure, retry supersession, and raw-output deletion.
- [ ] 5.4 Add assignment fixtures for exact names, explicit aliases, Unicode/whitespace/case variants, duplicate names, absent matches, and cross-account isolation.
- [ ] 5.5 Build and version the de-identified English evaluation corpus; verify zero false assignments, 99.5% lab-tuple precision, 99.5% source-page accuracy, zero unanchored published observations, 95% prescription-candidate precision, and zero documented-condition candidates whose cited text does not literally name the condition.
- [ ] 5.6 Verify staging and production flags stay disabled until privacy, Mumbai residency, ZDR, Supabase migration/RLS, and quality gates pass; document gradual enablement, cost controls, and no-fallback rollback.
- [ ] 5.7 Run the backend test suite and strict OpenSpec validation.
- [ ] 5.8 Complete implementation review and finalize `review.md` with the reviewed commit, test evidence, findings, and resume state.
