# ADR 0008: Use Extraction Jobs

## Status

Accepted

## Implementation Status

Partial. The job model and status lifecycle exist; production queue-backed workers are not implemented yet.

## Context

AI extraction can be slow, fail, or require retries. It should not be permanently tied to the HTTP upload request lifecycle.

## Decision

Represent extraction as a job with explicit lifecycle status.

Local development may run jobs inline. Production should process extraction in a separate worker backed by a real queue.

## Consequences

Uploads can evolve toward fast request handling while extraction happens asynchronously. The job model gives the API a stable place for status, failure reasons, retries, raw output, and extracted fields.
