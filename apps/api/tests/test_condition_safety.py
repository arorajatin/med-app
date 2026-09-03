import pytest

from app.ai.base import (
    DocumentExtraction,
    DocumentMetadataDatum,
    MemoryCandidateDatum,
    MetricObservationDatum,
    SourceReferenceData,
)
from app.ai.condition_safety import (
    enforce_condition_safety,
    is_condition_shaped_candidate,
    is_condition_shaped_name,
)
from app.ai.mock_provider import MockExtractor


def extract(text: str, *, filename: str = "record.pdf") -> DocumentExtraction:
    return MockExtractor().extract_document(
        file_bytes=text.encode(),
        filename=filename,
        mime_type="application/pdf",
    )


def reference(*, text_span: str = "mock span") -> SourceReferenceData:
    return SourceReferenceData(
        part_ordinal=0,
        logical_page=1,
        text_span=text_span,
        bounding_polygon=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
    )


@pytest.mark.parametrize(
    ("text", "filename"),
    [
        ("Lab report\ncreatinine 1.2 mg/dL\nkidney follow up", "lab.pdf"),
        ("Lab report\nSGPT 45\nliver", "lab.pdf"),
        ("Prescription\nTablet metformin 500 mg", "prescription.pdf"),
        ("Prescription\nSymptoms: cough and wheezing", "prescription.pdf"),
        ("Lab report\nhemoglobin 13.2 g/dL", "diabetes-kidney-lab.pdf"),
        ("Prescription\nDiagnosis: seasonal allergic rhinitis", "prescription.pdf"),
    ],
)
def test_mock_extractor_does_not_create_condition_output(text, filename):
    result = extract(text, filename=filename)

    assert not any(
        is_condition_shaped_candidate(candidate) for candidate in result.memory_candidates
    )
    assert not any(
        is_condition_shaped_name(candidate.metadata_type)
        for candidate in result.metadata_candidates
    )
    assert all(candidate.exact_condition_text is None for candidate in result.memory_candidates)


def test_condition_safety_gate_omits_all_unvalidated_condition_shapes():
    memory_candidates = [
        MemoryCandidateDatum(
            subtype=subtype,
            label=f"Unvalidated {subtype}",
            value={"text": "Fabricated condition"},
            confidence=0.9,
            source_references=[reference()],
        )
        for subtype in (
            "condition",
            "diagnosis_candidate",
            "clinical_impression",
            "reported_problem",
        )
    ]
    # A literally documented condition still waits for the structured source contract.
    memory_candidates.append(
        MemoryCandidateDatum(
            subtype="documented_condition_candidate",
            label="Documented condition",
            value={"text": "Type 2 diabetes mellitus"},
            confidence=0.95,
            exact_condition_text="Type 2 diabetes mellitus",
            source_references=[reference(text_span="Type 2 diabetes mellitus")],
        )
    )
    memory_candidates.append(
        MemoryCandidateDatum(
            subtype="prescription_medication",
            label="Metformin 500 mg",
            value={"medication_name": "Metformin 500 mg"},
            confidence=0.8,
            source_references=[reference(text_span="Tablet Metformin 500 mg")],
        )
    )

    filtered = enforce_condition_safety(
        DocumentExtraction(
            document_type="lab_report",
            raw_output={"condition": "Inferred kidney disease", "item_count": 999},
            processing_method="native_text",
            routing_reason="deterministic_mock_text",
            memory_candidates=memory_candidates,
        ),
        allow_baseline_items=True,
    )

    assert [candidate.subtype for candidate in filtered.memory_candidates] == [
        "prescription_medication"
    ]
    assert filtered.raw_output["condition_safety"] == {
        "policy": "literal_source_validation_required",
        "condition_output_enabled": False,
        "baseline_item_output_enabled": True,
        "provider_output_persisted": False,
        "omitted_item_count": 5,
    }
    assert filtered.raw_output["provider_item_count"] == 6
    assert filtered.raw_output["item_count"] == 1
    assert "condition" not in filtered.raw_output


def test_condition_safety_gate_omits_every_item_from_an_unapproved_extractor():
    extraction = DocumentExtraction(
        document_type="lab_report",
        raw_output={"item_count": 3},
        processing_method="native_text",
        routing_reason="unapproved_extractor",
        metadata_candidates=[
            DocumentMetadataDatum(
                metadata_type="record_date",
                value={"date": "2026-06-01"},
                confidence=0.9,
                source_references=[reference()],
            )
        ],
        observations=[
            MetricObservationDatum(
                metric_identity="creatinine",
                label="Creatinine",
                original_value={"value": 1.2},
                confidence=0.9,
                source_references=[reference()],
            )
        ],
        memory_candidates=[
            MemoryCandidateDatum(
                subtype="prescription_medication",
                label="Metformin 500 mg",
                value={"medication_name": "Metformin 500 mg"},
                confidence=0.8,
                source_references=[reference()],
            )
        ],
    )

    filtered = enforce_condition_safety(extraction, allow_baseline_items=False)

    assert filtered.metadata_candidates == []
    assert filtered.observations == []
    assert filtered.memory_candidates == []
    assert filtered.raw_output["provider_item_count"] == 3
    assert filtered.raw_output["item_count"] == 0
    assert filtered.raw_output["condition_safety"]["baseline_item_output_enabled"] is False


def test_condition_safety_gate_omits_unsupported_metadata_and_unanchored_items():
    extraction = DocumentExtraction(
        document_type="prescription",
        raw_output={},
        processing_method="native_text",
        routing_reason="deterministic_mock_text",
        metadata_candidates=[
            DocumentMetadataDatum(
                metadata_type="issuer",
                value={"text": "Unsupported issuer"},
                confidence=0.9,
                source_references=[reference()],
            ),
            DocumentMetadataDatum(
                metadata_type="document_type",
                value={"text": "prescription"},
                confidence=0.9,
                source_references=[],
            ),
        ],
        memory_candidates=[
            MemoryCandidateDatum(
                subtype="prescription_instruction",
                label="Follow-up mentioned",
                value={"instructions": "follow up"},
                confidence=0.6,
                source_references=[
                    SourceReferenceData(
                        part_ordinal=0,
                        logical_page=0,
                        text_span="",
                        bounding_polygon=[],
                    )
                ],
            )
        ],
    )

    filtered = enforce_condition_safety(extraction, allow_baseline_items=True)

    assert filtered.metadata_candidates == []
    assert filtered.memory_candidates == []
    assert filtered.raw_output["condition_safety"]["omitted_item_count"] == 3


@pytest.mark.parametrize(
    "name",
    [
        "condition",
        "documented_condition_candidate",
        "diagnosis_candidate",
        "clinical_impression",
        "chronic-disease",
        "reported problem",
    ],
)
def test_condition_shaped_names_are_detected(name):
    assert is_condition_shaped_name(name) is True


@pytest.mark.parametrize(
    "name", ["record_date", "document_type", "test_result", "prescription_medication"]
)
def test_permitted_names_are_not_condition_shaped(name):
    assert is_condition_shaped_name(name) is False
