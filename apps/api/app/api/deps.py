from fastapi import Depends, HTTPException, status

from app.ai.base import Extractor
from app.ai.mock_provider import MockExtractor
from app.config import Settings, get_settings
from app.storage import LocalPrivateStorage


def get_storage(settings: Settings = Depends(get_settings)) -> LocalPrivateStorage:
    return LocalPrivateStorage(settings)


def get_extractor(settings: Settings = Depends(get_settings)) -> Extractor:
    if settings.extraction_provider == "mock":
        return MockExtractor()
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Extraction provider is not implemented: {settings.extraction_provider}",
    )
