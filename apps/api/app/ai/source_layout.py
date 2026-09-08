"""Canonical source locations, built independently of the structuring model."""

import math
from io import BytesIO

import pdfplumber

from app.ai.base import DocumentPart, SourceLayout, SourcePage, SourceReferenceData, SourceWord


class ExtractionValidationError(ValueError):
    """Only the fixed code may reach a job, response, or log."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def native_layout(parts: tuple[DocumentPart, ...]) -> SourceLayout:
    """Read local PDF words; images have addressable pages but no invented OCR text.

    The production all-pages routing gate and Textract adapter are separate work.
    This parser supplies actual geometry for the local normalized-result contract.
    """

    pages: list[SourcePage] = []
    for part in parts:
        part_id = part.part_id or f"part-{part.ordinal}"
        if part.mime_type != "application/pdf":
            pages.append(SourcePage(part_id, part.ordinal, len(pages) + 1, "", ()))
            continue
        with pdfplumber.open(BytesIO(part.file_bytes)) as pdf:
            for page in pdf.pages:
                text = ""
                words: list[SourceWord] = []
                previous_top: float | None = None
                for index, word in enumerate(page.extract_words()):
                    left, top, right, bottom = (
                        float(word[key]) for key in ("x0", "top", "x1", "bottom")
                    )
                    if not (0 <= left < right <= page.width and 0 <= top < bottom <= page.height):
                        raise ExtractionValidationError("invalid_source_layout")
                    if text:
                        text += (
                            "\n"
                            if previous_top is not None and abs(top - previous_top) > 3
                            else " "
                        )
                    start = len(text)
                    text += word["text"]
                    words.append(
                        SourceWord(
                            id=f"native:{len(pages) + 1}:{index}",
                            start=start,
                            end=len(text),
                            polygon=(
                                (left / page.width, top / page.height),
                                (right / page.width, top / page.height),
                                (right / page.width, bottom / page.height),
                                (left / page.width, bottom / page.height),
                            ),
                        )
                    )
                    previous_top = top
                pages.append(SourcePage(part_id, part.ordinal, len(pages) + 1, text, tuple(words)))
    return SourceLayout("native_text", tuple(pages))


def enclosing_polygon(words: list[SourceWord]) -> list[list[float]]:
    points = [point for word in words for point in word.polygon]
    left, right = min(x for x, _ in points), max(x for x, _ in points)
    top, bottom = min(y for _, y in points), max(y for _, y in points)
    return [[left, top], [right, top], [right, bottom], [left, bottom]]


def reference_for_span(page: SourcePage, span: str) -> SourceReferenceData:
    start = page.text.find(span)
    if start < 0 or not span:
        raise ExtractionValidationError("invalid_source_reference")
    words = [word for word in page.words if word.end > start and word.start < start + len(span)]
    if not words:
        raise ExtractionValidationError("invalid_source_reference")
    return SourceReferenceData(
        part_id=page.part_id,
        part_ordinal=page.part_ordinal,
        logical_page=page.logical_page,
        text_span=span,
        bounding_polygon=enclosing_polygon(words),
        native_word_ids=[word.id for word in words],
    )


def resolve_reference(reference: SourceReferenceData, layout: SourceLayout) -> SourcePage:
    """Resolve every identifier, span, and polygon against independently read evidence."""

    error = ExtractionValidationError("invalid_source_reference")
    page = next(
        (page for page in layout.pages if page.logical_page == reference.logical_page), None
    )
    if (
        page is None
        or reference.part_id != page.part_id
        or reference.part_ordinal != page.part_ordinal
        or not reference.text_span.strip()
    ):
        raise error
    if layout.processing_method == "native_text":
        ids = reference.native_word_ids
        other_ids = reference.textract_block_ids
    else:
        ids = reference.textract_block_ids
        other_ids = reference.native_word_ids
    if not ids or other_ids or len(set(ids)) != len(ids):
        raise error
    by_id = {word.id: (index, word) for index, word in enumerate(page.words)}
    if any(word_id not in by_id for word_id in ids):
        raise error
    indices = [by_id[word_id][0] for word_id in ids]
    if indices != list(range(indices[0], indices[0] + len(indices))):
        raise error
    words = [by_id[word_id][1] for word_id in ids]
    cited_text = page.text[words[0].start : words[-1].end]
    offset = cited_text.find(reference.text_span)
    if (
        offset < 0
        or words[0].start + offset >= words[0].end
        or words[0].start + offset + len(reference.text_span) <= words[-1].start
    ):
        raise error
    expected = enclosing_polygon(words)
    actual = reference.bounding_polygon
    if len(actual) != 4 or any(len(point) != 2 for point in actual):
        raise error
    if any(
        not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0 <= value <= 1
        or abs(value - expected[index][axis]) > 1e-6
        for index, point in enumerate(actual)
        for axis, value in enumerate(point)
    ):
        raise error
    return page


def reference_contains_span(
    reference: SourceReferenceData, page: SourcePage, start: int, end: int
) -> bool:
    """Check an assertion's location inside an already validated reference."""

    ids = reference.native_word_ids or reference.textract_block_ids
    assert ids
    words = {word.id: word for word in page.words}
    first, last = words[ids[0]], words[ids[-1]]
    cited_start = first.start + page.text[first.start : last.end].index(reference.text_span)
    return cited_start <= start < end <= cited_start + len(reference.text_span)
