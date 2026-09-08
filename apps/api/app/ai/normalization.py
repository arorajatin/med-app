"""Validate the four extraction classes against independently parsed source evidence."""

import math
import re
from dataclasses import replace
from datetime import date
from decimal import Decimal, InvalidOperation

from app.ai.base import (
    DocumentExtraction,
    DocumentMetadataDatum,
    MemoryCandidateDatum,
    MetricObservationDatum,
    PatientEvidenceDatum,
    SourceLayout,
    SourcePage,
)
from app.ai.source_layout import (
    ExtractionValidationError,
    reference_contains_span,
    resolve_reference,
)
from app.services.patient_matching import normalize_patient_name

_METADATA_KEYS = {
    "document_type": "text",
    "record_date": "date",
    "issuer_name": "text",
    "display_filename": "text",
}
_PRESCRIPTION_KEYS = {
    "medication_name",
    "strength",
    "dosage_form",
    "dose",
    "route",
    "frequency",
    "duration",
    "instructions",
}
_NON_PATIENT_ASSERTION = re.compile(
    r"\b(?:no|not|never|without|denies|denied|negative|rule[ds]? out|screen\w*|suspect\w*|"
    r"possible|possibly|probable|uncertain|maybe|may|might|risk|family|mother|father|sister|"
    r"brother|parent|relative|wife|husband|son|daughter|if|exclude\w*|unlikely|"
    r"example|hypothetical|another|other|someone else|template)\b|\?",
    re.IGNORECASE,
)


def _literal(value: object, source: str) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float, Decimal)):
        try:
            expected = Decimal(str(value))
            return expected.is_finite() and any(
                Decimal(number) == expected
                for number in re.findall(r"(?<![\w.])[+-]?\d+(?:\.\d+)?(?![\w.])", source)
            )
        except InvalidOperation:
            return False
    if not isinstance(value, str) or not value.strip():
        return False
    normalized = " ".join(source.casefold().split())
    return (
        re.search(
            r"(?<!\w)" + re.escape(" ".join(value.casefold().split())) + r"(?!\w)", normalized
        )
        is not None
    )


def _date_literal(value: date, source: str) -> bool:
    return any(
        _literal(rendered, source) for rendered in (value.isoformat(), value.strftime("%Y/%m/%d"))
    )


def _affirmative_condition(candidate: MemoryCandidateDatum, pages: list[SourcePage]) -> bool:
    condition = candidate.exact_condition_text
    if not condition or candidate.value != {"text": condition}:
        return False
    for reference, page in zip(candidate.source_references, pages, strict=True):
        if not _literal(condition, reference.text_span):
            continue
        # Use source context, not a provider-supplied assertion flag or a cropped span.
        # This deliberately omits ambiguous contexts; the local contract has no recall floor.
        if _NON_PATIENT_ASSERTION.search(page.text):
            continue
        assertion = re.compile(
            r"(?:^|\n)\s*(?:(?:the\s+)?patient\s+(?:has|is diagnosed with|was diagnosed with)\s+|"
            r"diagnos(?:is|es)\s*:\s*)(?P<condition>"
            + re.escape(condition)
            + r")(?=\s*[.;\n]|\s*$)",
            re.IGNORECASE,
        )
        if any(
            reference_contains_span(reference, page, *match.span("condition"))
            for match in assertion.finditer(page.text)
        ):
            return True
    return False


