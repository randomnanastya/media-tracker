from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user import WatchStatus
from app.services.sync_jellyfin_watched_series_service import (
    sync_jellyfin_watched_series,
)
from tests.factories import EpisodeFactory, SeasonFactory, SeriesFactory, UserFactory


@pytest.mark.asyncio
async def test_sync_watched_episodes_no_episodes(mock_session, user):
    users_scalars = MagicMock()
    users_scalars.all.return_value = [user]

    users_result = MagicMock()
    users_result.scalars.return_value = users_scalars

    mock_session.execute = AsyncMock(return_value=users_result)

    with (
        patch(
            "app.services.sync_jellyfin_watched_series_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
            new_callable=AsyncMock,
        ) as mock_fetch,
    ):
        mock_fetch.return_value = []

        result = await sync_jellyfin_watched_series(mock_session)

        assert result.total_users == 1
        assert result.watched_added == 0
        assert result.watched_updated == 0
        assert result.unwatched_marked == 0


@pytest.mark.asyncio
async def test_sync_watched_episodes_add_new(mock_session, user, episode, season, series):
    episode.season = season
    season.series_id = series.id

    episode_data = {
        "Id": "new-ep-jf",
        "SeriesId": series.jellyfin_id,
        "ParentIndexNumber": season.number,
        "IndexNumber": episode.number,
        "UserData": {
            "Played": True,
            "LastPlayedDate": "2024-01-01T10:00:00Z",
        },
    }

    mock_session.execute = AsyncMock(
        side_effect=[
            _make_scalars_all([user]),  # users
            _make_scalars_all([series]),  # series lookup
            _make_scalars_all([season]),  # seasons
            _make_scalars_all([episode]),  # episodes
            _make_scalars_iter([]),  # watch history
            MagicMock(),  # insert
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_series_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
            new_callable=AsyncMock,
            return_value=[episode_data],
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_series_by_ids",
            new_callable=AsyncMock,
            return_value=[{"Id": series.jellyfin_id, "ProviderIds": {}}],
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.parse_datetime",
            return_value="parsed-date",
        ),
    ):
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
    season.series_id = series.id

    existing_watch.episode_id = episode.id
    existing_watch.status = WatchStatus.PLANNED
    existing_watch.is_manual = False
    existing_watch.watched_at = None

    episode_data = {
        "Id": episode.jellyfin_id,
        "SeriesId": series.jellyfin_id,
        "ParentIndexNumber": season.number,
        "IndexNumber": episode.number,
        "UserData": {
            "Played": True,
            "LastPlayedDate": "2024-01-02T10:00:00Z",
        },
    }

    mock_session.execute = AsyncMock(
        side_effect=[
            _make_scalars_all([user]),
            _make_scalars_all([series]),
            _make_scalars_all([season]),
            _make_scalars_all([episode]),
            _make_scalars_iter([existing_watch]),
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_series_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
            new_callable=AsyncMock,
            return_value=[episode_data],
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_series_by_ids",
            new_callable=AsyncMock,
            return_value=[{"Id": series.jellyfin_id, "ProviderIds": {}}],
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.parse_datetime",
            return_value="parsed-date",
        ),
    ):
        result = await sync_jellyfin_watched_series(mock_session)

        assert result.watched_updated == 1
        assert existing_watch.status == WatchStatus.WATCHED
        assert existing_watch.watched_at == "parsed-date"
        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_sync_watched_episodes_mark_unwatched(
    mock_session, user, episode, season, series, existing_watch
):
    episode.season = season
    season.series_id = series.id

    existing_watch.episode_id = episode.id
    existing_watch.status = WatchStatus.WATCHED
    existing_watch.is_manual = False

    episode_data = {
        "Id": episode.jellyfin_id,
        "SeriesId": series.jellyfin_id,
        "ParentIndexNumber": season.number,
        "IndexNumber": episode.number,
        "UserData": {
            "Played": False,
            "PlaybackPositionTicks": 0,
        },
    }

    mock_session.execute = AsyncMock(
        side_effect=[
            _make_scalars_all([user]),
            _make_scalars_all([series]),
            _make_scalars_all([season]),
            _make_scalars_all([episode]),
            _make_scalars_iter([existing_watch]),
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_series_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
            new_callable=AsyncMock,
            return_value=[episode_data],
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_series_by_ids",
            new_callable=AsyncMock,
            return_value=[{"Id": series.jellyfin_id, "ProviderIds": {}}],
        ),
    ):
        result = await sync_jellyfin_watched_series(mock_session)

        assert result.watched_updated == 1
        assert existing_watch.status == WatchStatus.PLANNED
        mock_session.commit.assert_called()


def _make_scalars_all(items):
    """Helper: mock result supporting .scalars().all()"""
    scalars = MagicMock()
    scalars.all.return_value = items
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


def _make_scalars_iter(items):
    """Helper: mock result supporting iteration over .scalars()"""
    scalars = MagicMock()
    scalars.__iter__ = MagicMock(return_value=iter(items))
    result = MagicMock()
    result.scalars.return_value = scalars
    return result


