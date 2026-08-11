import pytest

from app.ai.base import DocumentExtraction, ExtractedDatum
from app.ai.condition_safety import enforce_condition_safety, is_condition_shaped_field
from app.ai.mock_provider import MockExtractor


def extract(text: str, *, filename: str = "record.txt") -> DocumentExtraction:
    return MockExtractor().extract_document(
        file_bytes=text.encode(),
        filename=filename,
        mime_type="text/plain",
    )


@pytest.mark.parametrize(
    ("text", "filename"),
    [
        ("Lab report\ncreatinine 1.2 mg/dL\nkidney follow up", "lab.txt"),
        ("Lab report\nSGPT 45\nliver", "lab.txt"),
        ("Prescription\nTablet metformin 500 mg", "prescription.txt"),
        ("Prescription\nSymptoms: cough and wheezing", "prescription.txt"),
        ("Lab report\nhemoglobin 13.2 g/dL", "diabetes-kidney-lab.txt"),
        ("Prescription\nDiagnosis: seasonal allergic rhinitis", "prescription.txt"),
    ],
)
def test_mock_extractor_does_not_create_condition_output(text, filename):
    result = extract(text, filename=filename)

    assert not any(is_condition_shaped_field(field) for field in result.fields)


def test_condition_safety_gate_omits_all_unvalidated_condition_shapes():
    fields = [
        ExtractedDatum(
            field_type="condition",
            label="Legacy condition",
            value={"text": "Fabricated condition"},
            confidence=0.9,
            source_reference="mock:keyword",
        ),
        ExtractedDatum(
            field_type="documented_condition_candidate",
            label="Unvalidated documented condition",
            value={"text": "Unverified condition"},
            confidence=0.9,
            source_reference="mock:opaque",
        ),
        ExtractedDatum(
            field_type="diagnosis_candidate",
            label="Unvalidated diagnosis",
            value={"text": "Unverified diagnosis"},
            confidence=0.9,
            source_reference="mock:opaque",
        ),
        ExtractedDatum(
            field_type="clinical_impression",
            label="Unvalidated clinical impression",
            value={"text": "Unverified clinical impression"},
            confidence=0.9,
            source_reference="mock:opaque",
        ),
        ExtractedDatum(
            field_type="test_result",
            label="Creatinine",
            value={"name": "Creatinine", "value": 1.2, "unit": "mg/dL"},
            confidence=0.9,
            source_reference="mock:creatinine_pattern",
        ),
    ]

    filtered = enforce_condition_safety(
        DocumentExtraction(
            document_type="lab_report",
            raw_output={"condition": "Inferred kidney disease", "field_count": 999},
            fields=fields,
        ),
        allow_legacy_fields=True,
    )

    assert [field.field_type for field in filtered.fields] == ["test_result"]
    assert filtered.raw_output["condition_safety"] == {
        "policy": "literal_source_validation_required",
        "condition_output_enabled": False,
        "legacy_field_output_enabled": True,
        "provider_output_persisted": False,
        "omitted_field_count": 4,
    }
    assert filtered.raw_output["provider_field_count"] == 5
    assert filtered.raw_output["field_count"] == 1
    assert "condition" not in filtered.raw_output
