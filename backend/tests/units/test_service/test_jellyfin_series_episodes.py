from unittest.mock import AsyncMock, patch

import pytest

from app.services.import_jellyfin_series_service import _process_seasons_and_episodes


@pytest.mark.asyncio
async def test_process_seasons_no_episodes(mock_session, series):
    """нет эпизодов → ничего не делаем"""
    with patch(
        "app.services.import_jellyfin_series_service.fetch_jellyfin_episodes",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = []

        result = await _process_seasons_and_episodes(
            mock_session,
            series,
            "jf-series",
        )

        assert result == (0, 0)
        mock_session.add.assert_not_called()
        mock_session.flush.assert_not_called()


@pytest.mark.asyncio
async def test_process_seasons_creates_season_and_episodes(mock_session, series, empty_scalars):
    """создаётся 1 сезон и 2 эпизода"""
    episodes = [
        {
            "Id": "ep1",
            "ParentIndexNumber": 1,
            "IndexNumber": 1,
            "Name": "Pilot",
            "PremiereDate": "2020-01-01T00:00:00Z",
            "SeasonId": "season1",
        },
        {
            "Id": "ep2",
            "ParentIndexNumber": 1,
            "IndexNumber": 2,
            "Name": "Episode 2",
            "PremiereDate": "2020-01-08T00:00:00Z",
            "SeasonId": "season1",
        },
    ]

    with patch(
        "app.services.import_jellyfin_series_service.fetch_jellyfin_episodes",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = episodes

        mock_session.scalars.side_effect = [
            [],  # seasons
            [],  # episodes
        ]

        new_cnt, upd_cnt = await _process_seasons_and_episodes(
            mock_session,
            series,
            "jf-series",
        )

        assert new_cnt == 2
        assert upd_cnt == 0

        # Season + 2 Episodes
        assert mock_session.add.call_count == 3
        mock_session.flush.assert_called()


@pytest.mark.asyncio
async def test_process_seasons_updates_existing_episode(mock_session, series):
    """обновляется существующий эпизод"""
    existing_season = AsyncMock()
    existing_season.id = 10
    existing_season.number = 1
    existing_season.jellyfin_id = "season1"
    existing_season.release_date = None

    existing_episode = AsyncMock()
    existing_episode.jellyfin_id = "ep1"
    existing_episode.number = 1
    existing_episode.title = "Old title"
    existing_episode.air_date = None

    episodes = [
        {
            "Id": "ep1",
            "ParentIndexNumber": 1,
            "IndexNumber": 1,
            "Name": "New title",
            "PremiereDate": "2020-01-01T00:00:00Z",
            "SeasonId": "season1",
        }
    ]

    with patch(
        "app.services.import_jellyfin_series_service.fetch_jellyfin_episodes",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = episodes

        mock_session.scalars.side_effect = [
            [existing_season],
            [existing_episode],
        ]

        new_cnt, upd_cnt = await _process_seasons_and_episodes(
            mock_session,
            series,
            "jf-series",
        )

        assert new_cnt == 0
        assert upd_cnt == 1
        mock_session.flush.assert_called()


@pytest.mark.asyncio
async def test_process_seasons_skips_invalid_episode(mock_session, series):
    """битые эпизоды пропускаются"""
    episodes = [
        {
            "Id": None,  # invalid
            "ParentIndexNumber": "1",
            "IndexNumber": None,
            "Name": None,
        }
    ]

    with patch(
        "app.services.import_jellyfin_series_service.fetch_jellyfin_episodes",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = episodes

        mock_session.scalars.return_value = []

        new_cnt, upd_cnt = await _process_seasons_and_episodes(
            mock_session,
            series,
            "jf-series",
        )

        assert new_cnt == 0
        assert upd_cnt == 0
        mock_session.add.assert_not_called()
