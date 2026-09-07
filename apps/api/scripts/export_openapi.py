"""Write the backend's OpenAPI document to `contracts/openapi.json`.

The checked-in document is the source every client generates from, so it is
regenerated deliberately rather than fetched from a running server.

Usage:
    uv run --frozen --package med-app-backend python apps/api/scripts/export_openapi.py
"""

import json
from pathlib import Path

from app.main import create_app

CONTRACT_PATH = Path(__file__).resolve().parents[3] / "contracts" / "openapi.json"


def openapi_document() -> dict:
    return create_app().openapi()


def serialize(document: dict) -> str:
    """Stable formatting so an unrelated edit cannot show up as contract drift."""

    return json.dumps(document, indent=2, sort_keys=True) + "\n"


def main() -> None:
    CONTRACT_PATH.write_text(serialize(openapi_document()))
    print(f"Wrote {CONTRACT_PATH}")


if __name__ == "__main__":
    main()
