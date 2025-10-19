from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_import_sonarr_success(
    async_client, mock_session, sonarr_series_basic, sonarr_episodes_basic, mock_exists_result_false
):
    """API должен вернуть 200 и корректный JSON при успешном импорте."""
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
    """API должен вернуть 200 с ошибкой при сбое сервиса."""
    with (
        patch(
            "app.services.sonarr_service.fetch_sonarr_series", new_callable=AsyncMock
        ) as mock_fetch_series,
        patch("app.core.logging.logger.error") as mock_logger,
    ):
        mock_fetch_series.side_effect = Exception("Connection timeout")

        response = await async_client.post("/api/v1/sonarr/import")

        assert response.status_code == 200
        assert response.json() == {
            "new_series": 0,
            "updated_series": 0,
            "new_episodes": 0,
            "updated_episodes": 0,
            "error": {
                "code": "SONARR_FETCH_FAILED",
                "message": "Failed to fetch series: Connection timeout",
            },
        }
        mock_logger.assert_any_call("Failed to fetch series from Sonarr: %s", "Connection timeout")
