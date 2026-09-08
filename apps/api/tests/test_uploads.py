import asyncio
from hashlib import sha256
from io import BytesIO
from pathlib import Path

import pytest
from document_fixtures import image_bytes, pdf_bytes
from fastapi import UploadFile

from app import models
from app.ai.base import DocumentExtraction, Extractor
from app.api import routes
from app.api.deps import get_extractor
from app.config import get_settings
from app.database import get_db
from app.document_inputs import UploadValidationError
from app.storage import LocalPrivateStorage

AUTH = {"Authorization": "Bearer upload-owner"}


def upload(client, files, *, route="direct-file", data=None):
    return client.post(
        f"/ingestions/{route}",
        headers=AUTH,
        files=[("uploads", file) for file in files],
        data=data or {},
    )


def assert_no_receipt(tmp_path):
    with next(get_db()) as db:
        for model in (models.Ingestion, models.IngestionPart, models.ExtractionJob):
            assert db.query(model).count() == 0
    assert not [path for path in (tmp_path / "storage").rglob("*") if path.is_file()]


@pytest.mark.parametrize("format,mime", [("JPEG", "image/jpeg"), ("PNG", "image/png")])
@pytest.mark.parametrize("route", ["direct-file", "camera"])
def test_valid_image_has_detected_mime_and_private_route_provenance(client, format, mime, route):
    content = image_bytes(format)
    response = upload(client, [("original.img", content, "application/octet-stream")], route=route)
    assert response.status_code == 201, response.text
    result = response.json()
    ingestion = result["ingestion"]
    assert ingestion["source_channel"] == route.replace("-", "_")
    assert ingestion["upload_state"] == "complete"
    assert ingestion["assignment_state"] == "needs_assignment"
    assert result["record"] is None
    assert result["parts"][0]["detected_mime_type"] == mime
    assert "object_key" not in response.text
    assert "storage_bucket" not in response.text
    assert "authorization_basis" not in response.text
    with next(get_db()) as db:
        part = db.query(models.IngestionPart).one()
        assert part.sha256 == sha256(content).hexdigest()
        assert part.authorization_basis == "authenticated_web_upload"
        assert part.actor_identity_id
        assert part.account_id == db.query(models.Ingestion).one().account_id
        assert ingestion["id"] in part.object_key


