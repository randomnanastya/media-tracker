from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.models.user import WatchStatus
from app.services.sync_jellyfin_watched_movies_service import sync_jellyfin_watched_movies


@pytest.mark.asyncio
async def test_sync_watched_movies_no_movies(mock_session, user):
    result_mock = Mock()

    scalars_mock = Mock()
    scalars_mock.all.return_value = [user]

    result_mock.scalars.return_value = scalars_mock

    mock_session.execute = AsyncMock(return_value=result_mock)

    with (
        patch(
            "app.services.sync_jellyfin_watched_movies_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
            new_callable=AsyncMock,
        ) as mock_fetch,
    ):
        mock_fetch.return_value = []

        result = await sync_jellyfin_watched_movies(mock_session)

        assert result.total_users == 1
        assert result.total_movies_processed == 0
        assert result.watched_added == 0
        assert result.watched_updated == 0
        assert result.unwatched_marked == 0


@pytest.mark.asyncio
async def test_sync_watched_movies_add_new(mock_session, user, movie):
    movie.tmdb_id = "123"  # Match movie_data

    movie_data = {
        "Id": "jf-movie-1",
        "Name": "Test Movie",
        "ProviderIds": {"Tmdb": "123"},
        "UserData": {"Played": True, "LastPlayedDate": "2024-01-01T10:00:00Z"},
    }

    users_scalars_mock = MagicMock()
    users_scalars_mock.all.return_value = [user]

    users_result_mock = MagicMock()
    users_result_mock.scalars.return_value = users_scalars_mock

    wh_scalars_mock = MagicMock()
    wh_scalars_mock.__iter__.return_value = iter([])

    wh_result_mock = MagicMock()
    wh_result_mock.scalars.return_value = wh_scalars_mock

    # Empty result for jellyfin_id search
    empty_scalars_mock = MagicMock()
    empty_scalars_mock.__iter__.return_value = iter([])
    empty_result_mock = MagicMock()
    empty_result_mock.scalars.return_value = empty_scalars_mock

    # Movie found by tmdb_id
    movies_scalars_mock = MagicMock()
    movies_scalars_mock.__iter__.return_value = iter([movie])
    movies_result_mock = MagicMock()
    movies_result_mock.scalars.return_value = movies_scalars_mock

    mock_session.execute = AsyncMock(
        side_effect=[
            users_result_mock,  # 1. select(User)
            wh_result_mock,  # 2. select(WatchHistory)
            empty_result_mock,  # 3. select(Movie).where(jellyfin_id.in_(...))
            movies_result_mock,  # 4. select(Movie).where(tmdb_id.in_(...))
            empty_result_mock,  # 5. select(Movie).where(imdb_id.in_(...))
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_movies_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "app.services.sync_jellyfin_watched_movies_service.parse_datetime",
            return_value="parsed-date",
        ),
    ):
        mock_fetch.return_value = [movie_data]

        result = await sync_jellyfin_watched_movies(mock_session)

        assert result.watched_added == 1
        assert result.watched_updated == 0
        assert result.unwatched_marked == 0

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_sync_watched_movies_update_existing(mock_session, user, movie, existing_watch):
    movie.tmdb_id = "123"  # Match movie_data

    movie_data = {
        "Id": "jf-movie-1",
        "ProviderIds": {"Tmdb": "123"},
        "UserData": {
            "Played": True,
            "LastPlayedDate": "2024-01-02T10:00:00Z",
        },
    }

    users_scalars_mock = MagicMock()
    users_scalars_mock.all.return_value = [user]
    users_result_mock = MagicMock()
    users_result_mock.scalars.return_value = users_scalars_mock

    wh_scalars_mock = MagicMock()
    wh_scalars_mock.__iter__.return_value = iter([existing_watch])
    wh_result_mock = MagicMock()
    wh_result_mock.scalars.return_value = wh_scalars_mock

    # Movie found by tmdb_id
    movies_scalars_mock = MagicMock()
    movies_scalars_mock.__iter__.return_value = iter([movie])
    movies_result_mock = MagicMock()
    movies_result_mock.scalars.return_value = movies_scalars_mock

    empty_scalars = MagicMock()
    empty_scalars.__iter__.return_value = iter([])
    empty_result = MagicMock()
    empty_result.scalars.return_value = empty_scalars

    mock_session.execute = AsyncMock(
        side_effect=[
            users_result_mock,  # 1. select(User).where(...)
            wh_result_mock,  # 2. select(WatchHistory).where(...)
            empty_result,  # 3. select(Movie).where(jellyfin_id.in_(...))
            movies_result_mock,  # 4. select(Movie).where(tmdb_id.in_(...))
            empty_result,  # 5. select(Movie).where(imdb_id.in_(...))
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_movies_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "app.services.sync_jellyfin_watched_movies_service.parse_datetime",
            return_value="2024-01-02T10:00:00",
        ),
    ):
        mock_fetch.return_value = [movie_data]

        result = await sync_jellyfin_watched_movies(mock_session)

        assert result.watched_updated == 1
        assert result.watched_added == 0
        assert result.unwatched_marked == 0

        assert existing_watch.status == WatchStatus.WATCHED

        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_sync_watched_movies_mark_unwatched(mock_session, user, movie, existing_watch):
    existing_watch.status = WatchStatus.WATCHED
    movie.tmdb_id = "123"  # Match movie_data

    movie_data = {
        "Id": "jf-movie-1",
        "ProviderIds": {"Tmdb": "123"},
        "UserData": {
            "Played": False,
        },
    }

    def create_scalars_mock_with_all(items):
        """Создает мок для scalars().all() цепочки."""
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = items
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        return result_mock

    def create_scalars_mock_with_iter(items):
        """Создает мок для scalars() итерации (for x in scalars())."""
        scalars_mock = MagicMock()
        scalars_mock.__iter__.return_value = iter(items)
        result_mock = MagicMock()
        result_mock.scalars.return_value = scalars_mock
        return result_mock

    users_result = create_scalars_mock_with_all([user])
    watch_history_result = create_scalars_mock_with_iter([existing_watch])
    movies_result = create_scalars_mock_with_iter([movie])
    empty_result = create_scalars_mock_with_iter([])

    mock_session.execute = AsyncMock(
        side_effect=[
            users_result,  # 1. select(User).where(...)
            watch_history_result,  # 2. select(WatchHistory).where(...)
            empty_result,  # 3. select(Movie).where(jellyfin_id.in_(...))
            movies_result,  # 4. select(Movie).where(tmdb_id.in_(...))
            empty_result,  # 5. select(Movie).where(imdb_id.in_(...))
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_movies_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
            new_callable=AsyncMock,
        ) as mock_fetch,
    ):
        mock_fetch.return_value = [movie_data]

        result = await sync_jellyfin_watched_movies(mock_session)

        assert result.unwatched_marked == 0
        assert result.watched_added == 0
        assert result.watched_updated == 1
        assert result.total_users == 1
        assert result.total_movies_processed == 1

        assert existing_watch.status == WatchStatus.PLANNED

        mock_session.commit.assert_called()