def validate_extraction(
    extraction: DocumentExtraction,
    layout: SourceLayout,
    *,
    allow_documented_conditions: bool = False,
) -> DocumentExtraction:
    """A bad reference rejects the whole attempt; unsupported literal values are omitted.

    Condition validation is testable here but production admission remains disabled until
    protected raw storage, review, and rollout evidence land. This is not a provider allowlist.
    """

    schema_error = ExtractionValidationError("invalid_extraction_schema")
    if (
        extraction.processing_method not in {"native_text", "textract_ocr"}
        or not extraction.routing_reason
    ):
        raise schema_error
    items: list[
        PatientEvidenceDatum | DocumentMetadataDatum | MetricObservationDatum | MemoryCandidateDatum
    ] = [
        *extraction.patient_evidence,
        *extraction.metadata_candidates,
        *extraction.observations,
        *extraction.memory_candidates,
    ]
    if items and extraction.processing_method != layout.processing_method:
        raise ExtractionValidationError("invalid_source_reference")
    resolved: dict[int, list[SourcePage]] = {}
    for item in items:
        if not math.isfinite(item.confidence) or not 0 <= item.confidence <= 1:
            raise schema_error
        if not item.source_references:
            raise ExtractionValidationError("invalid_source_reference")
        resolved[id(item)] = [
            resolve_reference(reference, layout) for reference in item.source_references
        ]

    patients = []
    for patient in extraction.patient_evidence:
        source = "\n".join(reference.text_span for reference in patient.source_references)
        if not _literal(patient.extracted_name, source):
            continue
        patient_label = re.compile(
            r"(?:^|\n)\s*patient(?: name)?\s*:\s*(?P<name>"
            + re.escape(patient.extracted_name)
            + r")(?=\s*(?:\n|$)|\s+(?:age|sex|gender|dob|date of birth|patient id)\s*:)",
            re.IGNORECASE,
        )
        if not any(
            reference_contains_span(reference, page, *match.span("name"))
            for reference, page in zip(
                patient.source_references, resolved[id(patient)], strict=True
            )
            for match in patient_label.finditer(page.text)
        ):
            continue
        patients.append(
            replace(
                patient,
                normalized_name=normalize_patient_name(patient.extracted_name),
                date_of_birth=patient.date_of_birth
                if patient.date_of_birth and _date_literal(patient.date_of_birth, source)
                else None,
                patient_identifier=patient.patient_identifier
                if _literal(patient.patient_identifier, source)
                else None,
            )
        )

    metadata = []
    for candidate in extraction.metadata_candidates:
        key = _METADATA_KEYS.get(candidate.metadata_type)
        if key is None or set(candidate.value) != {key}:
            raise schema_error
        source = "\n".join(reference.text_span for reference in candidate.source_references)
        value = candidate.value[key]
        if candidate.metadata_type == "document_type":
            labels = {
                "lab_report": ("lab report", "cbc", "creatinine", "hemoglobin"),
                "prescription": ("prescription", "tablet", "capsule"),
            }
            supported = any(_literal(label, source) for label in labels.get(value, ()))
        else:
            supported = _literal(value, source)
        if supported:
            metadata.append(candidate)

    observations = []
    for observation in extraction.observations:
        if set(observation.original_value) != {"value"} or not observation.metric_identity.strip():
            raise schema_error
        source = "\n".join(reference.text_span for reference in observation.source_references)
        # A label and a number on different rows do not establish a lab tuple.
        value_lines = [
            line
            for line in source.splitlines()
            if _literal(observation.label, line)
            and _literal(observation.original_value["value"], line)
            and (observation.original_unit is None or _literal(observation.original_unit, line))
        ]
        if not value_lines:
            continue
        if observation.original_unit is not None and not _literal(
            observation.original_unit, source
        ):
            continue
        if observation.normalized_value not in (
            None,
            observation.original_value,
        ) or observation.normalized_unit not in (None, observation.original_unit):
            raise schema_error
        if observation.reference_range and not all(
            _literal(value, source) for value in observation.reference_range.values()
        ):
            continue
        if observation.flag is not None and not _literal(observation.flag, source):
            continue
        if observation.observed_on and not _date_literal(observation.observed_on, source):
            continue
        observations.append(observation)

    memory = []
    for memory_item in extraction.memory_candidates:
        source = "\n".join(reference.text_span for reference in memory_item.source_references)
        if memory_item.subtype == "documented_condition_candidate":
            if allow_documented_conditions and _affirmative_condition(
                memory_item, resolved[id(memory_item)]
            ):
                memory.append(memory_item)
            continue
        if (
            memory_item.subtype not in {"prescription_medication", "prescription_instruction"}
            or memory_item.exact_condition_text is not None
        ):
            raise schema_error
        required = (
            "medication_name"
            if memory_item.subtype == "prescription_medication"
            else "instructions"
        )
        if required not in memory_item.value or set(memory_item.value) - _PRESCRIPTION_KEYS:
            raise schema_error
        if all(_literal(value, source) for value in memory_item.value.values()):
            memory.append(memory_item)
    return replace(
        extraction,
        patient_evidence=patients,
        metadata_candidates=metadata,
        observations=observations,
        memory_candidates=memory,
    )
