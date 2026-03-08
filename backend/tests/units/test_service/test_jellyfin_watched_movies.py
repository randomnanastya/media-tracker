from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from app.services.sync_jellyfin_watched_movies_service import sync_jellyfin_watched_movies


@pytest.mark.asyncio
async def test_sync_watched_movies_no_movies(mock_session, user):
    result_mock = Mock()

    scalars_mock = Mock()
    scalars_mock.all.return_value = [user]

    result_mock.scalars.return_value = scalars_mock

    mock_session.execute = AsyncMock(return_value=result_mock)

    with patch(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        new_callable=AsyncMock,
    ) as mock_fetch:
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

        assert existing_watch.is_watched is True

        mock_session.commit.assert_called()


@pytest.mark.asyncio
async def test_sync_watched_movies_mark_unwatched(mock_session, user, movie, existing_watch):
    existing_watch.is_watched = True
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

    with patch(
        "app.services.sync_jellyfin_watched_movies_service.fetch_jellyfin_movies_for_user_all",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = [movie_data]

        result = await sync_jellyfin_watched_movies(mock_session)

        assert result.unwatched_marked == 1
        assert result.watched_added == 0
        assert result.watched_updated == 0
        assert result.total_users == 1
        assert result.total_movies_processed == 1

        assert existing_watch.is_watched is False

        mock_session.commit.assert_called()