def _make_scalars_all(items):
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = items
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    return result_mock


def _make_scalars_iter(items):
    scalars_mock = MagicMock()
    scalars_mock.__iter__.return_value = iter(items)
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    return result_mock


@pytest.mark.asyncio
async def test_sync_heals_jellyfin_id_on_tmdb_match(mock_session, user, movie):
    """
    Фильм в БД с jellyfin_id="old-jf-id" и tmdb_id="123".
    Jellyfin возвращает тот же фильм с Id="new-jf-id" и ProviderIds={"Tmdb":"123"}.
    После синка movie.jellyfin_id должен стать "new-jf-id" (heal-on-match).
    """
    movie.jellyfin_id = "old-jf-id"
    movie.tmdb_id = "123"

    movie_data = {
        "Id": "new-jf-id",
        "Name": "Healed Movie",
        "ProviderIds": {"Tmdb": "123"},
        "UserData": {"Played": True, "LastPlayedDate": "2024-06-01T10:00:00Z"},
    }

    mock_session.execute = AsyncMock(
        side_effect=[
            _make_scalars_all([user]),  # 1. select(User)
            _make_scalars_iter([]),  # 2. select(WatchHistory)
            _make_scalars_iter([]),  # 3. select(Movie).where(jellyfin_id.in_("new-jf-id")) → miss
            _make_scalars_iter([movie]),  # 4. select(Movie).where(tmdb_id.in_("123")) → hit
            # no 5th call: ProviderIds has no Imdb → imdb_ids is empty
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_movies_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
            new_callable=AsyncMock,
            return_value=[movie_data],
        ),
        patch(
            "app.services.sync_jellyfin_watched_movies_service.parse_datetime",
            return_value="parsed-date",
        ),
    ):
        result = await sync_jellyfin_watched_movies(mock_session)

    assert result.watched_added == 1
    assert movie.jellyfin_id == "new-jf-id"


