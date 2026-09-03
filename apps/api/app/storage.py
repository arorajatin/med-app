from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import Settings


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
        self.max_upload_bytes = settings.max_upload_bytes

    async def save_upload(
        self,
        *,
        account_id: str,
        ingestion_id: str,
        part_id: str,
        upload: UploadFile,
    ) -> StoredFile:
        filename = Path(upload.filename or "upload.bin").name
        mime_type = upload.content_type or "application/octet-stream"
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
        target_dir.mkdir(parents=True, exist_ok=True)

        size = 0
        digest = sha256()
        with target.open("wb") as out:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > self.max_upload_bytes:
                    target.unlink(missing_ok=True)
                    raise ValueError("File exceeds configured upload size limit.")
                out.write(chunk)
                digest.update(chunk)

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
