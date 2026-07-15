## Why

The backend predates OpenSpec and needs a truthful starting point for future spec-driven changes. This baseline records the implemented MVP and separates it from unfinished production infrastructure.

## What Changes

- Capture current authenticated ownership and privacy behavior.
- Capture family profile and medical record workflows.
- Capture consented extraction jobs and structured results.
- Capture the human review boundary and reviewed medical memory.
- Capture appointment preparation and feedback behavior.
- Preserve the architectural decisions that shaped the implementation.

## Capabilities

### New Capabilities

- `access-control`: Authentication modes and owner isolation.
- `family-profiles`: User-owned profiles for self and family members.
- `medical-records`: Private records, consent, and file uploads.
- `document-extraction`: Extraction jobs and reviewable outputs.
- `reviewed-medical-memory`: Human-reviewed facts derived from records.
- `appointment-preparation`: Appointments, checklists, and feedback.

### Modified Capabilities

None. This change establishes the initial OpenSpec baseline.

## Impact

This is a documentation migration only. It describes the behavior implemented in `app/`, the contracts exposed by `app/api/routes.py`, and the flows exercised by `tests/` without changing runtime behavior.