@pytest.mark.asyncio
async def test_sync_movie_not_found_logs_warning(mock_session, user, caplog):
    """
    Все три словаря пусты — фильм не найден ни по одному ID.
    Проверяем, что warning залогирован и счётчики равны нулю.
    """
    movie_data = {
        "Id": "unknown-jf-id",
        "Name": "Ghost Movie",
        "ProviderIds": {"Tmdb": "999", "Imdb": "tt999"},
        "UserData": {"Played": True},
    }

    mock_session.execute = AsyncMock(
        side_effect=[
            _make_scalars_all([user]),  # 1. select(User)
            _make_scalars_iter([]),  # 2. select(WatchHistory)
            _make_scalars_iter([]),  # 3. select(Movie).where(jellyfin_id.in_(...))
            _make_scalars_iter([]),  # 4. select(Movie).where(tmdb_id.in_(...))
            _make_scalars_iter([]),  # 5. select(Movie).where(imdb_id.in_(...))
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_movies_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
            new_callable=AsyncMock,
            return_value=[movie_data],
        ),
    ):
        import logging

        with caplog.at_level(logging.WARNING, logger="media_tracker"):
            result = await sync_jellyfin_watched_movies(mock_session)

    assert result.watched_added == 0
    assert result.watched_updated == 0

    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert warning_records, "Expected at least one WARNING log record, got none"
    warning_text = " ".join(r.getMessage() for r in warning_records)
    assert (
        "Movie not found in DB" in warning_text or "Ghost Movie" in warning_text
    ), f"Expected 'Movie not found in DB' warning, got: {warning_text}"


@pytest.mark.asyncio
async def test_sync_dropped_detection_uses_resolved_ids(mock_session, user, movie):
    """
    WatchHistory с status=PLANNED для фильма, которого нет в Jellyfin.
    Jellyfin возвращает другой фильм с неизвестными ID — movie из WatchHistory
    не попадает в jellyfin_media_ids, поэтому его статус должен стать DROPPED.
    """
    movie.jellyfin_id = "db-movie-jf"
    movie.tmdb_id = "db-tmdb"
    movie.imdb_id = None

    planned_watch = MagicMock()
    planned_watch.media_id = movie.id
    planned_watch.status = WatchStatus.PLANNED
    planned_watch.is_manual = False

    # Jellyfin returns a completely different movie (IDs not in DB)
    jellyfin_movie_data = {
        "Id": "unknown-jf-id",
        "Name": "Unknown Movie",
        "ProviderIds": {"Tmdb": "unknown-tmdb"},
        "UserData": {"Played": False},
    }

    # DB queries for the unknown Jellyfin movie's IDs return empty results.
    # imdb_ids is empty so there are only 4 execute calls (no 5th for imdb).
    empty_iter = _make_scalars_iter([])

    mock_session.execute = AsyncMock(
        side_effect=[
            _make_scalars_all([user]),  # 1. select(User)
            _make_scalars_iter([planned_watch]),  # 2. select(WatchHistory)
            empty_iter,  # 3. select(Movie).where(jellyfin_id.in_(...))
            empty_iter,  # 4. select(Movie).where(tmdb_id.in_(...))
            # no 5th call: imdb_ids is empty → no query
        ]
    )

    with (
        patch(
            "app.services.sync_jellyfin_watched_movies_service.get_decrypted_config",
            new_callable=AsyncMock,
            return_value=("http://jellyfin:8096", "test-api-key"),
        ),
        patch(
            "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
            new_callable=AsyncMock,
            return_value=[jellyfin_movie_data],
        ),
    ):
        result = await sync_jellyfin_watched_movies(mock_session)

    assert result.unwatched_marked == 1
    assert planned_watch.status == WatchStatus.DROPPED
