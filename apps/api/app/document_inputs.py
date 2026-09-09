"""Validate private source content without trusting browser MIME or filenames."""

import warnings
from pathlib import Path

import pdfplumber
from pdfminer.pdfdocument import PDFPasswordIncorrect
from PIL import Image, UnidentifiedImageError

MAX_DOCUMENT_BYTES = 15_000_000
MAX_LOGICAL_PARTS = 20
MAX_IMAGE_BYTES = 10_000_000
MAX_IMAGE_DIMENSION = 10_000
# A 600 DPI A4 scan is ~35 megapixels, so this clears real reports while bounding the
# decoded buffer a single image can allocate; the per-side cap alone permits 100 megapixels.
MAX_IMAGE_PIXELS = 40_000_000
IMAGE_MIME_TYPES = {"image/jpeg", "image/png"}


class UploadValidationError(ValueError):
    def __init__(self, code: str, message: str, status_code: int = 422):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def validate_source(path: Path, *, size_bytes: int) -> str:
    if size_bytes == 0:
        raise UploadValidationError("empty_file", "This file is empty. Choose another file.")
    with path.open("rb") as source:
        signature = source.read(8)
    if signature.startswith(b"%PDF-"):
        return _validate_pdf(path)
    if not signature.startswith((b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")):
        raise UploadValidationError(
            "unsupported_file_type", "Choose an unencrypted PDF, JPEG, or PNG file.", 415
        )
    if size_bytes > MAX_IMAGE_BYTES:
        raise UploadValidationError("image_too_large", "Each image must be 10 MB or smaller.", 413)
    try:
        with _open_within_limits(path) as picture:
            if getattr(picture, "n_frames", 1) != 1:
                raise UploadValidationError(
                    "animated_image", "Choose a still JPEG or PNG image, without animation."
                )
            mime_type = Image.MIME[picture.format or ""]
            picture.verify()
        # verify() checks the container; load() also rejects truncated pixel data.
        with _open_within_limits(path) as picture:
            picture.load()
        return mime_type
    except Image.DecompressionBombError as exc:
        raise UploadValidationError(
            "image_pixels_exceeded",
            "Each image must be 40 megapixels or smaller.",
            413,
        ) from exc
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        if isinstance(exc, UploadValidationError):
            raise
        raise UploadValidationError(
            "corrupt_image", "This image could not be opened. Export it again or retake the photo."
        ) from exc


def _open_within_limits(path: Path) -> Image.Image:
    """Open the header only and reject oversized images before any pixel data is decoded."""
    with warnings.catch_warnings():
        # Pillow's advisory bomb threshold is looser than the pixel cap enforced below.
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        picture = Image.open(path)
    width, height = picture.size
    if max(width, height) > MAX_IMAGE_DIMENSION:
        picture.close()
        raise UploadValidationError(
            "image_dimensions_exceeded",
            "Each image dimension must be 10,000 pixels or smaller.",
            413,
        )
    if width * height > MAX_IMAGE_PIXELS:
        picture.close()
        raise UploadValidationError(
            "image_pixels_exceeded", "Each image must be 40 megapixels or smaller.", 413
        )
    return picture


def _validate_pdf(path: Path) -> str:
    try:
        with pdfplumber.open(path) as document:
            if document.doc.encryption:
                raise PDFPasswordIncorrect
            if not document.pages:
                raise ValueError("No pages")
            if len(document.pages) > MAX_LOGICAL_PARTS:
                raise UploadValidationError(
                    "too_many_pages", "A PDF must contain no more than 20 pages.", 413
                )
            for page in document.pages:
                # Parse every page so a broken later page cannot complete an upload.
                _ = page.layout
                page.close()
        return "application/pdf"
    except PDFPasswordIncorrect as exc:
        raise UploadValidationError(
            "encrypted_pdf", "This PDF is encrypted. Upload an unencrypted copy."
        ) from exc
    except Exception as exc:
        if isinstance(exc, UploadValidationError):
            raise
        if isinstance(exc.__context__, PDFPasswordIncorrect):
            raise UploadValidationError(
                "encrypted_pdf", "This PDF is encrypted. Upload an unencrypted copy."
            ) from exc
        raise UploadValidationError(
            "corrupt_pdf", "This PDF could not be opened. Export it again and try another copy."
        ) from exc