@pytest.mark.asyncio
async def test_sync_heals_series_jellyfin_id_on_tvdb_match(mock_session):
    """
    Series in DB has stale jellyfin_id. Jellyfin episode payload carries new SeriesId.
    fetch_jellyfin_series_by_ids resolves the new SeriesId to Tvdb that matches DB series.
    After sync the series object must have its jellyfin_id updated (heal-on-match).
    """
    user = UserFactory.build(id=1, jellyfin_user_id="jf-user-1")
    series = SeriesFactory.build(
        id=10, jellyfin_id="old-series-jf", tvdb_id="tvdb-123", imdb_id=None
    )
    season = SeasonFactory.build(id=5, series_id=series.id, number=1)
    episode = EpisodeFactory.build(id=20, season_id=season.id, number=1, jellyfin_id="ep-jf-1")
    episode.season = season

    ep_data = {
        "Id": "ep-jf-1",
        "SeriesId": "new-series-jf",
        "ParentIndexNumber": 1,
        "IndexNumber": 1,
        "UserData": {"Played": True, "LastPlayedDate": "2024-03-01T10:00:00Z"},
    }

    # SQL order: users → series lookup → seasons → episodes → watch_history → insert
    users_result = _make_scalars_all([user])
    series_result = _make_scalars_all([series])
    seasons_result = _make_scalars_all([season])
    episodes_result = _make_scalars_all([episode])
    wh_result = _make_scalars_iter([])

    mock_session.execute = AsyncMock(
        side_effect=[
            users_result,  # 1. select(User)
            series_result,  # 2. select(Series).where(or_(...))
            seasons_result,  # 3. select(Season)
            episodes_result,  # 4. select(Episode)
            wh_result,  # 5. select(WatchHistory)
            MagicMock(),  # 6. insert(WatchHistory)
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_series_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
            new_callable=AsyncMock,
            return_value=[ep_data],
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_series_by_ids",
            new_callable=AsyncMock,
            return_value=[{"Id": "new-series-jf", "ProviderIds": {"Tvdb": "tvdb-123"}}],
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.parse_datetime",
            return_value="parsed-date",
        ),
    ):
        result = await sync_jellyfin_watched_series(mock_session)

    # heal must have updated the in-memory object
    assert series.jellyfin_id == "new-series-jf"
    assert result.watched_added == 1


@pytest.mark.asyncio
async def test_sync_heals_episode_jellyfin_id_on_season_ep_match(mock_session):
    """
    Episode in DB has stale jellyfin_id. Series is matched by its (correct) jellyfin_id.
    Jellyfin episode payload carries a new episode Id for the same S01E01.
    After sync the episode object must have its jellyfin_id updated (heal-on-match).
    """
    user = UserFactory.build(id=1, jellyfin_user_id="jf-user-2")
    series = SeriesFactory.build(id=11, jellyfin_id="jf-series-1", tvdb_id="tvdb-456", imdb_id=None)
    season = SeasonFactory.build(id=6, series_id=series.id, number=1)
    episode = EpisodeFactory.build(id=21, season_id=season.id, number=1, jellyfin_id="old-ep-jf")
    episode.season = season

    ep_data = {
        "Id": "new-ep-jf",
        "SeriesId": "jf-series-1",
        "ParentIndexNumber": 1,
        "IndexNumber": 1,
        "UserData": {"Played": True, "LastPlayedDate": "2024-04-01T10:00:00Z"},
    }

    users_result = _make_scalars_all([user])
    series_result = _make_scalars_all([series])
    seasons_result = _make_scalars_all([season])
    episodes_result = _make_scalars_all([episode])
    wh_result = _make_scalars_iter([])

    mock_session.execute = AsyncMock(
        side_effect=[
            users_result,
            series_result,
            seasons_result,
            episodes_result,
            wh_result,
            MagicMock(),  # insert
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_series_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
            new_callable=AsyncMock,
            return_value=[ep_data],
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_series_by_ids",
            new_callable=AsyncMock,
            # series matched by jellyfin_id directly — provider IDs not needed for resolve
            return_value=[{"Id": "jf-series-1", "ProviderIds": {}}],
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.parse_datetime",
            return_value="parsed-date",
        ),
    ):
        result = await sync_jellyfin_watched_series(mock_session)

    assert episode.jellyfin_id == "new-ep-jf"
    assert result.watched_added == 1


@pytest.mark.asyncio
async def test_sync_series_not_found_skips_all_episodes(mock_session):
    """
    fetch_jellyfin_series_by_ids returns an empty list — provider IDs are unknown.
    The series cannot be resolved by any ID, so all episodes are skipped.
    watched_added must stay 0.
    """
    user = UserFactory.build(id=1, jellyfin_user_id="jf-user-3")

    ep_data = {
        "Id": "ep-x",
        "SeriesId": "unknown-series-jf",
        "ParentIndexNumber": 1,
        "IndexNumber": 1,
        "UserData": {"Played": True, "LastPlayedDate": "2024-05-01T10:00:00Z"},
    }

    users_result = _make_scalars_all([user])
    # Series DB query returns nothing — no match
    series_result = _make_scalars_all([])
    seasons_result = _make_scalars_all([])
    episodes_result = _make_scalars_all([])
    wh_result = _make_scalars_iter([])

    mock_session.execute = AsyncMock(
        side_effect=[
            users_result,
            series_result,
            seasons_result,
            episodes_result,
            wh_result,
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_series_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
            new_callable=AsyncMock,
            return_value=[ep_data],
        ),
        patch(
            "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_series_by_ids",
            new_callable=AsyncMock,
            # Empty list — no provider IDs available, series can't be resolved
            return_value=[],
        ),
    ):
        result = await sync_jellyfin_watched_series(mock_session)

    assert result.watched_added == 0
    assert result.watched_updated == 0
