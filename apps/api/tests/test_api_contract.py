"""The checked-in OpenAPI document is the source clients generate from."""

import importlib.util
from pathlib import Path

EXPORTER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "export_openapi.py"
REGENERATE = (
    "Regenerate it with `uv run --frozen --package med-app-backend python "
    "apps/api/scripts/export_openapi.py`, then run `npm run contracts:generate` in apps/web."
)


def load_exporter():
    spec = importlib.util.spec_from_file_location("export_openapi", EXPORTER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_in_openapi_document_matches_the_running_api(client):
    """The `client` fixture pins the settings the document is generated under."""

    exporter = load_exporter()

    assert exporter.CONTRACT_PATH.read_text() == exporter.serialize(exporter.openapi_document()), (
        f"contracts/openapi.json no longer matches the API. {REGENERATE}"
    )
