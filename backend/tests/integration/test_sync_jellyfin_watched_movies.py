from datetime import UTC, datetime

import pytest
from sqlalchemy import delete, select

from app.models import WatchHistory
from app.services.sync_jellyfin_watched_movies_service import sync_jellyfin_watched_movies
from tests.integration.conftest import create_movie, create_user


@pytest.mark.asyncio
async def test_sync_adds_watched_movie(session_no_expire, monkeypatch):
    """
    Тест добавления просмотренного фильма.
    Использует сессию с expire_on_commit=False чтобы избежать проблем
    с доступом к атрибутам после коммита.
    """
    _ = await create_user(session_no_expire, username="alice", jellyfin_user_id="jf_1")
    movie = await create_movie(session_no_expire, jellyfin_id="10", tmdb_id="100", imdb_id="tt100")

    async def mock_fetch(jellyfin_user_id):
        return [
            {
                "Id": "10",
                "Name": "Test Movie",
                "ProviderIds": {"Tmdb": "100", "Imdb": "tt100"},
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T12:00:00Z"},
            }
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_movies(session_no_expire)

    await session_no_expire.commit()

    watches = (await session_no_expire.execute(select(WatchHistory))).scalars().all()

    assert len(watches) == 1
    assert watches[0].media_id == movie.id
    assert watches[0].is_watched is True
    assert watches[0].watched_at == datetime(2024, 1, 1, 12, 0, tzinfo=UTC)

    assert result.watched_added == 1
    assert result.watched_updated == 0
    assert result.unwatched_marked == 0
    assert result.total_users == 1
    assert result.total_movies_processed == 1


@pytest.mark.asyncio
async def test_sync_with_mixed_watched_status(session_no_expire, monkeypatch):
    """
    Тест обработки смешанного статуса просмотра.
    Сценарий: несколько фильмов с разным статусом просмотра.
    """
    _ = await create_user(session_no_expire, username="mixed", jellyfin_user_id="jf_10")

    movies = []
    for i in range(3):
        movie = await create_movie(session_no_expire, jellyfin_id=f"mixed_{i}", tmdb_id=f"100{i}")
        movies.append(movie)

    await session_no_expire.commit()

    async def mock_fetch(jellyfin_user_id):
        return [
            {
                "Id": "mixed_0",
                "Name": "Watched Movie",
                "ProviderIds": {"Tmdb": "1000"},
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T10:00:00Z"},
            },
            {
                "Id": "mixed_1",
                "Name": "Unwatched Movie",
                "ProviderIds": {"Tmdb": "1001"},
                "UserData": {"Played": False},
            },
            {
                "Id": "mixed_2",
                "Name": "Another Watched",
                "ProviderIds": {"Tmdb": "1002"},
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-02T11:00:00Z"},
            },
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_movies(session_no_expire)

    await session_no_expire.commit()

    watches = (await session_no_expire.execute(select(WatchHistory))).scalars().all()

    assert len(watches) == 2

    assert result.watched_added == 2
    assert result.watched_updated == 0
    assert result.unwatched_marked == 0
    assert result.total_users == 1
    assert result.total_movies_processed == 3


@pytest.mark.asyncio
async def test_sync_updates_existing_watched_movie(session_no_expire, monkeypatch):
    """Тест обновления уже существующей записи истории просмотров"""
    user = await create_user(session_no_expire, username="charlie", jellyfin_user_id="jf_3")
    movie = await create_movie(session_no_expire, jellyfin_id="30", tmdb_id="300")

    old_watch = WatchHistory(
        user_id=user.id,
        media_id=movie.id,
        is_watched=True,
        watched_at=datetime(2023, 12, 1, 10, 0, tzinfo=UTC),
    )
    session_no_expire.add(old_watch)
    await session_no_expire.commit()

    async def mock_fetch(jellyfin_user_id):
        return [
            {
                "Id": "30",
                "Name": "Updated Movie",
                "ProviderIds": {"Tmdb": "300"},
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-15T20:00:00Z"},
            }
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_movies(session_no_expire)
    await session_no_expire.commit()

    watches = (await session_no_expire.execute(select(WatchHistory))).scalars().all()

    assert len(watches) == 1
    assert watches[0].watched_at == datetime(2024, 1, 15, 20, 0, tzinfo=UTC)
    assert result.watched_updated == 1
    assert result.watched_added == 0


@pytest.mark.asyncio
async def test_sync_marks_movie_unwatched(session_no_expire, monkeypatch):
    """Тест отметки фильма как непросмотренного"""
    user = await create_user(session_no_expire, username="david", jellyfin_user_id="jf_4")
    movie = await create_movie(session_no_expire, jellyfin_id="40", tmdb_id="400")

    old_watch = WatchHistory(
        user_id=user.id,
        media_id=movie.id,
        is_watched=True,
        watched_at=datetime(2023, 12, 1, 10, 0, tzinfo=UTC),
    )
    session_no_expire.add(old_watch)
    await session_no_expire.commit()

    async def mock_fetch(jellyfin_user_id):
        return [
            {
                "Id": "40",
                "Name": "Unwatched Movie",
                "ProviderIds": {"Tmdb": "400"},
                "UserData": {"Played": False},
            }
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_movies(session_no_expire)
    await session_no_expire.commit()

    watches = (await session_no_expire.execute(select(WatchHistory))).scalars().all()

    assert len(watches) == 1
    assert watches[0].is_watched is False
    assert result.unwatched_marked == 1


@pytest.mark.asyncio
async def test_sync_multiple_users(session_no_expire, monkeypatch):
    """Тест синхронизации для нескольких пользователей"""
    _ = await create_user(session_no_expire, username="user1", jellyfin_user_id="jf_5")
    _ = await create_user(session_no_expire, username="user2", jellyfin_user_id="jf_6")

    _ = await create_movie(session_no_expire, jellyfin_id="50", tmdb_id="500")
    _ = await create_movie(session_no_expire, jellyfin_id="60", tmdb_id="600")

    call_count = 0

    async def mock_fetch(jellyfin_user_id):
        nonlocal call_count
        call_count += 1

        if jellyfin_user_id == "jf_5":
            return [
                {
                    "Id": "50",
                    "Name": "Movie 1",
                    "ProviderIds": {"Tmdb": "500"},
                    "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T10:00:00Z"},
                }
            ]
        else:
            return [
                {
                    "Id": "60",
                    "Name": "Movie 2",
                    "ProviderIds": {"Tmdb": "600"},
                    "UserData": {"Played": True, "LastPlayedDate": "2024-01-02T11:00:00Z"},
                }
            ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_movies(session_no_expire)
    await session_no_expire.commit()

    assert call_count == 2
    watches = (await session_no_expire.execute(select(WatchHistory))).scalars().all()

    assert len(watches) == 2
    assert result.total_users == 2
    assert result.watched_added == 2


@pytest.mark.asyncio
async def test_find_movie_by_different_ids(session_no_expire, monkeypatch):
    """Тест поиска фильма по Jellyfin ID, TMDB ID и IMDb ID"""
    _ = await create_user(session_no_expire, username="multi_id", jellyfin_user_id="jf_7")

    _ = await create_movie(
        session_no_expire, jellyfin_id="jellyfin_70", tmdb_id="tmdb_700", imdb_id="tt700700"
    )

    async def mock_fetch_jellyfin(jellyfin_user_id):
        return [
            {
                "Id": "jellyfin_70",
                "Name": "Movie by Jellyfin ID",
                "ProviderIds": {},
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T10:00:00Z"},
            }
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        mock_fetch_jellyfin,
    )

    result = await sync_jellyfin_watched_movies(session_no_expire)
    await session_no_expire.commit()

    assert result.watched_added == 1

    await session_no_expire.execute(delete(WatchHistory))
    await session_no_expire.commit()

    async def mock_fetch_tmdb(jellyfin_user_id):
        return [
            {
                "Id": "unknown_jellyfin",
                "Name": "Movie by TMDB ID",
                "ProviderIds": {"Tmdb": "tmdb_700"},
                "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T10:00:00Z"},
            }
        ]

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        mock_fetch_tmdb,
    )

    result = await sync_jellyfin_watched_movies(session_no_expire)
    await session_no_expire.commit()

    assert result.watched_added == 1


@pytest.mark.asyncio
async def test_error_handling(session_no_expire, monkeypatch):
    """Тест обработки ошибок при синхронизации"""
    _ = await create_user(session_no_expire, username="good_user", jellyfin_user_id="jf_8")
    _ = await create_user(session_no_expire, username="bad_user", jellyfin_user_id="jf_9")

    _ = await create_movie(session_no_expire, jellyfin_id="80", tmdb_id="800")

    call_count = 0

    async def mock_fetch(jellyfin_user_id):
        nonlocal call_count
        call_count += 1

        if jellyfin_user_id == "jf_8":
            return [
                {
                    "Id": "80",
                    "Name": "Good Movie",
                    "ProviderIds": {"Tmdb": "800"},
                    "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T10:00:00Z"},
                }
            ]
        else:
            raise Exception("Jellyfin API error")

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_movies(session_no_expire)
    await session_no_expire.commit()

    watches = (await session_no_expire.execute(select(WatchHistory))).scalars().all()

    assert len(watches) == 1
    assert result.total_users == 2
    assert result.watched_added == 1


@pytest.mark.asyncio
async def test_no_movies_found(session_no_expire, monkeypatch):
    """Тест случая, когда у пользователя нет фильмов в Jellyfin"""
    _ = await create_user(session_no_expire, username="empty", jellyfin_user_id="jf_10")

    async def mock_fetch(jellyfin_user_id):
        return []

    monkeypatch.setattr(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        mock_fetch,
    )

    result = await sync_jellyfin_watched_movies(session_no_expire)

    watches = (await session_no_expire.execute(select(WatchHistory))).scalars().all()

    assert len(watches) == 0
    assert result.total_users == 1
    assert result.total_movies_processed == 0
    assert result.watched_added == 0
