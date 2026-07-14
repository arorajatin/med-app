# ADR 0007: Store Raw And Structured Extraction

## Status

Accepted

## Implementation Status

Implemented. Extraction jobs store raw output, and extracted fields store structured reviewable values.

## Context

AI providers may return useful metadata that does not fit the first normalized schema. At the same time, the app needs structured fields for review, memory, and appointment context.

## Decision

Store both raw extraction output and normalized extracted fields.

Raw output is kept on the extraction job. Normalized fields are stored as reviewable extracted fields with type, label, value, confidence, source reference, and confirmation status.

## Consequences

The system remains auditable and can reprocess old records as extraction improves. Storage usage increases, and sensitive raw output must follow the same privacy and deletion rules as medical records.
