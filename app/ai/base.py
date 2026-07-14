from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExtractedDatum:
    field_type: str
    label: str
    value: dict
    confidence: float
    source_reference: str | None = None
    normalized_value: dict | None = None


@dataclass(frozen=True)
class DocumentExtraction:
    document_type: str
    raw_output: dict
    fields: list[ExtractedDatum] = field(default_factory=list)


class Extractor:
    provider_name = "base"

    def extract_document(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        profile_context: dict | None = None,
    ) -> DocumentExtraction:
        raise NotImplementedError

