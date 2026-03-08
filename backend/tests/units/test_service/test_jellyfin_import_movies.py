from unittest.mock import AsyncMock, patch

import pytest

from app.services.import_jellyfin_movies_service import import_jellyfin_movies


@pytest.mark.asyncio
async def test_import_jellyfin_movies_creates_new_movies(mock_session):
    """Создаёт Media + Movie для каждого фильма."""
    from tests.factories import JellyfinMovieDictFactory

    movies = [
        JellyfinMovieDictFactory.build(
            Id="jf1", Name="Inception", ProviderIds={"Tmdb": "27205", "Imdb": "tt1375666"}
        ),
        JellyfinMovieDictFactory.build(
            Id="jf2", Name="Matrix", ProviderIds={"Tmdb": "603", "Imdb": "tt0133093"}
        ),
    ]

    with (
        patch(
            "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "app.services.import_jellyfin_movies_service.find_movie_by_jellyfin_id",
            new_callable=AsyncMock,
        ) as mock_find_jf,
        patch(
            "app.services.import_jellyfin_movies_service.find_movie_by_external_ids",
            new_callable=AsyncMock,
        ) as mock_find_external,
    ):
        mock_fetch.return_value = movies
        mock_find_jf.return_value = None
        mock_find_external.return_value = None

        result = await import_jellyfin_movies(mock_session)

        assert result.imported_count == 2
        assert result.updated_count == 0

        # Media + Movie per film
        assert mock_session.add.call_count == 4
        assert mock_session.flush.call_count == 2
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()


@pytest.mark.asyncio
async def test_import_jellyfin_movie_updates_existing_by_jellyfin_id(
    mock_session,
    existing_movie_without_ids,
):
    """Обновляет существующий фильм, найденный по jellyfin_id."""
    from tests.factories import JellyfinMovieDictFactory

    movie_data = JellyfinMovieDictFactory.build(
        Id="jf123", Name="Inception", ProviderIds={"Tmdb": "27205", "Imdb": "tt1375666"}
    )

    with (
        patch(
            "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "app.services.import_jellyfin_movies_service.find_movie_by_jellyfin_id",
            new_callable=AsyncMock,
        ) as mock_find_jf,
        patch(
            "app.services.import_jellyfin_movies_service.find_movie_by_external_ids",
            new_callable=AsyncMock,
        ) as mock_find_external,
    ):
        mock_fetch.return_value = [movie_data]
        mock_find_jf.return_value = existing_movie_without_ids
        mock_find_external.return_value = None

        result = await import_jellyfin_movies(mock_session)

        assert result.imported_count == 0
        assert result.updated_count == 1
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_import_jellyfin_movie_updates_by_external_ids(mock_session):
    """Test updating existing movie found by external IDs."""
    from tests.factories import JellyfinMovieDictFactory, MovieFactory

    # Create existing movie in DB
    existing_movie = MovieFactory.build(
        id=1, radarr_id=None, tmdb_id="27205", imdb_id=None, media__title="Inception"
    )
    mock_session.add(existing_movie.media)

    movie_data = JellyfinMovieDictFactory.build(
        Id="jf999", Name="Inception", ProviderIds={"Tmdb": "27205"}
    )

    with (
        patch(
            "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "app.services.import_jellyfin_movies_service.find_movie_by_jellyfin_id",
            new_callable=AsyncMock,
        ) as mock_find_jf,
        patch(
            "app.services.import_jellyfin_movies_service.find_movie_by_external_ids",
            new_callable=AsyncMock,
        ) as mock_find_external,
    ):
        mock_fetch.return_value = [movie_data]
        mock_find_jf.return_value = None
        mock_find_external.return_value = existing_movie

        result = await import_jellyfin_movies(mock_session)

        assert result.imported_count == 0
        assert result.updated_count == 1


@pytest.mark.asyncio
async def test_import_jellyfin_movie_without_any_ids_skipped(mock_session):
    from tests.factories import JellyfinMovieDictFactory

    movie_data = JellyfinMovieDictFactory.build(Id=None, Name="Unknown Movie", ProviderIds={})

    with (
        patch(
            "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
            new_callable=AsyncMock,
        ) as mock_fetch,
    ):
        mock_fetch.return_value = [movie_data]

        result = await import_jellyfin_movies(mock_session)

        assert result.imported_count == 0
        assert result.updated_count == 0
        mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_import_jellyfin_movies_flush_failure_rollbacks(mock_session):
    from tests.factories import JellyfinMovieDictFactory

    movie_data = JellyfinMovieDictFactory.build(Id="jf1", Name="Movie", ProviderIds={"Tmdb": "1"})

    with (
        patch(
            "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "app.services.import_jellyfin_movies_service.find_movie_by_jellyfin_id",
            new_callable=AsyncMock,
        ) as mock_find_jf,
        patch(
            "app.services.import_jellyfin_movies_service.find_movie_by_external_ids",
            new_callable=AsyncMock,
        ) as mock_find_external,
    ):
        mock_fetch.return_value = [movie_data]
        mock_find_jf.return_value = None
        mock_find_external.return_value = None

        mock_session.flush.side_effect = Exception("Flush failed")

        with pytest.raises(Exception, match="Flush failed"):
            await import_jellyfin_movies(mock_session)

        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_import_jellyfin_movies_commit_failure(mock_session):
    from tests.factories import JellyfinMovieDictFactory

    movie_data = JellyfinMovieDictFactory.build(Id="jf1", Name="Movie", ProviderIds={"Tmdb": "1"})

    with (
        patch(
            "app.services.import_jellyfin_movies_service.fetch_jellyfin_movies",
            new_callable=AsyncMock,
        ) as mock_fetch,
        patch(
            "app.services.import_jellyfin_movies_service.find_movie_by_jellyfin_id",
            new_callable=AsyncMock,
        ) as mock_find_jf,
        patch(
            "app.services.import_jellyfin_movies_service.find_movie_by_external_ids",
            new_callable=AsyncMock,
        ) as mock_find_external,
    ):
        mock_fetch.return_value = [movie_data]
        mock_find_jf.return_value = None
        mock_find_external.return_value = None

        mock_session.commit.side_effect = Exception("Commit failed")

        with pytest.raises(Exception, match="Commit failed"):
            await import_jellyfin_movies(mock_session)

        mock_session.rollback.assert_called_once()
