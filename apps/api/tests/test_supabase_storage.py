import asyncio
import json
from hashlib import sha256
from io import BytesIO
from urllib.error import HTTPError
from urllib.parse import urlsplit
from uuid import uuid4

import pytest
from document_fixtures import image_bytes, pdf_bytes
from fastapi import UploadFile

from app.config import Settings
from app.document_inputs import UploadValidationError
from app.storage import LocalPrivateStorage
from app.supabase_storage import StorageUnavailable, SupabasePrivateStorage


class StorageTransport:
    def __init__(self):
        self.objects = {}
        self.calls = []
        self.corrupt = False
        self.fail = False

    def open(self, request, timeout):
        self.calls.append(request)
        assert timeout == 30
        if self.fail:
            raise HTTPError(request.full_url, 503, "private provider detail", {}, None)
        path = urlsplit(request.full_url).path.removeprefix("/storage/v1")
        key = "/".join(path.split("/")[3:])
        if request.method == "DELETE":
            for item in json.loads(request.data)["prefixes"]:
                self.objects.pop(item, None)
            return BytesIO(b"[]")
        if path.startswith("/object/sign/"):
            assert 1 <= json.loads(request.data)["expiresIn"] <= 60
            return BytesIO(json.dumps({"signedURL": path + "?token=private-link"}).encode())
        if request.method == "POST":
            assert key not in self.objects
            assert request.get_header("X-upsert") == "false"
            self.objects[key] = request.data
            return BytesIO(b"{}")
        key = "/".join(path.split("/")[4:])
        return BytesIO(b"wrong content" if self.corrupt else self.objects[key])


@pytest.fixture()
def storage_setup(tmp_path, monkeypatch):
    transport = StorageTransport()
    monkeypatch.setattr("app.supabase_storage.build_opener", lambda *args: transport)
    account_id = str(uuid4())
    settings = Settings(
        _env_file=None,
        local_storage_root=str(tmp_path / "local"),
        supabase_url="https://test.supabase.co",
        supabase_anon_key="sb_publishable_test",
    )
    intents = []
    tokens = []

    def issue(operation, key):
        tokens.append((operation, key))
        return "scoped-workload-token"

    remote = SupabasePrivateStorage(
        settings,
        account_id=account_id,
        issue_token=issue,
        register_cleanup=intents.append,
    )
    return settings, remote, transport, intents, tokens, account_id


@pytest.mark.parametrize("backend", ["local", "supabase"])
@pytest.mark.parametrize(
    "filename,payload", [("report.pdf", pdf_bytes()), ("scan.png", image_bytes())]
)
def test_shared_validated_upload_contract(storage_setup, backend, filename, payload):
    settings, remote, transport, intents, tokens, account_id = storage_setup
    adapter = remote if backend == "supabase" else LocalPrivateStorage(settings)
    ingestion_id, part_id = str(uuid4()), str(uuid4())
    stored = asyncio.run(
        adapter.save_upload(
            account_id=account_id,
            ingestion_id=ingestion_id,
            part_id=part_id,
            upload=UploadFile(filename=filename, file=BytesIO(payload)),
        )
    )
    assert stored.object_key.startswith(
        f"accounts/{account_id}/ingestions/{ingestion_id}/parts/{part_id}/"
    )
    assert filename not in stored.object_key
    assert stored.size_bytes == len(payload)
    assert stored.sha256 == sha256(payload).hexdigest()
    assert adapter.read_bytes(stored.object_key) == payload
    if backend == "supabase":
        assert intents == [stored.object_key]
        assert [operation for operation, _ in tokens] == ["upload", "verify", "read"]
        assert all(
            call.get_header("Authorization") == "Bearer scoped-workload-token"
            for call in transport.calls
        )
        assert remote.signed_read(stored.object_key).startswith(
            "https://test.supabase.co/storage/v1/object/sign/"
        )
    adapter.delete_object(stored.object_key)
    adapter.delete_object(stored.object_key)


def test_rejected_source_never_reaches_remote_storage(storage_setup):
    _, remote, transport, intents, _, account_id = storage_setup
    with pytest.raises(UploadValidationError):
        asyncio.run(
            remote.save_upload(
                account_id=account_id,
                ingestion_id=str(uuid4()),
                part_id=str(uuid4()),
                upload=UploadFile(filename="bad.pdf", file=BytesIO(b"invalid")),
            )
        )
    assert transport.calls == intents == []


def test_checksum_mismatch_deletes_remote_copy_and_keeps_reconciliation_intent(storage_setup):
    _, remote, transport, intents, _, account_id = storage_setup
    transport.corrupt = True
    with pytest.raises(StorageUnavailable):
        asyncio.run(
            remote.save_upload(
                account_id=account_id,
                ingestion_id=str(uuid4()),
                part_id=str(uuid4()),
                upload=UploadFile(filename="report.pdf", file=BytesIO(pdf_bytes())),
            )
        )
    assert transport.objects == {}
    assert len(intents) == 1


def test_provider_failures_are_safe_and_have_durable_cleanup_intent(storage_setup):
    _, remote, transport, intents, _, account_id = storage_setup
    transport.fail = True
    with pytest.raises(StorageUnavailable, match="Private storage is unavailable") as error:
        asyncio.run(
            remote.save_upload(
                account_id=account_id,
                ingestion_id=str(uuid4()),
                part_id=str(uuid4()),
                upload=UploadFile(filename="private-name.pdf", file=BytesIO(pdf_bytes())),
            )
        )
    assert "private-name" not in str(error.value)
    assert "provider detail" not in str(error.value)
    assert len(intents) == 1


def test_cross_account_keys_and_long_lived_links_are_rejected(storage_setup):
    _, remote, transport, _, _, account_id = storage_setup
    foreign_key = f"accounts/{uuid4()}/ingestions/{uuid4()}/parts/{uuid4()}/{uuid4()}"
    for operation in (remote.read_bytes, remote.delete_object, remote.signed_read):
        with pytest.raises(PermissionError):
            operation(foreign_key)
    own_key = f"accounts/{account_id}/ingestions/{uuid4()}/parts/{uuid4()}/{uuid4()}"
    for lifetime in (0, 61, 3600):
        with pytest.raises(ValueError):
            remote.signed_read(own_key, expires_in=lifetime)
    assert transport.calls == []


def test_failure_to_record_intent_prevents_storage_write(storage_setup):
    _, remote, transport, _, _, account_id = storage_setup

    def failed_intent(key):
        raise RuntimeError("Database unavailable")

    remote.register_cleanup = failed_intent
    with pytest.raises(RuntimeError, match="Database unavailable"):
        asyncio.run(
            remote.save_upload(
                account_id=account_id,
                ingestion_id=str(uuid4()),
                part_id=str(uuid4()),
                upload=UploadFile(filename="report.pdf", file=BytesIO(pdf_bytes())),
            )
        )
    assert transport.calls == []
