from dataclasses import replace
from datetime import date

import pytest
from document_fixtures import pdf_bytes

from app.ai.base import (
    DocumentExtraction,
    DocumentMetadataDatum,
    DocumentPart,
    MemoryCandidateDatum,
    MetricObservationDatum,
    PatientEvidenceDatum,
)
from app.ai.mock_provider import MockExtractor
from app.ai.normalization import validate_extraction
from app.ai.source_layout import ExtractionValidationError, native_layout, reference_for_span


def layout_for(text: str, *, pages: int = 1):
    return native_layout(
        (
            DocumentPart(
                0,
                pdf_bytes(text.encode(), pages=pages),
                "report.pdf",
                "application/pdf",
                "source-part",
            ),
        )
    )


def result_for(layout):
    return DocumentExtraction("lab_report", {}, layout.processing_method, "local_contract")


def test_lab_values_cannot_be_borrowed_from_another_row():
    layout = layout_for("Lab report\nCreatinine pending\nHemoglobin 13.2 g/dL")
    page = layout.pages[0]
    extraction = replace(
        result_for(layout),
        observations=[
            MetricObservationDatum(
                "creatinine",
                "Creatinine",
                {"value": 13.2},
                0.9,
                [reference_for_span(page, "Creatinine pending\nHemoglobin 13.2 g/dL")],
            )
        ],
    )
    assert validate_extraction(extraction, layout).observations == []
    mock_result = MockExtractor().extract_with_layout(parts=(), layout=layout)
    assert [item.metric_identity for item in mock_result.observations] == ["hemoglobin"]


def test_four_classes_require_literal_values_and_real_source_geometry():
    layout = layout_for(
        "Lab report\nPatient: Asha Rao\nDate of birth: 1980-05-04\n"
        "Report date: 2026-09-01\nHemoglobin 13.2 g/dL\nTablet Metformin 500 mg\nPatient has asthma."
    )
    page = layout.pages[0]

    def ref(span):
        return reference_for_span(page, span)

    extraction = replace(
        result_for(layout),
        patient_evidence=[
            PatientEvidenceDatum(
                "Asha Rao",
                "MODEL-SUPPLIED WRONG NAME",
                0.9,
                [ref("Patient: Asha Rao\nDate of birth: 1980-05-04")],
                date_of_birth=date(1980, 5, 4),
            )
        ],
        metadata_candidates=[
            DocumentMetadataDatum("record_date", {"date": "2026-09-01"}, 0.9, [ref("2026-09-01")])
        ],
        observations=[
            MetricObservationDatum(
                "hemoglobin",
                "Hemoglobin",
                {"value": 13.2},
                0.9,
                [ref("Hemoglobin 13.2 g/dL")],
                original_unit="g/dL",
            )
        ],
        memory_candidates=[
            MemoryCandidateDatum(
                "prescription_medication",
                "Metformin",
                {"medication_name": "Metformin", "strength": "500 mg"},
                0.9,
                [ref("Tablet Metformin 500 mg")],
            ),
            MemoryCandidateDatum(
                "documented_condition_candidate",
                "asthma",
                {"text": "asthma"},
                0.9,
                [ref("asthma")],
                exact_condition_text="asthma",
            ),
        ],
    )
    safe = validate_extraction(extraction, layout, allow_documented_conditions=True)
    assert safe.patient_evidence[0].normalized_name == "asha rao"
    assert safe.patient_evidence[0].date_of_birth == date(1980, 5, 4)
    assert len(safe.metadata_candidates) == len(safe.observations) == 1
    assert len(safe.memory_candidates) == 2
    assert len(validate_extraction(extraction, layout).memory_candidates) == 1
    reference = safe.observations[0].source_references[0]
    assert reference.part_id == "source-part"
    assert reference.native_word_ids
    assert all(0 < coordinate < 1 for point in reference.bounding_polygon for coordinate in point)


