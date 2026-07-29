# Extraction and Medical-Memory Review Journey

## Goal

Separate automatically captured report measurements from AI-derived medical memory that requires an explicit submitted review.

## Extraction result

After successful extraction and patient assignment, the report can expose:

- patient-match evidence;
- trusted-document-metadata candidates such as report date and type;
- deterministic metric observations;
- proposed conditions;
- proposed medications;
- proposed follow-ups;
- proposed insights.

The system chooses text, OCR/vision, or hybrid processing. The user is not asked to select an OCR mode.

## Deterministic observations

1. Literal measurements are stored automatically in a report-linked observations table.
2. They retain original value/unit, optional normalized value, reference range, observation date, confidence, and source location when available.
3. They remain labeled unreviewed and outside medical memory.
4. They do not block memory-review completion.
5. The account manager can correct or exclude an observation while its original extraction remains auditable.

## Candidate-memory review

1. The account manager opens a report marked `Review needed`.
2. Each proposed condition, medication, follow-up, or insight appears with source context when available.
3. Every candidate is selected by default.
4. The account manager may edit a candidate.
5. The account manager may uncheck a candidate that should not enter memory.
6. The account manager submits the review.
7. Submission confirms selected unchanged candidates and trusts submitted edits.
8. Unchecked candidates become ignored and do not contribute to memory.
9. Merely viewing a selected-by-default candidate does not approve it.
10. Review completes after every candidate-memory item has a decision.
11. Revisiting a decision supersedes stale active memory without breaking audit provenance.

## Trust rules

- AI-derived semantic memory always requires submitted review.
- User-entered onboarding conditions and medications are trusted immediately with user-attested provenance.
- Metric observations never become personal-memory Chat evidence merely because they were captured.
- Unresolved patient assignment prevents both observation and candidate-memory publication.

