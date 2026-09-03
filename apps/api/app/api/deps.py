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


def require_feature(*, enabled: bool, feature: str) -> None:
    """Hide a disabled slice from callers.

    Routes call this inside the handler body so an unauthenticated request still
    fails authentication first and never learns which features a deployment runs.
    """

    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{feature} is not enabled for this deployment.",
        )