def test_pdf_and_user_context_keep_original_identity_without_trusting_notes(client):
    profile = client.put(
        "/account/onboarding/self-profile", headers=AUTH, json={"display_name": "Asha"}
    ).json()
    response = upload(
        client,
        [("original.pdf", pdf_bytes(), "image/png")],
        data={
            "provisional_profile_id": profile["id"],
            "display_filename": "September report",
            "user_context": "Possible asthma",
        },
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["parts"][0]["detected_mime_type"] == "application/pdf"
    assert result["parts"][0]["original_filename"] == "original.pdf"
    assert result["ingestion"]["display_filename"] == "September report"
    assert result["ingestion"]["user_context"] == "Possible asthma"
    assert result["ingestion"]["provisional_profile_id"] == profile["id"]
    assert result["ingestion"]["resolved_profile_id"] is None
    with next(get_db()) as db:
        assert db.query(models.Ingestion).one().user_renamed is True
        assert db.query(models.MemoryFact).count() == 0


def test_ordered_images_create_one_atomic_job_and_keep_parts_separate(make_client):
    client = make_client(EXTRACTION_RUN_INLINE="false")
    files = [
        ("second.png", image_bytes(size=(2, 3)), "image/png"),
        ("first.jpg", image_bytes("JPEG"), "image/jpeg"),
    ]
    response = upload(client, files)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["extraction_job"]["status"] == "queued"
    assert [part["ordinal"] for part in result["parts"]] == [0, 1]
    assert [part["original_filename"] for part in result["parts"]] == ["second.png", "first.jpg"]
    with next(get_db()) as db:
        assert db.query(models.Ingestion).count() == 1
        assert db.query(models.ExtractionJob).count() == 1
        assert db.query(models.ExtractionAttempt).count() == 0

    captured = []

    class RecordingExtractor(Extractor):
        def extract_logical_document(self, *, parts):
            captured.extend(parts)
            return DocumentExtraction("medical_record", {}, "textract_ocr", "test")

    client.app.dependency_overrides[get_extractor] = lambda: RecordingExtractor()
    job_id = result["extraction_job"]["id"]
    response = client.post(f"/extraction/jobs/{job_id}/run", headers=AUTH)
    assert response.status_code == 200, response.text
    assert [part.file_bytes for part in captured] == [file[1] for file in files]
    assert [part.ordinal for part in captured] == [0, 1]
    with next(get_db()) as db:
        assert db.query(models.ExtractionAttempt).count() == 1


@pytest.mark.parametrize(
    "files,route,status,code",
    [
        ([("empty.pdf", b"", "application/pdf")], "direct-file", 422, "empty_file"),
        (
            [("fake.pdf", b"not a PDF", "application/pdf")],
            "direct-file",
            415,
            "unsupported_file_type",
        ),
        (
            [("broken.pdf", b"%PDF-1.4\nbroken", "application/pdf")],
            "direct-file",
            422,
            "corrupt_pdf",
        ),
        ([("broken.png", b"\x89PNG\r\n\x1a\nbroken", "image/png")], "camera", 422, "corrupt_image"),
        (
            [("broken.jpg", image_bytes("JPEG")[:-20], "image/jpeg")],
            "direct-file",
            422,
            "corrupt_image",
        ),
        (
            [("scan.gif", image_bytes("GIF"), "image/png")],
            "direct-file",
            415,
            "unsupported_file_type",
        ),
        ([("report.pdf", pdf_bytes(), "image/jpeg")], "camera", 415, "invalid_document_group"),
        (
            [
                ("image.png", image_bytes(), "image/png"),
                ("report.pdf", pdf_bytes(), "application/pdf"),
            ],
            "direct-file",
            415,
            "invalid_document_group",
        ),
        (
            [("report.pdf", pdf_bytes(pages=21), "application/pdf")],
            "direct-file",
            413,
            "too_many_pages",
        ),
        (
            [("wide.png", image_bytes(size=(10001, 1)), "image/png")],
            "direct-file",
            413,
            "image_dimensions_exceeded",
        ),
        (
            # Within the per-side cap, but a tiny file that would decode to ~40 million pixels.
            [("bomb.png", image_bytes(size=(8000, 5001), mode="L"), "image/png")],
            "direct-file",
            413,
            "image_pixels_exceeded",
        ),
    ],
)
def test_invalid_content_never_completes_or_leaves_private_parts(
    client, tmp_path, files, route, status, code
):
    response = upload(client, files, route=route)
    assert response.status_code == status, response.text
    assert response.headers["X-Upload-Error-Code"] == code
    assert_no_receipt(tmp_path)


@pytest.mark.parametrize("kind", ["image", "document", "combined", "parts", "configured"])
def test_size_limits_and_partial_cleanup(make_client, tmp_path, kind):
    client = make_client(MAX_UPLOAD_BYTES="100" if kind == "configured" else "99999999")
    picture = image_bytes()
    if kind == "image":
        files = [("large.png", picture.ljust(10_000_001, b"\x00"), "image/png")]
    elif kind == "document":
        files = [("large.pdf", pdf_bytes().ljust(15_000_001), "application/pdf")]
    elif kind == "combined":
        files = [
            (f"{index}.png", picture.ljust(8_000_000, b"\x00"), "image/png") for index in range(2)
        ]
    elif kind == "parts":
        files = [(f"{index}.png", picture, "image/png") for index in range(21)]
    else:
        files = [("report.pdf", pdf_bytes(), "application/pdf")]
    response = upload(client, files)
    assert response.status_code == 413, response.text
    assert_no_receipt(tmp_path)


@pytest.mark.parametrize(
    "kind", ["image_bytes", "dimension", "pdf_pages", "parts", "document_bytes"]
)
def test_inclusive_product_boundaries(make_client, kind):
    client = make_client(EXTRACTION_RUN_INLINE="false")
    if kind == "image_bytes":
        files = [("large.png", image_bytes().ljust(10_000_000, b"\x00"), "image/png")]
    elif kind == "dimension":
        files = [("wide.png", image_bytes(size=(10000, 1)), "image/png")]
    elif kind == "pdf_pages":
        files = [("report.pdf", pdf_bytes(pages=20), "application/pdf")]
    elif kind == "document_bytes":
        files = [("report.pdf", pdf_bytes().ljust(15_000_000), "application/pdf")]
    else:
        files = [(f"{index}.png", image_bytes(), "image/png") for index in range(20)]
    response = upload(client, files)
    assert response.status_code == 201, response.text


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_channel", "camera"),
        ("account_id", "other-account"),
        ("actor_identity_id", "someone-else"),
        ("authorization_basis", "anything"),
        ("display_filename", "x" * 261),
        ("user_context", "x" * 4001),
    ],
)
def test_rejected_metadata_has_no_upload_side_effects(client, tmp_path, field, value):
    response = upload(client, [("report.pdf", pdf_bytes(), "application/pdf")], data={field: value})
    assert response.status_code == 422
    assert_no_receipt(tmp_path)


