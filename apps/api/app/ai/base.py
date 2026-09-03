from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class SourceReferenceData:
    part_ordinal: int
    logical_page: int
    text_span: str
    bounding_polygon: list[list[float]]
    native_word_ids: list[str] | None = None
    textract_block_ids: list[str] | None = None


@dataclass(frozen=True)
class PatientEvidenceDatum:
    extracted_name: str
    normalized_name: str
    confidence: float
    source_references: list[SourceReferenceData]
    date_of_birth: date | None = None
    patient_identifier: str | None = None


@dataclass(frozen=True)
class DocumentMetadataDatum:
    metadata_type: str
    value: dict
    confidence: float
    source_references: list[SourceReferenceData]


@dataclass(frozen=True)
class MetricObservationDatum:
    metric_identity: str
    label: str
    original_value: dict
    confidence: float
    source_references: list[SourceReferenceData]
    original_unit: str | None = None
    normalized_value: dict | None = None
    normalized_unit: str | None = None
    reference_range: dict | None = None
    flag: str | None = None
    observed_on: date | None = None
    body_system: str | None = None


@dataclass(frozen=True)
class MemoryCandidateDatum:
    subtype: str
    label: str
    value: dict
    confidence: float
    source_references: list[SourceReferenceData]
    exact_condition_text: str | None = None


@dataclass(frozen=True)
class DocumentExtraction:
    document_type: str
    raw_output: dict
    processing_method: str
    routing_reason: str
    patient_evidence: list[PatientEvidenceDatum] = field(default_factory=list)
    metadata_candidates: list[DocumentMetadataDatum] = field(default_factory=list)
    observations: list[MetricObservationDatum] = field(default_factory=list)
    memory_candidates: list[MemoryCandidateDatum] = field(default_factory=list)


class Extractor:
    provider_name = "base"

    def extract_document(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
    ) -> DocumentExtraction:
        raise NotImplementedError
