# Medical Metrics Journey

## Goal

Preserve deterministic values from reports as source-linked observations without turning those measurements into condition conclusions.

## First-release observations

1. Extraction identifies a literal measurement such as test name, value, unit, reference range, and observation date.
2. After patient assignment resolves, the system stores the measurement automatically.
3. The observation retains:
   - family profile;
   - source report and source location;
   - extraction attempt and confidence;
   - original value and unit;
   - optional normalized value and unit;
   - optional reference range;
   - observation date;
   - optional body-system classification.
4. The observation is visibly unreviewed and does not become medical memory.
5. The account manager can inspect it from report details.
6. The account manager can correct or exclude it without removing original provenance.
7. Extraction retry supersedes matching active observations instead of duplicating them.
8. A measurement, reference range, abnormal flag, or optional body-system classification is not evidence that a condition exists.

## Memory separation

1. A literal prescription medication or instruction is emitted as a candidate-memory item rather than a metric observation.
2. Prescription candidates are selected by default but become trusted only after the account manager submits the review.
3. If a prescription or lab report separately contains exact text that names a condition, extraction may create a pending `documented_condition_candidate` with that exact text and exact source reference.
4. The condition candidate is labeled `Condition written in this document — verify before saving` and requires `confirm`, `edit`, or `ignore`.
5. Only a confirmed or edited documented condition can enter trusted memory, Chat evidence, Drive condition groups, or appointment evidence.
6. Chat and appointment context exclude unreviewed observations, unsubmitted prescription candidates, and pending or ignored documented conditions.

## No condition inference

- Medication names, strengths, doses, routes, frequencies, durations, or instructions do not establish a condition.
- Lab values, reference ranges, and abnormal flags do not establish a condition.
- Symptoms, optional upload context, nearby text, and general medical knowledge do not establish a condition.
- When the source does not literally name a condition, extraction creates no documented-condition candidate, even if the medication or measurement is commonly associated with one.

## Independent review decisions

1. A report may contain both a metric observation and a separate documented-condition candidate.
2. Confirming or editing the documented condition does not make the observation trusted medical memory.
3. Correcting or excluding the observation does not confirm, edit, ignore, or otherwise change the documented-condition candidate.
4. The original source and review history remain auditable for both items.

## Longitudinal foundation

The first release can retrieve a profile's active observations for one metric in date order with source-report references. It does not yet provide the full interactive body-system graph.

## Safety behavior

- A value that cannot be supported by the source is omitted or marked unavailable.
- OCR/model confidence does not transform an observation into trusted medical advice.
- Optional upload context is descriptive only and never serves as source evidence for a condition.
- Cross-account observation reads behave as unavailable.
