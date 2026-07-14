# Architecture Decision Records

This folder tracks durable architectural decisions for the medical records backend.

ADRs should explain the decision and its rationale. They should not store raw agent transcripts or full step-by-step reasoning logs. Capture the useful engineering record: context, decision, tradeoffs, and consequences.

## How To Use

1. Copy `0000-template.md`.
2. Rename it using the next number and a short kebab-case title.
3. Mark the status as `Proposed`, `Accepted`, `Superseded`, or `Rejected`.
4. Mark the implementation status as `Not started`, `Partial`, `Implemented`, or `Deprecated`.
5. If a decision changes later, add a new ADR and mark the old one as superseded.

## Index

- [0000: Template](0000-template.md)
- [0001: Private By Default Medical Data](0001-private-by-default-medical-data.md)
- [0002: Review AI Output Before Memory](0002-review-ai-output-before-memory.md)
- [0003: Use FastAPI Python Backend](0003-use-fastapi-python-backend.md)
- [0004: Use SQLAlchemy Models](0004-use-sqlalchemy-models.md)
- [0005: Use Supabase Production Boundary](0005-use-supabase-production-boundary.md)
- [0006: Provider Agnostic AI Extraction](0006-provider-agnostic-ai-extraction.md)
- [0007: Store Raw And Structured Extraction](0007-store-raw-and-structured-extraction.md)
- [0008: Use Extraction Jobs](0008-use-extraction-jobs.md)
- [0009: Use Alembic Migrations](0009-use-alembic-migrations.md)
