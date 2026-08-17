from __future__ import annotations

import re
from collections.abc import Iterable

from app.ai.base import DocumentExtraction, MemoryCandidateDatum, SourceReferenceData

CONDITION_FIELD_TOKENS = frozenset({"condition", "diagnosis", "disease", "impression", "problem"})
CONDITION_SAFETY_POLICY = "literal_source_validation_required"
BASELINE_DOCUMENT_TYPES = frozenset({"medical_record", "lab_report", "prescription"})
BASELINE_METADATA_TYPES = frozenset({"document_type", "record_date"})
BASELINE_MEMORY_SUBTYPES = frozenset(
    {"prescription_medication", "prescription_instruction"}
)
BASELINE_MEMORY_CATEGORIES = frozenset({"medication", "test_result", "follow_up"})


def is_condition_shaped_name(value: str) -> bool:
    tokens = {token for token in re.split(r"[^a-z0-9]+", value.strip().casefold()) if token}
    return bool(tokens & CONDITION_FIELD_TOKENS)


def is_condition_shaped_candidate(candidate: MemoryCandidateDatum) -> bool:
    return candidate.exact_condition_text is not None or is_condition_shaped_name(candidate.subtype)


def is_permitted_memory_category(category: str) -> bool:
    return category.strip().casefold() in BASELINE_MEMORY_CATEGORIES


def _references_are_structured(references: Iterable[SourceReferenceData]) -> bool:
    refs = list(references)
    return bool(refs) and all(
        reference.part_ordinal >= 0
        and reference.logical_page >= 1
        and bool(reference.text_span)
        and len(reference.bounding_polygon) >= 3
        for reference in refs
    )


def enforce_condition_safety(
    extraction: DocumentExtraction,
    *,
    allow_baseline_items: bool = False,
) -> DocumentExtraction:
    """Fail closed until literal documented-condition validation is enabled."""

    metadata = [
        item
        for item in extraction.metadata_candidates
        if allow_baseline_items
        and item.metadata_type in BASELINE_METADATA_TYPES
        and _references_are_structured(item.source_references)
    ]
    observations = [
        item
        for item in extraction.observations
        if allow_baseline_items and _references_are_structured(item.source_references)
    ]
    memory_candidates = [
        item
        for item in extraction.memory_candidates
        if allow_baseline_items
        and item.subtype in BASELINE_MEMORY_SUBTYPES
        and not is_condition_shaped_candidate(item)
        and _references_are_structured(item.source_references)
    ]
    patient_evidence = [
        item
        for item in extraction.patient_evidence
        if allow_baseline_items and _references_are_structured(item.source_references)
    ]

    provider_item_count = sum(
        len(items)
        for items in (
            extraction.patient_evidence,
            extraction.metadata_candidates,
            extraction.observations,
            extraction.memory_candidates,
        )
    )
    retained_item_count = sum(
        len(items) for items in (patient_evidence, metadata, observations, memory_candidates)
    )
    document_type = extraction.document_type.strip().casefold()
    safe_document_type = document_type if document_type in BASELINE_DOCUMENT_TYPES else "unknown"
    raw_output = {
        "document_type": safe_document_type,
        "provider_item_count": provider_item_count,
        "item_count": retained_item_count,
        "condition_safety": {
            "policy": CONDITION_SAFETY_POLICY,
            "condition_output_enabled": False,
            "baseline_item_output_enabled": allow_baseline_items,
            "provider_output_persisted": False,
            "omitted_item_count": provider_item_count - retained_item_count,
        },
    }
    return DocumentExtraction(
        document_type=safe_document_type,
        raw_output=raw_output,
        processing_method=extraction.processing_method,
        routing_reason=extraction.routing_reason,
        patient_evidence=patient_evidence,
        metadata_candidates=metadata,
        observations=observations,
        memory_candidates=memory_candidates,
    )
