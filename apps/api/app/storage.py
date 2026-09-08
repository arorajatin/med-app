import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.document_inputs import MAX_DOCUMENT_BYTES, UploadValidationError, validate_source


@dataclass(frozen=True)
class StoredFile:
    storage_bucket: str
    object_key: str
    size_bytes: int
    mime_type: str
    filename: str
    sha256: str


class LocalPrivateStorage:
    def __init__(self, settings: Settings):
        self.root = Path(settings.local_storage_root)
        self.max_upload_bytes = min(settings.max_upload_bytes, MAX_DOCUMENT_BYTES)

    async def save_upload(
        self,
        *,
        account_id: str,
        ingestion_id: str,
        part_id: str,
        upload: UploadFile,
    ) -> StoredFile:
        filename = re.sub(
            r"[\x00-\x1f\x7f]", "", (upload.filename or "upload").replace("\\", "/").split("/")[-1]
        )
        if not filename.strip() or len(filename) > 260:
            raise UploadValidationError(
                "invalid_filename", "Use a filename between 1 and 260 characters."
            )
        object_key = (
            Path("accounts")
            / account_id
            / "ingestions"
            / ingestion_id
            / "parts"
            / part_id
            / str(uuid4())
        )
        target = self.root / object_key
        target_dir = target.parent
        size = 0
        digest = sha256()
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            with target.open("wb") as out:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_upload_bytes:
                        raise UploadValidationError(
                            "document_too_large",
                            "The report exceeds the upload size limit (at most 15 MB).",
                            413,
                        )
                    out.write(chunk)
                    digest.update(chunk)
            # Decoding images and parsing PDF pages is slow and CPU-bound; keep it off
            # the event loop so one upload cannot stall every other in-flight request.
            mime_type = await run_in_threadpool(validate_source, target, size_bytes=size)
        except Exception:
            target.unlink(missing_ok=True)
            raise

        return StoredFile(
            storage_bucket="local-private",
            object_key=str(object_key),
            size_bytes=size,
            mime_type=mime_type,
            filename=filename,
            sha256=digest.hexdigest(),
        )

    def save_raw_output(
        self, *, account_id: str, ingestion_id: str, attempt_id: str, payload: bytes
    ) -> tuple[str, str]:
        object_key = (
            Path("accounts")
            / account_id
            / "ingestions"
            / ingestion_id
            / "attempts"
            / attempt_id
            / str(uuid4())
        )
        target = self.root / object_key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        return "local-private", str(object_key)

    def read_bytes(self, object_key: str) -> bytes:
        path = self.root / object_key
        if not path.exists():
            raise FileNotFoundError(object_key)
        return path.read_bytes()

    def delete_object(self, object_key: str) -> None:
        (self.root / object_key).unlink(missing_ok=True)
