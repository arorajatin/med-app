from __future__ import annotations

import re
from dataclasses import replace
from datetime import date

from app.ai.base import (
    DocumentExtraction,
    DocumentMetadataDatum,
    DocumentPart,
    Extractor,
    MemoryCandidateDatum,
    MetricObservationDatum,
    PatientEvidenceDatum,
    SourceLayout,
    SourcePage,
    SourceReferenceData,
)
from app.ai.source_layout import native_layout, reference_for_span


class MockExtractor(Extractor):
    provider_name = "mock"

    def extract_logical_document(self, *, parts: tuple[DocumentPart, ...]) -> DocumentExtraction:
        return self.extract_with_layout(parts=parts, layout=native_layout(parts))

    def extract_with_layout(
        self, *, parts: tuple[DocumentPart, ...], layout: SourceLayout
    ) -> DocumentExtraction:
        metadata: list[DocumentMetadataDatum] = []
        observations: list[MetricObservationDatum] = []
        memory: list[MemoryCandidateDatum] = []
        patients: list[PatientEvidenceDatum] = []
        document_type = "medical_record"
        for page in layout.pages:
            result = self.extract_document(
                file_bytes=page.text.encode(), filename="", mime_type="application/pdf"
            )
            if result.document_type != "medical_record":
                document_type = result.document_type
            metadata.extend(_locate_items(result.metadata_candidates, page))
            observations.extend(_locate_items(result.observations, page))
            memory.extend(_locate_items(result.memory_candidates, page))
            patients.extend(_locate_items(result.patient_evidence, page))
        return DocumentExtraction(
            document_type=document_type,
            raw_output={"document_type": document_type, "part_count": len(parts)},
            processing_method="native_text",
            routing_reason="deterministic_mock_text",
            metadata_candidates=metadata,
            observations=observations,
            memory_candidates=memory,
            patient_evidence=patients,
        )

    def extract_document(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
    ) -> DocumentExtraction:
        del filename, mime_type
        text = file_bytes.decode("utf-8", errors="ignore")
        searchable = text.casefold()
        metadata: list[DocumentMetadataDatum] = []
        observations: list[MetricObservationDatum] = []
        memory_candidates: list[MemoryCandidateDatum] = []
        patients: list[PatientEvidenceDatum] = []

        for match in re.finditer(
            r"(?:^|\n)\s*patient(?: name)?\s*:\s*([^\n]+)", text, re.IGNORECASE
        ):
            name = re.split(
                r"\s+(?:age|sex|gender|dob|date of birth|patient id)\s*:",
                match.group(1),
                flags=re.IGNORECASE,
            )[0].strip()
            if name and len(name) <= 240:
                patients.append(
                    PatientEvidenceDatum(
                        extracted_name=name,
                        normalized_name="",
                        confidence=1.0,
                        source_references=[self._reference(text, match.group(0).strip())],
                    )
                )

        document_type = "medical_record"
        document_type_span: str | None = None
        if any(term in searchable for term in ("lab report", "cbc", "creatinine", "hemoglobin")):
            document_type = "lab_report"
            document_type_span = self._first_present(
                text, ("lab report", "cbc", "creatinine", "hemoglobin")
            )
        elif any(term in searchable for term in ("prescription", "tablet", "capsule")):
            document_type = "prescription"
            document_type_span = self._first_present(text, ("prescription", "tablet", "capsule"))

        if document_type_span is not None:
            metadata.append(
                DocumentMetadataDatum(
                    metadata_type="document_type",
                    value={"text": document_type},
                    confidence=0.72,
                    source_references=[self._reference(text, document_type_span)],
                )
            )

        record_date = self._extract_date(text)
        if record_date is not None:
            parsed_date, source_span = record_date
            metadata.append(
                DocumentMetadataDatum(
                    metadata_type="record_date",
                    value={"date": parsed_date.isoformat()},
                    confidence=0.76,
                    source_references=[self._reference(text, source_span)],
                )
            )

        for label, metric_identity, unit in (
            ("creatinine", "creatinine", "mg/dL"),
            ("hemoglobin", "hemoglobin", "g/dL"),
        ):
            measurement = self._extract_number_after(text, label)
            if measurement is None:
                continue
            value, source_span = measurement
            # A conventional unit is not evidence that this particular report used it.
            unit_match = re.search(
                re.escape(source_span) + r"\s*(" + re.escape(unit) + r")\b", text, re.IGNORECASE
            )
            source_unit = unit_match.group(1) if unit_match else None
            if unit_match:
                source_span = unit_match.group(0)
            observations.append(
                MetricObservationDatum(
                    metric_identity=metric_identity,
                    label=label.title(),
                    original_value={"value": value},
                    original_unit=source_unit,
                    normalized_value={"value": value},
                    normalized_unit=source_unit,
                    confidence=0.7,
                    source_references=[self._reference(text, source_span)],
                )
            )

        medication_match = re.search(
            r"\b(?:tablet|capsule|tab\.?|cap\.?)\s+([a-zA-Z0-9 -]{2,40})", text, re.IGNORECASE
        )
        if medication_match:
            medication = medication_match.group(1).strip()
            memory_candidates.append(
                MemoryCandidateDatum(
                    subtype="prescription_medication",
                    label=medication,
                    value={"medication_name": medication},
                    confidence=0.58,
                    source_references=[self._reference(text, medication_match.group(0))],
                )
            )

        follow_up_match = re.search(r"\bfollow[ -]?up\b", text, re.IGNORECASE)
        if follow_up_match:
            memory_candidates.append(
                MemoryCandidateDatum(
                    subtype="prescription_instruction",
                    label="Follow-up mentioned",
                    value={"instructions": follow_up_match.group(0)},
                    confidence=0.6,
                    source_references=[self._reference(text, follow_up_match.group(0))],
                )
            )

        item_count = len(metadata) + len(observations) + len(memory_candidates)
        return DocumentExtraction(
            document_type=document_type,
            raw_output={"document_type": document_type, "item_count": item_count},
            processing_method="native_text",
            routing_reason="deterministic_mock_text",
            metadata_candidates=metadata,
            observations=observations,
            memory_candidates=memory_candidates,
            patient_evidence=patients,
        )

    @staticmethod
    def _reference(text: str, span: str) -> SourceReferenceData:
        start = text.casefold().find(span.casefold())
        end = start + len(span)
        return SourceReferenceData(
            part_ordinal=0,
            logical_page=1,
            native_word_ids=[f"mock:{start}:{end}"],
            text_span=text[start:end],
            bounding_polygon=[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        )

    @staticmethod
    def _first_present(text: str, candidates: tuple[str, ...]) -> str | None:
        searchable = text.casefold()
        for candidate in candidates:
            start = searchable.find(candidate)
            if start >= 0:
                return text[start : start + len(candidate)]
        return None

    @staticmethod
    def _extract_date(text: str) -> tuple[date, str] | None:
        match = re.search(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b", text)
        if not match:
            return None
        year, month, day = (int(part) for part in match.groups())
        try:
            return date(year, month, day), match.group(0)
        except ValueError:
            return None

    @staticmethod
    def _extract_number_after(text: str, label: str) -> tuple[float, str] | None:
        match = re.search(
            rf"\b{re.escape(label)}\b[ \t:=]+([+-]?\d+(?:\.\d+)?)(?![\w.])",
            text,
            re.IGNORECASE,
        )
        return (float(match.group(1)), match.group(0)) if match else None


def _locate_items[
    T: (DocumentMetadataDatum, MetricObservationDatum, MemoryCandidateDatum, PatientEvidenceDatum)
](items: list[T], page: SourcePage) -> list[T]:
    return [
        replace(
            item,
            source_references=[
                reference_for_span(page, reference.text_span)
                for reference in item.source_references
            ],
        )
        for item in items
    ]
