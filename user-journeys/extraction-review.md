# Extraction and Medical-Memory Review Journey

## Goal

Separate automatically captured lab measurements from review-required document metadata, prescription memory, and conditions that are literally written in a submitted prescription or lab report.

## Extraction result

After successful extraction and patient assignment, the report can expose:

- patient-match evidence;
- document-metadata candidates such as report date, issuer, type, and display name;
- deterministic metric observations;
- prescription medication and instruction candidates;
- a `documented_condition_candidate` only when the document itself contains exact text that names the condition.

The system uses native text only when every PDF page passes validation; otherwise it processes the whole PDF with OCR. Images always use OCR. The user is not asked to select a mode.

Medication names or doses, lab values or ranges, abnormal flags, symptoms, optional upload context, and general medical knowledge never create a condition candidate. The condition itself must be written in the prescription or lab report and linked to the exact supporting source text.

## Document-metadata review

1. Extracted report date, issuer, type, and display-name suggestions remain pending.
2. The account manager confirms or edits metadata before it becomes trusted for report-date ordering or display.
3. Optional upload context remains separate from extracted metadata and never becomes evidence for a condition or diagnosis.

## Deterministic observations

1. Literal measurements are stored automatically in a report-linked observations table.
2. They retain original value/unit, optional normalized value, reference range, observation date, confidence, and source location when available.
3. They remain labeled unreviewed and outside medical memory.
4. They do not block memory-review completion.
5. The account manager can correct or exclude an observation while its original extraction remains auditable.
6. Correcting or excluding an observation does not confirm, edit, ignore, or otherwise change a condition candidate from the same report.

## Prescription-memory review

1. The account manager opens a report marked `Review needed`.
2. Each prescription medication or instruction candidate appears with required page and source context.
3. Every candidate is selected by default.
4. The account manager may edit a candidate.
5. The account manager may uncheck a candidate that should not enter memory.
6. The account manager submits the review.
7. Submission confirms selected unchanged candidates and trusts submitted edits.
8. Unchecked candidates become ignored and do not contribute to memory.
9. Merely viewing a selected-by-default candidate does not approve it.

## Documented-condition review

1. A documented-condition item appears only when the prescription or lab report literally names the condition.
2. It shows the label `Condition written in this document — verify before saving`.
3. It shows the exact extracted condition text and the exact page and source span that names the condition.
4. It begins pending and is not selected or approved by default.
5. The account manager must choose `confirm`, `edit`, or `ignore`.
6. `confirm` trusts the exact written condition; `edit` trusts the submitted replacement while retaining the original text and source; `ignore` keeps the item outside memory.
7. Only a confirmed or edited documented condition can contribute to medical memory, Chat evidence, Drive condition groups, or appointment evidence.
8. Confirming or editing a condition does not make any metric observation in the same report trusted medical memory.

## Review completion

1. Review completes only after every prescription and documented-condition candidate has a non-pending decision.
2. Deterministic metric observations do not block completion.
3. Revisiting a decision supersedes stale active memory without breaking audit provenance.

## Trust rules

- Extracted semantic memory always requires an explicit review decision; selected prescription items become trusted only when the review is submitted.
- User-entered onboarding conditions and medications are trusted immediately with user-attested provenance.
- Metric observations never become personal-memory Chat evidence merely because they were captured.
- V1 never infers a condition from medication, dosage, lab values, reference ranges, flags, symptoms, optional context, or general associations.
- V1 extraction does not create inferred diagnoses, follow-ups, interpretations, or insight candidates.
- Pending or ignored documented conditions remain outside all trusted downstream uses.
- Unresolved patient assignment prevents both observation and candidate-memory publication.
