## Context

`Extractor` already provides a provider-neutral input and output boundary, and `MockExtractor` proves the current end-to-end flow. The current dependency raises HTTP 501 for any non-mock provider. V1 records arrive only through authenticated `direct_file` or `camera` web-upload routes as machine-readable PDFs, scans, photographs, and ordered image sets; provider output can be malformed or plausible but wrong. Because the documents contain health data, the production path must also prove the governing account-level consent snapshot, India-only processing, retention controls, source linkage, and atomic publication without prompting again for each document or condition candidate.

This change defines the production extraction adapter and its normalized contract. Durable dispatch, leases, and worker recovery remain in `add-queue-backed-extraction-worker`. Account-scoped storage and RLS remain in `adopt-supabase-data-boundary`. Patient assignment and profile publication remain in `define-first-release-family-health-experience` and consume the evidence classes defined here.

## Goals / Non-Goals

**Goals:**

- Select one production pipeline and region without coupling service code to AWS response shapes.
- Process a complete logical document with deterministic native-text versus OCR routing.
- Preserve page-level source evidence for every normalized item.
- Separate assignment evidence, metadata suggestions, lab observations, prescription memory, and literally documented condition candidates by trust class and review state.
- Fail atomically, retain encrypted audit material for the life of the report, and expose only safe operational diagnostics.
- Gate production enablement on representative, de-identified quality fixtures.

**Non-Goals:**

- Diagnose, interpret clinical significance, or infer a condition from medication details, lab values, ranges, flags, symptoms, or other facts not literally supported by the document.
- Support languages other than English, document families other than labs and prescriptions, encrypted PDFs, archives, or arbitrary office formats in V1.
- Let the model see account profiles or perform patient matching.
- Add durable queue infrastructure or define email, WhatsApp, or any other external-connector transport.
- Store document text, extracted medical values, or raw provider responses in logs or analytics.

## Decisions

### Use a fixed Mumbai-resident pipeline

The production adapter uses these pinned components:

1. `pdfplumber` reads positioned words and geometry from PDFs that pass the native-text gate.
2. Amazon Textract document analysis supplies OCR, layout, tables, and forms for all images and for PDFs that fail the gate. PDF processing uses asynchronous Textract APIs with Mumbai S3, SNS, and SQS resources and a customer-controlled, KMS-encrypted `OutputConfig` bucket.
3. Amazon Bedrock invokes Mistral Large 3 using model ID `mistral.mistral-large-3-675b-instruct` and schema-constrained output.

Textract, Bedrock, S3, SNS, SQS, and KMS resources SHALL be in `ap-south-1`; cross-region inference profiles and provider fallback are prohibited. Production startup or feature enablement fails closed unless the configured region and model match this contract, Bedrock reports zero-data-retention eligibility, and policy prevents a non-ZDR invocation. The mock remains available only in explicitly allowed local and test environments.

### Process an immutable logical document

One attempt receives one ordered logical document with stable source-part ordinals. Supported compositions are one PDF, one image, or an ordered JPEG/PNG image set. Limits are:

- 15,000,000 bytes per logical document;
- 20 logical pages or source parts;
- 10,000,000 bytes per image; and
- 10,000 pixels per image dimension.

Inputs must be unencrypted PDF, JPEG, or PNG. A valid but unsupported medical-document family is retained by the owning workflow but ends extraction with `unsupported_document_type`; it does not publish normalized clinical output. The supported V1 families are English-language lab reports and prescriptions.

### Route a PDF as one unit

`pdfplumber` first inspects every page and produces positioned word tokens. Native extraction is selected only when every nonblank page:

- opens successfully and the document is unencrypted;
- contains at least 20 positioned word tokens;
- has at least 99% printable extracted characters;
- has every token coordinate within page bounds; and
- has no raster image covering 50% or more of the page.

If any nonblank page fails, the complete PDF is sent to Textract. This avoids mixing coordinate systems within an attempt and keeps source references deterministic. Images and ordered image sets always use Textract. The attempt records `processing_method = native_text | textract_ocr`, the routing reason, input composition, component versions, request identifiers, and timings.

Both paths produce the same provider-neutral layout stream: stable word or block IDs, logical page number, text, and normalized bounding polygon. Blank pages remain addressable but do not independently fail the native-text token threshold.

### Constrain model input and output

Mistral receives only the normalized document layout, stable source IDs, and extraction instructions. It does not receive account, profile, authentication-email, or other unrelated account context. The adapter validates schema shape, permitted document family, supported trust classes, literal values, and every citation before it can stage a success.

Every normalized item has one or more `SourceReference` values containing the source-part ID, logical page number, cited native word IDs or Textract block IDs, the supporting text span, and a normalized bounding polygon. All identifiers and geometry must resolve against the persisted layout for that attempt. One nonexistent or mismatched reference makes the complete attempt terminally invalid; the service does not publish the remaining items.

### Use four explicit trust classes

The normalized contract contains exactly these V1 classes:

1. `patient_evidence`: literal patient name and optional DOB or patient identifier, used only by account-local assignment.
2. `document_metadata_candidate`: report date, issuer or provider, document type, and display-name suggestions. These require user review before becoming trusted metadata.
3. `metric_observation`: literal lab analyte, decimal or categorical value, unit, reference range, flag, and observation date. These may publish automatically only after profile assignment resolves and remain `unreviewed_extracted`, correctable, and excluded from trusted memory.
4. `memory_candidate`: either literal prescription medication/instruction fields or a `documented_condition_candidate` containing condition text literally written in the prescription or lab report. These begin pending and require explicit review before trusted memory publication.

