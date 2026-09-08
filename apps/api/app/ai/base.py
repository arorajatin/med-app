from dataclasses import dataclass, field
from datetime import date
from typing import Literal


@dataclass(frozen=True)
class SourceReferenceData:
    part_ordinal: int
    logical_page: int
    text_span: str
    bounding_polygon: list[list[float]]
    native_word_ids: list[str] | None = None
    textract_block_ids: list[str] | None = None
    part_id: str | None = None


@dataclass(frozen=True)
class SourceWord:
    id: str
    start: int
    end: int
    polygon: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class SourcePage:
    part_id: str
    part_ordinal: int
    logical_page: int
    text: str
    words: tuple[SourceWord, ...]


@dataclass(frozen=True)
class SourceLayout:
    """Evidence produced by source parsing/OCR, separately from model output."""

    processing_method: Literal["native_text", "textract_ocr"]
    pages: tuple[SourcePage, ...]


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


@dataclass(frozen=True)
class DocumentPart:
    ordinal: int
    file_bytes: bytes
    filename: str
    mime_type: str
    part_id: str = ""


class Extractor:
    provider_name = "base"

    def extract_with_layout(
        self, *, parts: tuple[DocumentPart, ...], layout: SourceLayout
    ) -> DocumentExtraction:
        return self.extract_logical_document(parts=parts)

    def extract_logical_document(self, *, parts: tuple[DocumentPart, ...]) -> DocumentExtraction:
        if len(parts) != 1:
            raise ValueError("This extractor does not support ordered multi-image documents.")
        part = parts[0]
        return self.extract_document(
            file_bytes=part.file_bytes, filename=part.filename, mime_type=part.mime_type
        )

    def extract_document(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
    ) -> DocumentExtraction:
        raise NotImplementedError
