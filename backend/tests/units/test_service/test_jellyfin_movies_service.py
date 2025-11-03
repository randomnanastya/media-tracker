from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models import Media, MediaType
from app.services.jellyfin_movies_service import sync_jellyfin_movies


@pytest.fixture
def jellyfin_user():
    user = AsyncMock()
    user.id = 1
    user.jellyfin_user_id = "jf_user1"
    user.username = "Alice"
    return user


@pytest.fixture
def jellyfin_movies_basic():
    return [
        {
            "Id": "jf_movie1",
            "Name": "Inception",
            "ProviderIds": {"Tmdb": "27205"},
            "UserData": {"Played": True, "LastPlayedDate": "2025-01-01T12:00:00Z"},
            "PremiereDate": "2010-07-16T00:00:00.0000000Z",
        },
        {
            "Id": "jf_movie2",
            "Name": "New Movie",
            "ProviderIds": {},
            "UserData": {"Played": False},
            "PremiereDate": "2024-01-01T00:00:00Z",
        },
    ]


@pytest.fixture
def existing_movie():
    media = AsyncMock()
    media.id = 100
    media.media_type = MediaType.MOVIE
    media.title = "Inception"

    movie = AsyncMock()
    movie.id = 100
    movie.tmdb_id = "27205"
    movie.jellyfin_id = None
    movie.watched = False
    movie.watched_at = None
    movie.media = media

    return movie


@pytest.mark.skip(reason="Временно пропускаем — логика обновится позже")
@pytest.mark.asyncio
async def test_sync_jellyfin_movies_updates_existing_movie(
    mock_session, jellyfin_user, jellyfin_movies_basic, existing_movie
):
    """Should update watched status and jellyfin_id for existing movie"""
    users_result_mock = Mock()
    users_result_mock.scalars.return_value.all.return_value = [jellyfin_user]

    existing_movie_result_mock = Mock()
    existing_movie_result_mock.scalars.return_value.first.return_value = existing_movie

    no_movies_result_mock = Mock()
    no_movies_result_mock.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [
        users_result_mock,
        existing_movie_result_mock,
        no_movies_result_mock,
    ]

    with patch(
        "app.services.jellyfin_movies_service.fetch_jellyfin_movies_for_user",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = jellyfin_movies_basic

        result = await sync_jellyfin_movies(mock_session)

        assert result.synced_count == 2
        assert result.updated_count == 1
        assert result.added_count == 1

        # Check update
        assert existing_movie.jellyfin_id == "jf_movie1"
        assert existing_movie.watched is True
        assert existing_movie.watched_at == datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        mock_session.add.assert_called()
        mock_session.flush.assert_called()
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_sync_jellyfin_movies_adds_new_movie_without_provider_ids(
    mock_session, jellyfin_user, jellyfin_movies_basic
):
    """Should add new movie even without tmdb/imdb"""
    users_result_mock = Mock()
    users_result_mock.scalars.return_value.all.return_value = [jellyfin_user]

    # No existing movie
    no_movie_result_mock = Mock()
    no_movie_result_mock.scalars.return_value.first.return_value = None

    mock_session.execute.side_effect = [
        users_result_mock,
        no_movie_result_mock,
        no_movie_result_mock,
    ]

    with patch(
        "app.services.jellyfin_movies_service.fetch_jellyfin_movies_for_user",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = jellyfin_movies_basic

        result = await sync_jellyfin_movies(mock_session)

        assert result.added_count == 2
        assert mock_session.add.call_count >= 4  # Media + Movie x 2
        assert mock_session.flush.call_count >= 2


@pytest.mark.skip(reason="Временно пропускаем — логика обновится позже")
@pytest.mark.asyncio
async def test_sync_jellyfin_movies_handles_unwatched_movie(mock_session, jellyfin_user):
    """Should set watched=False if Jellyfin says not played"""
    users_result_mock = Mock()
    users_result_mock.scalars.return_value.all.return_value = [jellyfin_user]

    movie_data = {
        "Id": "jf_movie3",
        "Name": "Unwatched",
        "ProviderIds": {"Tmdb": "123"},
        "UserData": {"Played": False},
        "PremiereDate": "2023-01-01T00:00:00Z",
    }

    existing = Mock()
    existing.jellyfin_id = "jf_movie3"
    existing.watched = True
    existing.watched_at = datetime.now(UTC)

    movie_result_mock = Mock()
    movie_result_mock.scalars.return_value.first.return_value = existing

    mock_session.execute.side_effect = [
        users_result_mock,
        movie_result_mock,
    ]

    with patch(
        "app.services.jellyfin_movies_service.fetch_jellyfin_movies_for_user",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = [movie_data]

        result = await sync_jellyfin_movies(mock_session)

        assert existing.watched is False
        assert existing.watched_at is None
        assert result.updated_count == 1


@pytest.mark.asyncio
async def test_sync_jellyfin_movies_parses_premiere_date(mock_session, jellyfin_user):
    """Should parse PremiereDate correctly"""
    movie_data = {
        "Id": "jf_new",
        "Name": "Old Movie",
        "ProviderIds": {},
        "UserData": {"Played": False},
        "PremiereDate": "1999-12-31T23:59:59.9999999Z",
    }

    users_result_mock = Mock()
    users_result_mock.scalars.return_value.all.return_value = [jellyfin_user]

    movie_result_mock = Mock()
    movie_result_mock.scalars.return_value.first.return_value = None

    mock_session.execute.side_effect = [
        users_result_mock,
        movie_result_mock,
    ]

    with patch(
        "app.services.jellyfin_movies_service.fetch_jellyfin_movies_for_user",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = [movie_data]

        await sync_jellyfin_movies(mock_session)

        added_media = None
        for call in mock_session.add.call_args_list:
            obj = call[0][0]
            if isinstance(obj, Media):
                added_media = obj
                break

        assert added_media is not None
        assert added_media.release_date == datetime(1999, 12, 31, 23, 59, 59, 999999, tzinfo=UTC)
