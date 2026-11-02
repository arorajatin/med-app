"""Private server-mediated Storage access using short-lived, single-object JWTs.

The API cannot read the signing secret. A restricted database function checks the
request identity before issuing a token for the non-bypass Storage workload role.
"""

import json
import re
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from app.config import Settings
from app.storage import LocalPrivateStorage, StoredFile

OBJECT_KEY = re.compile(
    r"accounts/([0-9a-f-]{36})/ingestions/([0-9a-f-]{36})/"
    r"parts/([0-9a-f-]{36})/([0-9a-f-]{36})\Z"
)


class StorageUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Private storage is unavailable. Please retry.")


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class SupabasePrivateStorage:
    def __init__(
        self,
        settings: Settings,
        *,
        account_id: str,
        issue_token: Callable[[str, str], str],
        register_cleanup: Callable[[str], None],
    ):
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise StorageUnavailable()
        self.settings = settings
        self.account_id = account_id
        self.bucket = settings.supabase_storage_bucket
        self.base_url = f"{settings.supabase_url.rstrip('/')}/storage/v1"
        self.issue_token = issue_token
        self.register_cleanup = register_cleanup

    def _key(self, object_key: str) -> str:
        match = OBJECT_KEY.fullmatch(object_key)
        if not match or match[1] != self.account_id:
            raise PermissionError("Object is outside the current account.")
        return quote(object_key, safe="/")

    def _send(
        self,
        method: str,
        path: str,
        *,
        operation: str,
        object_key: str,
        body: bytes | None = None,
        content_type: str = "application/json",
    ) -> bytes:
        self._key(object_key)
        request = Request(
            f"{self.base_url}{path}",
            method=method,
            data=body,
            headers={
                "apikey": self.settings.supabase_anon_key or "",
                "Authorization": f"Bearer {self.issue_token(operation, object_key)}",
                "Content-Type": content_type,
                "x-upsert": "false",
                "Cache-Control": "no-store",
            },
        )
        try:
            with build_opener(NoRedirects()).open(request, timeout=30) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError, OSError):
            # Provider responses, URLs, credentials, and filenames must not enter
            # public errors or logs. Never retry through a different backend.
            raise StorageUnavailable() from None

    async def save_upload(
        self, *, account_id: str, ingestion_id: str, part_id: str, upload: UploadFile
    ) -> StoredFile:
        if account_id != self.account_id:
            raise PermissionError("Object is outside the current account.")
        # Temporary validation files are removed on every exit. They are not a
        # durable filesystem fallback; receipt requires a verified remote copy.
        with TemporaryDirectory(prefix="med-app-upload-") as directory:
            validation = LocalPrivateStorage(
                self.settings.model_copy(update={"local_storage_root": directory})
            )
            stored = await validation.save_upload(
                account_id=account_id, ingestion_id=ingestion_id, part_id=part_id, upload=upload
            )
            key = self._key(stored.object_key)
            payload = (Path(directory) / stored.object_key).read_bytes()
            # Commit the cleanup intent before the network write, including when
            # the upload response is lost or the later metadata transaction fails.
            self.register_cleanup(stored.object_key)
            try:
                await run_in_threadpool(
                    self._send,
                    "POST",
                    f"/object/{self.bucket}/{key}",
                    operation="upload",
                    object_key=stored.object_key,
                    body=payload,
                    content_type=stored.mime_type,
                )
                remote = await run_in_threadpool(
                    self._send,
                    "GET",
                    f"/object/authenticated/{self.bucket}/{key}",
                    operation="verify",
                    object_key=stored.object_key,
                )
                if len(remote) != stored.size_bytes or sha256(remote).hexdigest() != stored.sha256:
                    raise StorageUnavailable()
            except Exception:
                try:
                    await run_in_threadpool(self.delete_object, stored.object_key)
                except StorageUnavailable:
                    pass  # The durable intent remains available for reconciliation.
                raise
        return StoredFile(
            storage_bucket=self.bucket,
            object_key=stored.object_key,
            size_bytes=stored.size_bytes,
            mime_type=stored.mime_type,
            filename=stored.filename,
            sha256=stored.sha256,
        )

    def read_bytes(self, object_key: str) -> bytes:
        key = self._key(object_key)
        return self._send(
            "GET",
            f"/object/authenticated/{self.bucket}/{key}",
            operation="read",
            object_key=object_key,
        )

    def delete_object(self, object_key: str) -> None:
        self._key(object_key)
        # Bulk deletion with one exact prefix is idempotent for absent objects.
        self._send(
            "DELETE",
            f"/object/{self.bucket}",
            operation="delete",
            object_key=object_key,
            body=json.dumps({"prefixes": [object_key]}).encode(),
        )

    def signed_read(self, object_key: str, *, expires_in: int = 60) -> str:
        if not 1 <= expires_in <= 60:
            raise ValueError("Private links expire within 60 seconds.")
        key = self._key(object_key)
        payload = self._send(
            "POST",
            f"/object/sign/{self.bucket}/{key}",
            operation="read",
            object_key=object_key,
            body=json.dumps({"expiresIn": expires_in}).encode(),
        )
        try:
            signed = json.loads(payload)["signedURL"]
            if not isinstance(signed, str):
                raise ValueError
            parsed = urlsplit(signed)
            if parsed.scheme or parsed.netloc or parsed.fragment:
                raise ValueError
            if parsed.path != f"/object/sign/{self.bucket}/{key}" or not parsed.query:
                raise ValueError
        except (KeyError, ValueError, TypeError):
            raise StorageUnavailable() from None
        return f"{self.base_url}{signed}"

    def save_raw_output(
        self, *, account_id: str, ingestion_id: str, attempt_id: str, payload: bytes
    ) -> tuple[str, str]:
        raise RuntimeError("Production extraction is not enabled for the upload/storage release.")
