from __future__ import annotations

import re

from app.ai.base import DocumentExtraction, ExtractedDatum

CONDITION_FIELD_TOKENS = frozenset(
    {"condition", "diagnosis", "disease", "impression", "problem"}
)
CONDITION_SAFETY_POLICY = "literal_source_validation_required"
TEMPORARILY_PERMITTED_DOCUMENT_TYPES = frozenset(
    {"medical_record", "lab_report", "prescription", "discharge_summary", "imaging_report"}
)
TEMPORARILY_PERMITTED_LEGACY_FIELD_TYPES = frozenset(
    {"document_type", "record_date", "test_result", "medication", "follow_up"}
)
TEMPORARILY_PERMITTED_LEGACY_MEMORY_CATEGORIES = frozenset(
    {"medication", "test_result", "follow_up"}
)


def is_condition_shaped_name(value: str) -> bool:
    tokens = {
        token
        for token in re.split(r"[^a-z0-9]+", value.strip().casefold())
        if token
    }
    return bool(tokens & CONDITION_FIELD_TOKENS)


def is_condition_shaped_field(field: ExtractedDatum) -> bool:
    """Return whether an untyped extractor field could represent a condition."""

    return is_condition_shaped_name(field.field_type)


def is_temporarily_permitted_legacy_field_type(field_type: str) -> bool:
    return field_type.strip().casefold() in TEMPORARILY_PERMITTED_LEGACY_FIELD_TYPES


def is_temporarily_permitted_legacy_memory_category(category: str) -> bool:
    return category.strip().casefold() in TEMPORARILY_PERMITTED_LEGACY_MEMORY_CATEGORIES


def enforce_condition_safety(
    extraction: DocumentExtraction,
    *,
    allow_legacy_fields: bool = False,
) -> DocumentExtraction:
    """Fail closed until condition candidates have resolvable literal source evidence.

    The baseline extraction contract has only a free-form field type and an opaque
    source-reference string. It cannot prove that a proposed condition was copied
    from the document. Only explicitly permitted fields from the built-in mock may
    survive; every other field and the provider's raw output are omitted before
    persistence. The structured V1 contract will replace this temporary gate with
    literal source-span validation and protected raw-output storage.
    """

    safe_fields = [
        field
        for field in extraction.fields
        if allow_legacy_fields
        and is_temporarily_permitted_legacy_field_type(field.field_type)
        and not is_condition_shaped_field(field)
    ]
    omitted_count = len(extraction.fields) - len(safe_fields)
    document_type = extraction.document_type.strip().casefold()
    safe_document_type = (
        document_type if document_type in TEMPORARILY_PERMITTED_DOCUMENT_TYPES else "unknown"
    )
    raw_output = {
        "document_type": safe_document_type,
        "provider_field_count": len(extraction.fields),
        "field_count": len(safe_fields),
        "condition_safety": {
            "policy": CONDITION_SAFETY_POLICY,
            "condition_output_enabled": False,
            "legacy_field_output_enabled": allow_legacy_fields,
            "provider_output_persisted": False,
            "omitted_field_count": omitted_count,
        },
    }

    return DocumentExtraction(
        document_type=safe_document_type,
        raw_output=raw_output,
        fields=safe_fields,
    )
