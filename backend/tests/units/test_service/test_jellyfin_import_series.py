from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.jellyfin import JellyfinImportSeriesResponse
from app.services.import_jellyfin_series_service import import_jellyfin_series


@pytest.mark.asyncio
async def test_import_jellyfin_series_creates_new_series(mock_session):
    """Создание нового сериала (без сезонов)"""
    series_data = [
        {
            "Id": "jf-series-1",
            "Name": "Breaking Bad",
            "ProviderIds": {
                "Tvdb": "81189",
                "Imdb": "tt0903747",
                "Tmdb": "1396",
            },
            "PremiereDate": "2008-01-20T00:00:00Z",
            "Status": "Ended",
            "ProductionYear": 2008,
        }
    ]

    fake_series = AsyncMock()
    fake_series.id = 1
    fake_series.media.title = "Breaking Bad"

    with (
        patch(
            "app.services.import_jellyfin_series_service.fetch_jellyfin_series",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "app.services.import_jellyfin_series_service._find_series_by_jellyfin_id",
            new_callable=AsyncMock,
        ) as mock_find_jf,
        patch(
            "app.services.import_jellyfin_series_service.find_series_by_external_ids",
            new_callable=AsyncMock,
        ) as mock_find_external,
        patch(
            "app.services.import_jellyfin_series_service.create_new_series",
            new_callable=AsyncMock,
        ) as mock_create,
        patch(
            "app.services.import_jellyfin_series_service._process_seasons_and_episodes",
            new_callable=AsyncMock,
        ) as mock_process,
    ):
        mock_fetch.return_value = series_data
        mock_find_jf.return_value = None
        mock_find_external.return_value = None
        mock_create.return_value = fake_series
        mock_process.return_value = (0, 0)

        result = await import_jellyfin_series(mock_session)

        assert result == JellyfinImportSeriesResponse(
            new_series=1,
            updated_series=0,
            new_episodes=0,
            updated_episodes=0,
        )

        mock_create.assert_awaited_once()
        mock_process.assert_awaited_once()
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_import_jellyfin_series_updates_existing_by_jellyfin_id(
    mock_session,
    existing_series_without_ids,
):
    """Обновление существующего сериала по jellyfin_id"""
    series_data = [
        {
            "Id": "jf-123",
            "Name": "Better Call Saul",
            "ProviderIds": {"Imdb": "tt3032476"},
            "PremiereDate": "2015-02-08",
            "Status": "Ended",
            "ProductionYear": 2015,
        }
    ]

    with (
        patch(
            "app.services.import_jellyfin_series_service.fetch_jellyfin_series",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "app.services.import_jellyfin_series_service._find_series_by_jellyfin_id",
            new_callable=AsyncMock,
        ) as mock_find_jf,
        patch(
            "app.services.import_jellyfin_series_service.find_series_by_external_ids",
            new_callable=AsyncMock,
        ) as mock_find_external,
        patch(
            "app.services.import_jellyfin_series_service._process_seasons_and_episodes",
            new_callable=AsyncMock,
        ) as mock_process,
    ):
        mock_fetch.return_value = series_data
        mock_find_jf.return_value = existing_series_without_ids
        mock_find_external.return_value = None
        mock_process.return_value = (0, 0)

        result = await import_jellyfin_series(mock_session)

        assert result.new_series == 0
        assert result.updated_series == 1
        mock_session.commit.assert_called_once()