@pytest.mark.parametrize(
    "mutation",
    [
        {"part_id": "foreign-part"},
        {"part_ordinal": 1},
        {"logical_page": 0},
        {"logical_page": 2},
        {"native_word_ids": []},
        {"native_word_ids": ["fabricated"]},
        {"textract_block_ids": ["mixed-method"]},
        {"text_span": "Hemoglobin 99"},
        {"bounding_polygon": [[0, 0], [1, 0], [1, 1], [0, 1]]},
        {"bounding_polygon": [[float("nan"), 0]] * 4},
    ],
)
def test_any_invalid_reference_rejects_the_complete_result(mutation):
    layout = layout_for("Lab report\nHemoglobin 13.2 g/dL")
    reference = replace(reference_for_span(layout.pages[0], "Hemoglobin 13.2 g/dL"), **mutation)
    extraction = replace(
        result_for(layout),
        observations=[
            MetricObservationDatum("hemoglobin", "Hemoglobin", {"value": 13.2}, 0.9, [reference])
        ],
        metadata_candidates=[
            DocumentMetadataDatum(
                "document_type",
                {"text": "lab_report"},
                0.9,
                [reference_for_span(layout.pages[0], "Lab report")],
            )
        ],
    )
    with pytest.raises(ExtractionValidationError, match="invalid_source_reference"):
        validate_extraction(extraction, layout)


@pytest.mark.parametrize("kind", ["missing", "duplicate", "reordered", "too_wide"])
def test_references_cannot_omit_or_reorder_source_words(kind):
    layout = layout_for("Lab report\nHemoglobin 13.2 g/dL")
    reference = reference_for_span(layout.pages[0], "Hemoglobin 13.2 g/dL")
    ids = reference.native_word_ids
    if kind == "duplicate":
        reference = replace(reference, native_word_ids=[ids[0], ids[0]])
    elif kind == "reordered":
        reference = replace(reference, native_word_ids=list(reversed(ids)))
    elif kind == "too_wide":
        reference = replace(reference, text_span="13.2")
    extraction = replace(
        result_for(layout),
        observations=[
            MetricObservationDatum(
                "hemoglobin",
                "Hemoglobin",
                {"value": 13.2},
                0.9,
                [] if kind == "missing" else [reference],
            )
        ],
    )
    with pytest.raises(ExtractionValidationError, match="invalid_source_reference"):
        validate_extraction(extraction, layout)


@pytest.mark.parametrize(
    "source",
    [
        "Patient has no asthma.",
        "Patient does not have asthma.",
        "Asthma ruled out.",
        "Screening for asthma.",
        "Possible asthma.",
        "Patient may have asthma.",
        "Family history: asthma.",
        "Mother has asthma.",
        "Diagnosis: asthma in father.",
        "Family history:\nDiagnosis: asthma.",
        "Patient has asthma?",
        "Patient denies asthma.",
        "Tablet salbutamol for asthma screening.",
        "Asthma is a possible cause of wheezing.",
        "Example: Patient has asthma.",
        "Another patient has asthma.",
        "If patient has asthma.",
        "No evidence of asthma.\nDiagnosis: asthma.",
    ],
)
def test_cropped_condition_mentions_cannot_escape_assertion_validation(source):
    layout = layout_for("Prescription\n" + source)
    span = "asthma" if "asthma" in layout.pages[0].text else "Asthma"
    candidate = MemoryCandidateDatum(
        "documented_condition_candidate",
        span,
        {"text": span},
        0.99,
        [reference_for_span(layout.pages[0], span)],
        exact_condition_text=span,
    )
    result = validate_extraction(
        replace(result_for(layout), memory_candidates=[candidate]),
        layout,
        allow_documented_conditions=True,
    )
    assert result.memory_candidates == []


@pytest.mark.parametrize(
    "source,span",
    [
        ("Prescription\nTablet Metformin 500 mg", "Metformin"),
        ("Lab report\nGlucose 180 mg/dL", "Glucose 180 mg/dL"),
        ("Prescription\nSymptoms: wheezing", "wheezing"),
    ],
)
def test_medications_measurements_and_symptoms_cannot_support_a_condition(source, span):
    layout = layout_for(source)
    candidate = MemoryCandidateDatum(
        "documented_condition_candidate",
        "diabetes",
        {"text": "diabetes"},
        0.99,
        [reference_for_span(layout.pages[0], span)],
        exact_condition_text="diabetes",
    )
    assert (
        validate_extraction(
            replace(result_for(layout), memory_candidates=[candidate]),
            layout,
            allow_documented_conditions=True,
        ).memory_candidates
        == []
    )


