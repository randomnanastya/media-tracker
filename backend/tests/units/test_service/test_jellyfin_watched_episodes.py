from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.sync_jellyfin_watched_series_service import (
    sync_jellyfin_watched_series,
)


@pytest.mark.asyncio
async def test_sync_watched_episodes_no_episodes(mock_session, user):
    users_scalars = MagicMock()
    users_scalars.all.return_value = [user]

    users_result = MagicMock()
    users_result.scalars.return_value = users_scalars

    mock_session.execute = AsyncMock(return_value=users_result)

    with patch(
        "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = []

        result = await sync_jellyfin_watched_series(mock_session)

        assert result.total_users == 1
        assert result.watched_added == 0
        assert result.watched_updated == 0
        assert result.unwatched_marked == 0


@pytest.mark.asyncio
async def test_sync_watched_episodes_add_new(mock_session, user, episode, season, series):
    episode.season = season
    season.series = series

    episode_data = {
        "Id": episode.jellyfin_id,
        "UserData": {
            "Played": True,
            "LastPlayedDate": "2024-01-01T10:00:00Z",
        },
    }

    users_result = MagicMock()
    users_result.scalars.return_value.all.return_value = [user]

    episodes_scalars = MagicMock()
    episodes_scalars.__iter__.return_value = iter([episode])
    episodes_result = MagicMock()
    episodes_result.scalars.return_value = episodes_scalars

    wh_scalars = MagicMock()
    wh_scalars.__iter__.return_value = iter([])
    wh_result = MagicMock()
    wh_result.scalars.return_value = wh_scalars

    mock_session.execute = AsyncMock(
        side_effect=[
            users_result,  # users
            episodes_result,  # episodes
            wh_result,  # watch history
            MagicMock(),  # insert
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "app.services.sync_jellyfin_watched_series_service.parse_datetime",
            return_value="parsed-date",
        ),
    ):
        mock_fetch.return_value = [episode_data]

        result = await sync_jellyfin_watched_series(mock_session)

        assert result.watched_added == 1
        assert result.watched_updated == 0
        assert result.unwatched_marked == 0

        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_sync_watched_episodes_update_existing(
    mock_session, user, episode, season, series, existing_watch
):
    episode.season = season
    season.series = series

    existing_watch.episode_id = episode.id
    existing_watch.is_watched = False

    episode_data = {
        "Id": episode.jellyfin_id,
        "UserData": {
            "Played": True,
            "LastPlayedDate": "2024-01-02T10:00:00Z",
        },
    }

    users_result = MagicMock()
    users_result.scalars.return_value.all.return_value = [user]

    episodes_result = MagicMock()
    episodes_result.scalars.return_value.__iter__.return_value = iter([episode])

    wh_result = MagicMock()
    wh_result.scalars.return_value.__iter__.return_value = iter([existing_watch])

    mock_session.execute = AsyncMock(
        side_effect=[
            users_result,
            episodes_result,
            wh_result,
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "app.services.sync_jellyfin_watched_series_service.parse_datetime",
            return_value="parsed-date",
        ),
    ):
        mock_fetch.return_value = [episode_data]

        result = await sync_jellyfin_watched_series(mock_session)

        assert result.watched_updated == 1
        assert existing_watch.is_watched is True
        assert existing_watch.watched_at == "parsed-date"

        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_sync_watched_episodes_mark_unwatched(
    mock_session, user, episode, season, series, existing_watch
):
    episode.season = season
    season.series = series

    existing_watch.episode_id = episode.id
    existing_watch.is_watched = True

    episode_data = {
        "Id": episode.jellyfin_id,
        "UserData": {
            "Played": False,
        },
    }

    users_result = MagicMock()
    users_result.scalars.return_value.all.return_value = [user]

    episodes_result = MagicMock()
    episodes_result.scalars.return_value.__iter__.return_value = iter([episode])

    wh_result = MagicMock()
    wh_result.scalars.return_value.__iter__.return_value = iter([existing_watch])

    mock_session.execute = AsyncMock(
        side_effect=[
            users_result,
            episodes_result,
            wh_result,
        ]
    )

    with patch(
        "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = [episode_data]

        result = await sync_jellyfin_watched_series(mock_session)

        assert result.unwatched_marked == 1
        assert existing_watch.is_watched is False

        mock_session.commit.assert_called()
