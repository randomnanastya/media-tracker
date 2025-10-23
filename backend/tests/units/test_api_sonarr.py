import os
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.schemas.error_codes import SonarrErrorCode
from app.schemas.responses import ErrorDetail
from app.schemas.sonarr import SonarrImportResponse


@pytest.mark.asyncio
async def test_import_sonarr_success(
    async_client, mock_session, sonarr_series_basic, sonarr_episodes_basic, mock_exists_result_false
):
    """Test Sonarr import endpoint returns success response."""
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_episodes", new_callable=AsyncMock
        ) as mock_fetch_episodes,
        patch("app.core.logging.logger.info") as mock_logger,
    ):
        mock_fetch_series.return_value = sonarr_series_basic

        mock_fetch_episodes.side_effect = [
            sonarr_episodes_basic if series_id == 1 else []
            for series_id in [s["id"] for s in sonarr_series_basic]
        ]
        mock_session.execute.return_value = mock_exists_result_false
        mock_session.scalar.return_value = None

        response = await async_client.post("/api/v1/sonarr/import")

        assert response.status_code == 200
        assert response.json() == {
            "new_series": len(sonarr_series_basic),
            "updated_series": 0,
            "new_episodes": len(sonarr_episodes_basic),
            "updated_episodes": 0,
            "error": None,
        }
        mock_logger.assert_any_call("Post Sonarr series import...")


@pytest.mark.asyncio
async def test_import_sonarr_failure(async_client, mock_session):
    """API должен вернуть 500 с ошибкой при сбое сервиса."""
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch("app.core.logging.logger.error") as mock_logger,
    ):
        mock_fetch_series.side_effect = Exception("Connection timeout")

        response = await async_client.post("/api/v1/sonarr/import")

        assert response.status_code == 500
        assert response.json() == {
            "detail": {
                "code": "SONARR_FETCH_FAILED",
                "message": "Failed to fetch series: Connection timeout",
            },
        }
        mock_logger.assert_any_call("Failed to fetch series from Sonarr: %s", "Connection timeout")


@pytest.mark.asyncio
async def test_sonarr_import_endpoint_error(async_client: AsyncClient):
    """Test Sonarr import endpoint handles errors correctly."""
    with (
        patch("app.api.sonarr.import_sonarr_series", new_callable=AsyncMock) as mock_import_series,
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch.dict(os.environ, {"SONARR_API_KEY": "test_key"}),
    ):
        mock_import_series.return_value = SonarrImportResponse(
            new_series=0,
            updated_series=0,
            new_episodes=0,
            updated_episodes=0,
            error=ErrorDetail(
                code=SonarrErrorCode.SONARR_FETCH_FAILED,
                message="Failed to fetch series",
            ),
        )
        response = await async_client.post("/api/v1/sonarr/import")
        assert response.status_code == 200
        assert response.json() == {
            "new_series": 0,
            "updated_series": 0,
            "new_episodes": 0,
            "updated_episodes": 0,
            "error": {"code": "SONARR_FETCH_FAILED", "message": "Failed to fetch series"},
        }
        mock_import_series.assert_called_once()
        mock_fetch_series.assert_not_called()


@pytest.mark.asyncio
async def test_sonarr_import_endpoint_no_api_key(async_client: AsyncClient):
    """Test Sonarr import endpoint when SONARR_API_KEY is not set."""
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch("app.core.logging.logger.error") as mock_logger,
        patch.dict(os.environ, {}, clear=True),  # Очищаем окружение
    ):
        mock_fetch_series.side_effect = ValueError("SONARR_API_KEY is not set")
        response = await async_client.post("/api/v1/sonarr/import")
        assert response.status_code == 500
        assert response.json() == {
            "detail": {
                "code": "SONARR_FETCH_FAILED",
                "message": "Failed to fetch series: SONARR_API_KEY is not set",
            },
        }
        mock_logger.assert_any_call(
            "Failed to fetch series from Sonarr: %s", "SONARR_API_KEY is not set"
        )