Prescription candidates retain medication name, strength, dosage form, dose, route, frequency, duration, and instructions when present. A documented-condition candidate retains the exact condition text and a source reference to the span that names it. Medication details, lab values, ranges, flags, symptoms, and general medical associations never create a condition candidate by themselves. A documented condition requires `confirm`, `edit`, or `ignore`; only confirmation or a reviewed replacement may enter trusted memory.

The adapter omits unavailable or unsupported values instead of inferring them. It does not produce diagnoses, clinical interpretations, or provider-authored patient matches. A resolvable citation to text that does not itself name the proposed condition is semantically unsupported and causes that candidate to be omitted; a missing, mismatched, or fabricated source reference invalidates the complete attempt.

### Keep identity resolution deterministic and local

The provider returns source-linked `patient_evidence`; a local service performs assignment only against profiles and explicit aliases owned by the same account. V1 normalization uses Unicode NFKC, surrounding and repeated whitespace normalization, and case folding. Automatic assignment requires exactly one exact full-name or explicit-alias match and no contradictory extracted DOB. No match, multiple matches, or contradictory DOB becomes `needs_assignment`. Fuzzy, phonetic, confidence-only, and cross-account matching are prohibited.

### Commit one complete attempt or nothing

Native/Textract output, Mistral output, normalized items, source references, component provenance, attempt status, and record status are staged and validated as one result. A transaction publishes the complete set and success status together. Any reading, provider, schema, citation, normalization, or commit failure publishes no new result set and leaves previously committed or reviewed output unchanged.

The queue-worker change owns the canonical retry classification. It permits at most three total numbered attempts, with persisted jitter around 30 seconds and two minutes, for provider/network timeouts, throttling or HTTP 429, provider/AWS 5xx or temporary unavailability, transient S3/SQS/SNS/KMS transport failures, interrupted claims, retryable Textract failures, and the bounded Textract callback timeout. Invalid input, unsupported document family, malformed schema, invalid source references, deterministic normalization failure, region/ZDR/authentication/authorization/credential/key/role/policy/configuration failure, and exhausted transient attempts are terminal. Each retry creates the next numbered attempt against the same immutable logical-document manifest; it cannot append partial output from a prior attempt.

### Retain audit output while deleting provider staging promptly

Successful native/Textract layout and raw Bedrock output are encrypted, access-controlled operational records retained until the source report is deleted. Report deletion removes the raw output, normalized results, and source-reference material. Routine clients cannot fetch raw provider output; exceptional operational access is separately authorized and audited.

Textract input and `OutputConfig` objects are deleted after application persistence succeeds, with a 24-hour lifecycle backstop. Failed attempts retain only a safe, non-clinical failure envelope for 30 days. Bedrock uses `data_retention_mode: none`, and IAM or SCP policy prevents relaxing that mode.

### Keep observability content-free

Metrics cover component, method, document family, attempt status, duration, retry class, page count, and normalized-item counts. Logs contain internal identifiers, request IDs, configuration versions or hashes, and safe failure codes. Logs and queue payloads exclude file/document hashes, file bytes, document text, source spans, raw responses, extracted values, patient identifiers, and credentials.

### Gate rollout on precision and provenance

The evaluation corpus is de-identified and covers machine-readable PDFs, scans, photographs, multi-page lab reports, ordered images, and prescriptions. Production enablement requires:

- zero false automatic profile assignments;
- at least 99.5% exact precision for published lab `(metric name, value, unit, source page)` tuples;
- at least 99.5% correct source-page attribution;
- zero unanchored or fabricated published observations; and
- at least 95% precision for review-required prescription memory candidates; and
- zero documented-condition candidates whose cited text does not literally name the extracted condition.

Recall is reported but is not a safety gate; omission is preferable to an incorrect published value. Results are versioned by corpus, `pdfplumber`, Textract API/configuration, Bedrock model, prompt schema, and normalizer.

## Risks / Trade-offs

- Native text can be present but unusable -> apply the whole-PDF gate and route the complete PDF to Textract on any page failure.
- Model output can be plausible but unsupported -> require resolvable source references and reject the complete attempt on any invalid citation.
- Medication or lab evidence can look condition-specific without naming a condition -> permit a documented-condition candidate only when its exact cited span literally names the condition, otherwise omit it.
- Strict exact matching may leave more records unassigned -> prefer manual resolution over a false family-profile assignment.
- Provider retention or regional processing may violate policy -> fail closed on region and ZDR preflight and keep the production feature disabled until privacy approval.
- Retaining raw successful output increases sensitive-data exposure -> encrypt it, isolate operational access, audit reads, and bind deletion to report deletion.
- Large or complex documents may exceed provider limits -> enforce product limits before submission and return a safe terminal failure.

## Migration Plan

1. Add the four-class normalized contract, including prescription and literal documented-condition memory subtypes, authenticated web-upload logical-document inputs, component provenance, source-reference validation, and safe failure taxonomy behind a disabled production feature flag.
2. Configure Mumbai KMS, S3, SNS, SQS, Textract, and Bedrock resources; verify region and ZDR policy before accepting production traffic.
3. Implement and contract-test the native gate, Textract conversion, Mistral schema adapter, literal-condition/no-inference validation, atomic commit, and encrypted raw-result lifecycle.
4. Run the de-identified corpus and publish the versioned quality report. Do not enable production unless every gate passes.
5. Enable in staging with content-free telemetry, then roll out production gradually after privacy, residency, RLS, and operational reviews.

Rollback disables new production extraction. It SHALL NOT route production medical documents to the mock or another region/provider. Previously committed results remain linked to their attempt and source until their report is deleted.
