from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.models import WatchHistory
from app.services.sync_jellyfin_watched_series_service import sync_jellyfin_watched_series
from tests.integration.conftest import create_episode, create_season, create_series, create_user


async def test_sync_adds_watched_episode(session_no_expire, monkeypatch):
    """
    Тест добавления просмотренной серии.
    """
    _ = await create_user(session_no_expire, username="alice", jellyfin_user_id="jf_1")

    series = await create_series(
        session_no_expire, title="Test Series", jellyfin_id="series_1", tmdb_id="tmdb_100"
    )

    season = await create_season(
        session_no_expire, series_id=series.id, number=1, jellyfin_id="season_1"
    )

    episode = await create_episode(
        session_no_expire,
        season_id=season.id,
        number=1,
        title="Test Episode",
        jellyfin_id="episode_1",
    )

    async def mock_fetch(jellyfin_user_id):
        return [
            {
                "Id": "episode_1",
                "Name": "Test Episode",
                "SeriesId": "series_1",
                "SeasonId": "season_1",
                "IndexNumber": 1,
                "ParentIndexNumber": 1,
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T12:00:00Z"},
                "ProviderIds": {"Tmdb": "tmdb_100"},
            }
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_series(session_no_expire)

    await session_no_expire.commit()

    watches = (
        (
            await session_no_expire.execute(
                select(WatchHistory).where(WatchHistory.episode_id.isnot(None))
            )
        )
        .scalars()
        .all()
    )

    assert len(watches) == 1
    assert watches[0].episode_id == episode.id
    assert watches[0].media_id == series.id
    assert watches[0].is_watched is True
    assert watches[0].watched_at == datetime(2024, 1, 1, 12, 0, tzinfo=UTC)

    assert result.watched_added == 1
    assert result.watched_updated == 0
    assert result.unwatched_marked == 0
    assert result.total_users == 1
    assert result.total_episodes_processed == 1


async def test_sync_updates_existing_watched_episode(session_no_expire, monkeypatch):
    """
    Тест обновления уже существующей записи просмотра эпизода.
    """
    user = await create_user(session_no_expire, username="bob", jellyfin_user_id="jf_2")

    series = await create_series(
        session_no_expire, title="Updated Series", jellyfin_id="series_2", tmdb_id="tmdb_200"
    )

    season = await create_season(
        session_no_expire, series_id=series.id, number=1, jellyfin_id="season_2"
    )

    episode = await create_episode(
        session_no_expire,
        season_id=season.id,
        number=1,
        title="Episode to Update",
        jellyfin_id="episode_2",
    )

    old_watch = WatchHistory(
        user_id=user.id,
        media_id=series.id,
        episode_id=episode.id,
        is_watched=True,
        watched_at=datetime(2023, 12, 1, 10, 0, tzinfo=UTC),
    )
    session_no_expire.add(old_watch)
    await session_no_expire.commit()

    async def mock_fetch(jellyfin_user_id):
        return [
            {
                "Id": "episode_2",
                "Name": "Episode to Update",
                "SeriesId": "series_2",
                "SeasonId": "season_2",
                "IndexNumber": 1,
                "ParentIndexNumber": 1,
                "UserData": {
                    "Played": True,
                    "LastPlayedDate": "2024-01-15T20:00:00Z",  # Новая дата просмотра
                },
                "ProviderIds": {"Tmdb": "tmdb_200"},
            }
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_series(session_no_expire)
    await session_no_expire.commit()

    watches = (
        (
            await session_no_expire.execute(
                select(WatchHistory).where(WatchHistory.episode_id == episode.id)
            )
        )
        .scalars()
        .all()
    )

    assert len(watches) == 1
    assert watches[0].watched_at == datetime(2024, 1, 15, 20, 0, tzinfo=UTC)
    assert result.watched_updated == 1
    assert result.watched_added == 0


async def test_sync_marks_episode_unwatched(session_no_expire, monkeypatch):
    """
    Тест отметки эпизода как непросмотренного.
    """
    user = await create_user(session_no_expire, username="charlie", jellyfin_user_id="jf_3")

    series = await create_series(
        session_no_expire, title="Unwatched Series", jellyfin_id="series_3", tmdb_id="tmdb_300"
    )

    season = await create_season(
        session_no_expire, series_id=series.id, number=1, jellyfin_id="season_3"
    )

    episode = await create_episode(
        session_no_expire,
        season_id=season.id,
        number=1,
        title="Episode to Unwatch",
        jellyfin_id="episode_3",
    )

    old_watch = WatchHistory(
        user_id=user.id,
        media_id=series.id,
        episode_id=episode.id,
        is_watched=True,
        watched_at=datetime(2023, 12, 1, 10, 0, tzinfo=UTC),
    )
    session_no_expire.add(old_watch)
    await session_no_expire.commit()

    async def mock_fetch(jellyfin_user_id):
        return [
            {
                "Id": "episode_3",
                "Name": "Episode to Unwatch",
                "SeriesId": "series_3",
                "SeasonId": "season_3",
                "IndexNumber": 1,
                "ParentIndexNumber": 1,
                "UserData": {"Played": False},
                "ProviderIds": {"Tmdb": "tmdb_300"},
            }
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_series(session_no_expire)
    await session_no_expire.commit()

    watches = (
        (
            await session_no_expire.execute(
                select(WatchHistory).where(WatchHistory.episode_id == episode.id)
            )
        )
        .scalars()
        .all()
    )

    assert len(watches) == 1
    assert watches[0].is_watched is False
    assert result.unwatched_marked == 1
    assert result.watched_added == 0
    assert result.watched_updated == 0


async def test_sync_multiple_episodes_for_user(session_no_expire, monkeypatch):
    """
    Тест синхронизации нескольких эпизодов для одного пользователя.
    """
    _ = await create_user(session_no_expire, username="multi_ep", jellyfin_user_id="jf_4")

    series = await create_series(
        session_no_expire, title="Multi-Episode Series", jellyfin_id="series_4", tmdb_id="tmdb_400"
    )

    season = await create_season(
        session_no_expire, series_id=series.id, number=1, jellyfin_id="season_4"
    )

    episodes = []
    for i in range(3):
        episode = await create_episode(
            session_no_expire,
            season_id=season.id,
            number=i + 1,
            title=f"Episode {i + 1}",
            jellyfin_id=f"episode_{i + 4}",
        )
        episodes.append(episode)

    await session_no_expire.commit()

    async def mock_fetch(jellyfin_user_id):
        return [
            {
                "Id": "episode_4",
                "Name": "Episode 1",
                "SeriesId": "series_4",
                "SeasonId": "season_4",
                "IndexNumber": 1,
                "ParentIndexNumber": 1,
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T10:00:00Z"},
                "ProviderIds": {"Tmdb": "tmdb_400"},
            },
            {
                "Id": "episode_5",
                "Name": "Episode 2",
                "SeriesId": "series_4",
                "SeasonId": "season_4",
                "IndexNumber": 2,
                "ParentIndexNumber": 1,
                "UserData": {"Played": False},
                "ProviderIds": {"Tmdb": "tmdb_400"},
            },
            {
                "Id": "episode_6",
                "Name": "Episode 3",
                "SeriesId": "series_4",
                "SeasonId": "season_4",
                "IndexNumber": 3,
                "ParentIndexNumber": 1,
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-02T11:00:00Z"},
                "ProviderIds": {"Tmdb": "tmdb_400"},
            },
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_series(session_no_expire)
    await session_no_expire.commit()

    watches = (
        (
            await session_no_expire.execute(
                select(WatchHistory).where(WatchHistory.episode_id.isnot(None))
            )
        )
        .scalars()
        .all()
    )

    assert len(watches) == 2

    watched_episode_ids = {w.episode_id for w in watches}
    assert episodes[0].id in watched_episode_ids
    assert episodes[2].id in watched_episode_ids
    assert episodes[1].id not in watched_episode_ids

    assert result.watched_added == 2
    assert result.watched_updated == 0
    assert result.unwatched_marked == 0
    assert result.total_episodes_processed == 3


async def test_sync_multiple_users(session_no_expire, monkeypatch):
    """
    Тест синхронизации эпизодов для нескольких пользователей.
    """
    user1 = await create_user(session_no_expire, username="user1", jellyfin_user_id="jf_5")
    user2 = await create_user(session_no_expire, username="user2", jellyfin_user_id="jf_6")

    series = await create_series(
        session_no_expire, title="Shared Series", jellyfin_id="series_5", tmdb_id="tmdb_500"
    )

    season = await create_season(
        session_no_expire, series_id=series.id, number=1, jellyfin_id="season_5"
    )

    _ = await create_episode(
        session_no_expire,
        season_id=season.id,
        number=1,
        title="Shared Episode",
        jellyfin_id="episode_7",
    )

    call_count = 0

    async def mock_fetch(jellyfin_user_id):
        nonlocal call_count
        call_count += 1

        return [
            {
                "Id": "episode_7",
                "Name": "Shared Episode",
                "SeriesId": "series_5",
                "SeasonId": "season_5",
                "IndexNumber": 1,
                "ParentIndexNumber": 1,
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T12:00:00Z"},
                "ProviderIds": {"Tmdb": "tmdb_500"},
            }
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_series(session_no_expire)
    await session_no_expire.commit()

    assert call_count == 2
    watches = (
        (
            await session_no_expire.execute(
                select(WatchHistory).where(WatchHistory.episode_id.isnot(None))
            )
        )
        .scalars()
        .all()
    )

    assert len(watches) == 2

    user_ids = {w.user_id for w in watches}
    assert user1.id in user_ids
    assert user2.id in user_ids

    assert result.total_users == 2
    assert result.watched_added == 2
    assert result.total_episodes_processed == 2


async def test_skip_episode_not_found_in_database(session_no_expire, monkeypatch):
    """
    Тест пропуска эпизода, который не найден в базе данных.
    """
    _ = await create_user(session_no_expire, username="not_found", jellyfin_user_id="jf_7")

    series = await create_series(
        session_no_expire, title="Test Series", jellyfin_id="series_6", tmdb_id="tmdb_600"
    )

    season = await create_season(
        session_no_expire, series_id=series.id, number=1, jellyfin_id="season_6"
    )

    episode = await create_episode(
        session_no_expire,
        season_id=season.id,
        number=1,
        title="Existing Episode",
        jellyfin_id="episode_other",
    )

    await session_no_expire.commit()

    async def mock_fetch(jellyfin_user_id):
        return [
            {
                "Id": "episode_8",
                "Name": "Missing Episode",
                "SeriesId": "series_6",
                "SeasonId": "season_6",
                "IndexNumber": 2,
                "ParentIndexNumber": 1,
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T12:00:00Z"},
                "ProviderIds": {"Tmdb": "tmdb_600"},
            },
            {
                "Id": "episode_other",
                "Name": "Existing Episode",
                "SeriesId": "series_6",
                "SeasonId": "season_6",
                "IndexNumber": 1,
                "ParentIndexNumber": 1,
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T12:00:00Z"},
                "ProviderIds": {"Tmdb": "tmdb_600"},
            },
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_series(session_no_expire)
    await session_no_expire.commit()

    watches = (
        (
            await session_no_expire.execute(
                select(WatchHistory).where(WatchHistory.episode_id.isnot(None))
            )
        )
        .scalars()
        .all()
    )

    assert len(watches) == 1
    assert watches[0].episode_id == episode.id

    assert result.total_episodes_processed == 1
    assert result.watched_added == 1


@pytest.mark.asyncio
async def test_error_handling_during_sync(session_no_expire, monkeypatch):
    """
    Тест обработки ошибок во время синхронизации.
    """
    _ = await create_user(session_no_expire, username="good_user", jellyfin_user_id="jf_9")
    _ = await create_user(session_no_expire, username="bad_user", jellyfin_user_id="jf_10")

    series = await create_series(
        session_no_expire, title="Test Series", jellyfin_id="series_7", tmdb_id="tmdb_700"
    )

    season = await create_season(
        session_no_expire, series_id=series.id, number=1, jellyfin_id="season_7"
    )

    _ = await create_episode(
        session_no_expire,
        season_id=season.id,
        number=1,
        title="Test Episode",
        jellyfin_id="episode_9",
    )

    call_count = 0

    async def mock_fetch(jellyfin_user_id):
        nonlocal call_count
        call_count += 1

        if jellyfin_user_id == "jf_9":
            return [
                {
                    "Id": "episode_9",
                    "Name": "Test Episode",
                    "SeriesId": "series_7",
                    "SeasonId": "season_7",
                    "IndexNumber": 1,
                    "ParentIndexNumber": 1,
                    "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T12:00:00Z"},
                    "ProviderIds": {"Tmdb": "tmdb_700"},
                }
            ]
        else:  # jf_10 - вызывает ошибку
            raise Exception("Jellyfin API error")

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_series(session_no_expire)
    await session_no_expire.commit()

    watches = (
        (
            await session_no_expire.execute(
                select(WatchHistory).where(WatchHistory.episode_id.isnot(None))
            )
        )
        .scalars()
        .all()
    )

    assert len(watches) == 1
    assert result.total_users == 2
    assert result.watched_added == 1


@pytest.mark.asyncio
async def test_bulk_insert_of_watched_episodes(session_no_expire, monkeypatch):
    """
    Тест массовой вставки просмотренных эпизодов.
    """
    _ = await create_user(session_no_expire, username="bulk_user", jellyfin_user_id="jf_11")

    series = await create_series(
        session_no_expire, title="Bulk Series", jellyfin_id="series_8", tmdb_id="tmdb_800"
    )

    season = await create_season(
        session_no_expire, series_id=series.id, number=1, jellyfin_id="season_8"
    )

    episodes = []
    for i in range(10):
        episode = await create_episode(
            session_no_expire,
            season_id=season.id,
            number=i + 1,
            title=f"Episode {i + 1}",
            jellyfin_id=f"episode_{i + 10}",
        )
        episodes.append(episode)

    await session_no_expire.commit()

    async def mock_fetch(jellyfin_user_id):
        return [
            {
                "Id": f"episode_{i + 10}",
                "Name": f"Episode {i + 1}",
                "SeriesId": "series_8",
                "SeasonId": "season_8",
                "IndexNumber": i + 1,
                "ParentIndexNumber": 1,
                "UserData": {"Played": True, "LastPlayedDate": f"2024-01-{i + 1:02d}T12:00:00Z"},
                "ProviderIds": {"Tmdb": "tmdb_800"},
            }
            for i in range(10)
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_series_service.fetch_jellyfin_episodes_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_series(session_no_expire)
    await session_no_expire.commit()

    watches = (
        (
            await session_no_expire.execute(
                select(WatchHistory).where(WatchHistory.episode_id.isnot(None))
            )
        )
        .scalars()
        .all()
    )

    assert len(watches) == 10
    assert result.watched_added == 10
    assert result.total_episodes_processed == 10

    watched_episode_ids = {w.episode_id for w in watches}
    for episode in episodes:
        assert episode.id in watched_episode_ids
