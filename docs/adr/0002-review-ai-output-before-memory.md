# ADR 0002: Review AI Output Before Memory

## Status

Accepted

## Implementation Status

Implemented. The review flow stores pending extraction separately and memory only uses confirmed or edited fields.

## Context

AI extraction from medical records can be incomplete, ambiguous, or wrong. The app's living memory may influence what users remember, track, and ask doctors.

## Decision

AI output is untrusted until the user reviews it.

Only confirmed or edited extracted fields may enter medical memory. Pending, ignored, and incorrect fields must not update memory or appointment checklist context.

## Consequences

This reduces unsafe automation but adds a review step for users. The backend must keep raw extraction separate from user-confirmed medical facts, and every memory fact should link back to its source record and extracted field.
