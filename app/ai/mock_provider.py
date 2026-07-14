from __future__ import annotations

import re
from datetime import date

from app.ai.base import DocumentExtraction, ExtractedDatum, Extractor


class MockExtractor(Extractor):
    provider_name = "mock"

    def extract_document(
        self,
        *,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        profile_context: dict | None = None,
    ) -> DocumentExtraction:
        text = file_bytes.decode("utf-8", errors="ignore")
        searchable = f"{filename}\n{text}".lower()
        fields: list[ExtractedDatum] = []

        document_type = "medical_record"
        if any(term in searchable for term in ("lab", "cbc", "creatinine", "hemoglobin")):
            document_type = "lab_report"
        elif any(term in searchable for term in ("prescription", "rx", "tablet", "capsule")):
            document_type = "prescription"
        elif any(term in searchable for term in ("discharge", "admission")):
            document_type = "discharge_summary"
        elif any(term in searchable for term in ("xray", "mri", "ct scan", "ultrasound")):
            document_type = "imaging_report"

        fields.append(
            ExtractedDatum(
                field_type="document_type",
                label="Document type",
                value={"text": document_type},
                confidence=0.72,
                source_reference="mock:file_or_content",
            )
        )

        record_date = self._extract_date(text)
        if record_date:
            fields.append(
                ExtractedDatum(
                    field_type="record_date",
                    label="Record date",
                    value={"date": record_date.isoformat()},
                    normalized_value={"date": record_date.isoformat()},
                    confidence=0.76,
                    source_reference="mock:date_pattern",
                )
            )

        if "liver" in searchable or "sgpt" in searchable or "sgot" in searchable:
            fields.append(
                ExtractedDatum(
                    field_type="condition",
                    label="Liver-related finding",
                    value={"text": "Liver-related finding mentioned in the record"},
                    normalized_value={"body_system": "liver"},
                    confidence=0.67,
                    source_reference="mock:liver_keyword",
                )
            )

        if "kidney" in searchable or "creatinine" in searchable:
            fields.append(
                ExtractedDatum(
                    field_type="condition",
                    label="Kidney-related finding",
                    value={"text": "Kidney-related finding mentioned in the record"},
                    normalized_value={"body_system": "kidney"},
                    confidence=0.67,
                    source_reference="mock:kidney_keyword",
                )
            )

        creatinine = self._extract_number_after(text, "creatinine")
        if creatinine is not None:
            fields.append(
                ExtractedDatum(
                    field_type="test_result",
                    label="Creatinine",
                    value={"name": "Creatinine", "value": creatinine, "unit": "mg/dL"},
                    normalized_value={"marker": "creatinine", "value": creatinine, "unit": "mg/dL"},
                    confidence=0.7,
                    source_reference="mock:creatinine_pattern",
                )
            )

        hemoglobin = self._extract_number_after(text, "hemoglobin")
        if hemoglobin is not None:
            fields.append(
                ExtractedDatum(
                    field_type="test_result",
                    label="Hemoglobin",
                    value={"name": "Hemoglobin", "value": hemoglobin, "unit": "g/dL"},
                    normalized_value={"marker": "hemoglobin", "value": hemoglobin, "unit": "g/dL"},
                    confidence=0.7,
                    source_reference="mock:hemoglobin_pattern",
                )
            )

        medication_match = re.search(
            r"\b(?:tablet|capsule|tab\.?|cap\.?)\s+([a-zA-Z0-9 -]{2,40})", text, re.IGNORECASE
        )
        if medication_match:
            medication = medication_match.group(1).strip()
            fields.append(
                ExtractedDatum(
                    field_type="medication",
                    label=medication,
                    value={"name": medication},
                    confidence=0.58,
                    source_reference="mock:medication_pattern",
                )
            )

        if "follow up" in searchable or "follow-up" in searchable:
            fields.append(
                ExtractedDatum(
                    field_type="follow_up",
                    label="Follow-up mentioned",
                    value={"text": "Follow-up instruction mentioned in the record"},
                    confidence=0.6,
                    source_reference="mock:follow_up_keyword",
                )
            )

        return DocumentExtraction(
            document_type=document_type,
            raw_output={
                "provider": self.provider_name,
                "document_type": document_type,
                "filename": filename,
                "mime_type": mime_type,
                "field_count": len(fields),
            },
            fields=fields,
        )

    @staticmethod
    def _extract_date(text: str) -> date | None:
        match = re.search(r"\b(20\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b", text)
        if not match:
            return None
        year, month, day = (int(part) for part in match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    @staticmethod
    def _extract_number_after(text: str, label: str) -> float | None:
        match = re.search(rf"{label}\D+(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        return float(match.group(1)) if match else None

