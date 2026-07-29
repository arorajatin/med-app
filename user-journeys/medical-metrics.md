# Medical Metrics Journey

## Goal

Preserve deterministic values from reports as source-linked observations while keeping AI interpretation behind the reviewed-memory boundary.

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

## Insight separation

1. A human-readable condition, medication, follow-up, or interpretation is emitted as a candidate-memory item rather than a metric observation.
2. It becomes trusted only after submitted review.
3. Chat and appointment context exclude unreviewed observations and candidate memory.

## Longitudinal foundation

The first release can retrieve a profile's active observations for one metric in date order with source-report references. It does not yet provide the full interactive body-system graph.

## Safety behavior

- A value that cannot be supported by the source is omitted or marked unavailable.
- OCR/model confidence does not transform an observation into trusted medical advice.
- Cross-account observation reads behave as unavailable.

