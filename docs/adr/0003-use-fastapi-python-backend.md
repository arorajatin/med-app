# ADR 0003: Use FastAPI Python Backend

## Status

Accepted

## Implementation Status

Implemented. The backend exposes FastAPI routes and runs through Uvicorn.

## Context

The backend needs authenticated APIs, file upload handling, AI/document processing, background extraction jobs, and a mobile-friendly contract. Python was chosen for the backend.

## Decision

Use FastAPI as the backend HTTP framework.

Use Pydantic schemas for API validation and Uvicorn as the ASGI server.

## Consequences

The backend stays close to Python AI tooling while exposing typed HTTP APIs for mobile clients. Production deployment should run Uvicorn without `--reload` and behind a real process manager or platform runtime.
