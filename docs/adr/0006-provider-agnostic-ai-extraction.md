# ADR 0006: Provider Agnostic AI Extraction

## Status

Accepted

## Implementation Status

Partial. The provider interface and mock extractor exist; real OCR/model provider adapters are not implemented yet.

## Context

Medical record extraction may require OCR, vision models, text parsing, or specialist document AI. Provider choice may change based on cost, quality, privacy, or document type.

## Decision

Keep AI extraction behind an internal provider interface.

The backend should depend on a normalized extraction contract, not a specific model vendor. The current mock extractor exists for local development and tests.

## Consequences

API routes, review logic, and memory logic can stay stable while provider adapters change. Real providers must return document type, extracted fields, confidence, source references where available, and raw provider output.