@pytest.mark.parametrize("failure", ["second_part", "job"])
def test_storage_or_job_failure_rolls_back_receipt_and_allows_retry(
    client, tmp_path, monkeypatch, failure
):
    files = [("1.png", image_bytes(), "image/png"), ("2.png", image_bytes(), "image/png")]
    with monkeypatch.context() as patch:
        if failure == "second_part":
            original = LocalPrivateStorage.save_upload
            calls = 0

            async def fail_second(self, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("private/internal/storage/key")
                return await original(self, **kwargs)

            patch.setattr(LocalPrivateStorage, "save_upload", fail_second)
        else:

            def fail_job(*args, **kwargs):
                raise RuntimeError("private database error")

            patch.setattr(routes, "create_extraction_job", fail_job)
        response = upload(client, files)
        assert response.status_code == 503
        assert "private" not in response.text
        assert_no_receipt(tmp_path)
    assert upload(client, files).status_code == 201


def test_failed_stream_removes_the_current_partial_object(client, tmp_path, monkeypatch):
    storage = LocalPrivateStorage(get_settings())
    file = UploadFile(filename="report.pdf", file=BytesIO(pdf_bytes()))
    calls = 0

    async def fail_read(size):
        nonlocal calls
        calls += 1
        if calls == 1:
            return b"partial"
        raise OSError("read interrupted")

    monkeypatch.setattr(file, "read", fail_read)
    with pytest.raises(OSError):
        asyncio.run(
            storage.save_upload(
                account_id="owner", ingestion_id="ingestion", part_id="part", upload=file
            )
        )
    assert_no_receipt(tmp_path)


def test_password_protected_pdf_is_rejected(client, tmp_path):
    content = (Path(__file__).parent / "fixtures" / "encrypted.pdf").read_bytes()
    response = upload(client, [("encrypted.pdf", content, "application/pdf")])
    assert response.status_code == 422
    assert response.headers["X-Upload-Error-Code"] == "encrypted_pdf"
    assert_no_receipt(tmp_path)


def test_job_is_not_created_for_incomplete_ingestion(client):
    with next(get_db()) as db:
        with pytest.raises(ValueError, match="complete logical document"):
            routes.create_extraction_job(db, ingestion=models.Ingestion(upload_state="receiving"))


def test_unsupported_multi_image_extractor_fails_without_joining_files():
    with pytest.raises(ValueError, match="ordered multi-image"):
        Extractor().extract_logical_document(parts=())


def test_empty_filename_is_rejected_before_storage(client, tmp_path):
    storage = LocalPrivateStorage(get_settings())
    with pytest.raises(UploadValidationError, match="filename"):
        asyncio.run(
            storage.save_upload(
                account_id="owner",
                ingestion_id="ingestion",
                part_id="part",
                upload=UploadFile(filename="   ", file=BytesIO(image_bytes())),
            )
        )
    assert_no_receipt(tmp_path)