def test_uncited_values_and_non_patient_names_are_omitted():
    layout = layout_for("Lab report\nDoctor: Asha Rao\nPatient: Ravi Rao\nHemoglobin 13.2 g/dL")
    ref = reference_for_span(layout.pages[0], "Hemoglobin 13.2 g/dL")
    extraction = replace(
        result_for(layout),
        patient_evidence=[
            PatientEvidenceDatum(
                "Asha Rao", "ravi rao", 0.99, [reference_for_span(layout.pages[0], "Asha Rao")]
            )
        ],
        observations=[
            MetricObservationDatum("hemoglobin", "Hemoglobin", {"value": 99}, 0.9, [ref])
        ],
    )
    result = validate_extraction(extraction, layout)
    assert result.patient_evidence == result.observations == []


def test_patient_reference_must_cite_the_patient_occurrence_of_a_repeated_name():
    layout = layout_for("Lab report\nDoctor: Asha Rao\nPatient: Asha Rao")
    extraction = replace(
        result_for(layout),
        patient_evidence=[
            PatientEvidenceDatum(
                "Asha Rao",
                "asha rao",
                0.99,
                [reference_for_span(layout.pages[0], "Doctor: Asha Rao")],
            )
        ],
    )
    assert validate_extraction(extraction, layout).patient_evidence == []
    mock_result = MockExtractor().extract_with_layout(parts=(), layout=layout)
    safe = validate_extraction(mock_result, layout)
    assert len(safe.patient_evidence) == 1
    assert safe.patient_evidence[0].source_references[0].text_span == "Patient: Asha Rao"


def test_condition_reference_must_cite_the_affirmative_occurrence():
    layout = layout_for("Prescription\nDiagnosis: asthma.\nEducational material: asthma")
    candidate = MemoryCandidateDatum(
        "documented_condition_candidate",
        "asthma",
        {"text": "asthma"},
        0.99,
        [reference_for_span(layout.pages[0], "Educational material: asthma")],
        exact_condition_text="asthma",
    )
    assert (
        validate_extraction(
            replace(result_for(layout), memory_candidates=[candidate]),
            layout,
            allow_documented_conditions=True,
        ).memory_candidates
        == []
    )


def test_multi_page_and_ocr_contract_preserve_source_identity():
    layout = layout_for("Lab report\nHemoglobin 13.2 g/dL", pages=2)
    reference = reference_for_span(layout.pages[1], "Hemoglobin 13.2 g/dL")
    assert reference.logical_page == 2
    assert reference.native_word_ids[0].startswith("native:2:")
    ocr = replace(layout, processing_method="textract_ocr")
    reference = replace(
        reference, textract_block_ids=reference.native_word_ids, native_word_ids=None
    )
    extraction = replace(
        result_for(ocr),
        observations=[
            MetricObservationDatum("hemoglobin", "Hemoglobin", {"value": 13.2}, 0.9, [reference])
        ],
    )
    assert len(validate_extraction(extraction, ocr).observations) == 1
    with pytest.raises(ExtractionValidationError, match="invalid_source_reference"):
        validate_extraction(extraction, layout)


@pytest.mark.parametrize("confidence", [float("nan"), float("inf"), -0.01, 1.01])
def test_invalid_confidence_is_a_schema_failure(confidence):
    layout = layout_for("Lab report")
    candidate = DocumentMetadataDatum(
        "document_type",
        {"text": "lab_report"},
        confidence,
        [reference_for_span(layout.pages[0], "Lab report")],
    )
    with pytest.raises(ExtractionValidationError, match="invalid_extraction_schema"):
        validate_extraction(replace(result_for(layout), metadata_candidates=[candidate]), layout)
