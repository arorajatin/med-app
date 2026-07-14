from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import Settings


@dataclass(frozen=True)
class StoredFile:
    storage_path: str
    size_bytes: int
    mime_type: str
    filename: str


class LocalPrivateStorage:
    def __init__(self, settings: Settings):
        self.root = Path(settings.local_storage_root)
        self.max_upload_bytes = settings.max_upload_bytes

    async def save_upload(
        self,
        *,
        user_id: str,
        profile_id: str,
        record_id: str,
        upload: UploadFile,
    ) -> StoredFile:
        filename = Path(upload.filename or "upload.bin").name
        mime_type = upload.content_type or "application/octet-stream"
        target_dir = self.root / user_id / profile_id / record_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{uuid4()}_{filename}"

        size = 0
        with target.open("wb") as out:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > self.max_upload_bytes:
                    target.unlink(missing_ok=True)
                    raise ValueError("File exceeds configured upload size limit.")
                out.write(chunk)

        return StoredFile(
            storage_path=str(target),
            size_bytes=size,
            mime_type=mime_type,
            filename=filename,
        )

    def read_bytes(self, storage_path: str) -> bytes:
        path = Path(storage_path)
        if not path.exists():
            raise FileNotFoundError(storage_path)
        return path.read_bytes()

