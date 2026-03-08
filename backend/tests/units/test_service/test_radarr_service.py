from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.radarr_service import import_radarr_movies


@pytest.mark.asyncio
async def test_import_radarr_movies_creates_both_entities(mock_session, radarr_movies_basic):
    """Test service creates both Media and Movie entities for each movie."""
    # Arrange
    with (
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
        patch(
            "app.services.radarr_service.find_movie_by_radarr_id", new_callable=AsyncMock
        ) as mock_find_radarr,
        patch(
            "app.services.radarr_service.find_movie_by_external_ids", new_callable=AsyncMock
        ) as mock_find_external,
    ):
        mock_fetch.return_value = radarr_movies_basic

        # All movies not found by radarr_id or external_ids
        mock_find_radarr.return_value = None
        mock_find_external.return_value = None

        expected_movies_count = len(radarr_movies_basic)

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert
        assert (
            result.imported_count == expected_movies_count
        ), f"Expected to import {expected_movies_count} movies, but got {result}"

        # Verify add and flush calls for entity creation
        expected_add_calls = 2 * expected_movies_count  # Media + Movie per film
        assert (
            mock_session.add.call_count == expected_add_calls
        ), f"Expected {expected_add_calls} add calls, but got {mock_session.add.call_count}"

        assert (
            mock_session.flush.call_count == expected_movies_count
        ), f"Expected {expected_movies_count} flush calls, but got {mock_session.flush.call_count}"

        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()

        # Verify search functions were called for each movie
        assert mock_find_radarr.call_count == expected_movies_count
        assert mock_find_external.call_count == expected_movies_count


@pytest.mark.asyncio
async def test_import_radarr_movie_without_radarr_id_updates_by_tmdb(mock_session):
    """Movie without radarr_id but with tmdb_id → finds and updates."""
    # Arrange
    from tests.factories import MovieFactory, RadarrMovieDictFactory

    # Create existing movie in DB
    existing_movie = MovieFactory.build(id=1, radarr_id=None, tmdb_id="27205", imdb_id=None)
    mock_session.add(existing_movie.media)

    with (
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
        patch(
            "app.services.radarr_service.find_movie_by_radarr_id", new_callable=AsyncMock
        ) as mock_find_radarr,
        patch(
            "app.services.radarr_service.find_movie_by_external_ids", new_callable=AsyncMock
        ) as mock_find_external,
    ):
        mock_fetch.return_value = [
            RadarrMovieDictFactory.build(
                id=None, title="Inception", tmdbId=27205, imdbId="tt1375666"
            )
        ]

        # radarr_id = None → find_movie_by_radarr_id not called
        mock_find_radarr.return_value = None
        # Found by external_ids
        mock_find_external.return_value = existing_movie

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert
        assert result.imported_count == 0
        assert result.updated_count == 1


@pytest.mark.asyncio
async def test_import_radarr_movie_without_radarr_id_updates_by_imdb(mock_session):
    """Movie without radarr_id but with imdb_id → finds and updates."""
    # Arrange
    from tests.factories import MovieFactory, RadarrMovieDictFactory

    # Create existing movie in DB
    existing_movie = MovieFactory.build(
        id=2, radarr_id=None, tmdb_id=None, imdb_id="tt0133093", media__title="The Matrix"
    )
    mock_session.add(existing_movie.media)

    with (
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
        patch(
            "app.services.radarr_service.find_movie_by_radarr_id", new_callable=AsyncMock
        ) as mock_find_radarr,
        patch(
            "app.services.radarr_service.find_movie_by_external_ids", new_callable=AsyncMock
        ) as mock_find_external,
    ):
        mock_fetch.return_value = [
            RadarrMovieDictFactory.build(
                id=None, title="The Matrix", tmdbId=603, imdbId="tt0133093"
            )
        ]

        mock_find_radarr.return_value = None
        mock_find_external.return_value = existing_movie

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert
        assert result.imported_count == 0
        assert result.updated_count == 1


@pytest.mark.asyncio
async def test_import_radarr_movie_with_radarr_id_updates_existing_by_tmdb(mock_session):
    """Movie with radarr_id but already exists by tmdb → updates radarr_id."""
    # Arrange
    from tests.factories import MovieFactory, RadarrMovieDictFactory

    # Create existing movie in DB (without radarr_id but with tmdb_id)
    existing_movie = MovieFactory.build(
        id=1, radarr_id=None, tmdb_id="27205", imdb_id=None, media__title="Inception"
    )
    mock_session.add(existing_movie.media)

    with (
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
        patch(
            "app.services.radarr_service.find_movie_by_radarr_id", new_callable=AsyncMock
        ) as mock_find_radarr,
        patch(
            "app.services.radarr_service.find_movie_by_external_ids", new_callable=AsyncMock
        ) as mock_find_external,
    ):
        mock_fetch.return_value = [
            RadarrMovieDictFactory.build(
                id=123, title="Inception", tmdbId=27205, imdbId="tt1375666"
            )
        ]

        # Not found by radarr_id, but found by external_ids
        mock_find_radarr.return_value = None
        mock_find_external.return_value = existing_movie

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert
        assert result.imported_count == 0
        assert result.updated_count == 1


@pytest.mark.asyncio
async def test_import_radarr_movie_without_ids_skips_creation(mock_session):
    """Movie without radarr_id and without tmdb/imdb → skips creation."""
    # Arrange
    from tests.factories import RadarrMovieDictFactory

    with (
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
        patch(
            "app.services.radarr_service.find_movie_by_radarr_id", new_callable=AsyncMock
        ) as mock_find_radarr,
        patch(
            "app.services.radarr_service.find_movie_by_external_ids", new_callable=AsyncMock
        ) as mock_find_external,
    ):
        mock_fetch.return_value = [
            RadarrMovieDictFactory.build(
                id=None, title="Unknown Movie", no_external_ids=True, no_date=True
            )
        ]

        mock_find_radarr.return_value = None
        mock_find_external.return_value = None

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert
        assert result.imported_count == 0
        assert result.updated_count == 0
        mock_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_import_radarr_movie_without_radarr_id_already_complete_skips_update(mock_session):
    """Movie without radarr_id, but DB entry is complete → skips update."""
    # Arrange
    from datetime import UTC, datetime

    from tests.factories import MovieFactory, RadarrMovieDictFactory

    # Create existing movie in DB with all IDs already set
    existing_movie = MovieFactory.build(
        id=3,
        radarr_id=None,
        tmdb_id="27205",
        imdb_id="tt1375666",
        media__title="Inception",
        media__release_date=datetime(2010, 7, 16, tzinfo=UTC),
    )
    mock_session.add(existing_movie.media)

    with (
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
        patch(
            "app.services.radarr_service.find_movie_by_radarr_id", new_callable=AsyncMock
        ) as mock_find_radarr,
        patch(
            "app.services.radarr_service.find_movie_by_external_ids", new_callable=AsyncMock
        ) as mock_find_external,
    ):
        mock_fetch.return_value = [
            RadarrMovieDictFactory.build(
                id=None, title="Inception", tmdbId=27205, imdbId="tt1375666"
            )
        ]

        mock_find_radarr.return_value = None
        mock_find_external.return_value = existing_movie

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert
        assert result.imported_count == 0
        assert result.updated_count == 0


@pytest.mark.asyncio
async def test_import_radarr_movies_skips_existing_movies(mock_session):
    """Test service skips movies that already exist in database."""
    # Arrange
    from tests.factories import RadarrMovieDictFactory

    sample_movies_mixed = [
        RadarrMovieDictFactory.build(id=1, title="Existing Movie"),
        RadarrMovieDictFactory.build(id=2, title="New Movie"),
    ]

    with (
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
        patch(
            "app.services.radarr_service.find_movie_by_radarr_id", new_callable=AsyncMock
        ) as mock_find_radarr,
        patch(
            "app.services.radarr_service.find_movie_by_external_ids", new_callable=AsyncMock
        ) as mock_find_external,
    ):
        mock_fetch.return_value = sample_movies_mixed

        # First movie exists, second is new
        mock_find_radarr.side_effect = [None, None]  # Both not found by radarr_id
        mock_find_external.side_effect = [Mock(), None]  # First found by external, second not

        expected_imported_count = 1

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert
        assert result.imported_count == expected_imported_count


@pytest.mark.asyncio
async def test_import_radarr_movies_handles_partial_insert_failure(mock_session):
    """Test service performs transaction rollback when flush fails during movie import."""
    # Arrange
    from tests.factories import RadarrMovieDictFactory

    movies_with_tmdb = [
        RadarrMovieDictFactory.build(id=1, title="Movie 1", tmdbId=1001),
        RadarrMovieDictFactory.build(id=2, title="Movie 2", tmdbId=1002),
    ]

    with (
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
        patch(
            "app.services.radarr_service.find_movie_by_radarr_id", new_callable=AsyncMock
        ) as mock_find_radarr,
        patch(
            "app.services.radarr_service.find_movie_by_external_ids", new_callable=AsyncMock
        ) as mock_find_external,
    ):
        mock_fetch.return_value = movies_with_tmdb

        # Both movies not found → should create new
        mock_find_radarr.return_value = None
        mock_find_external.return_value = None

        flush_call_count = 0

        async def mock_flush():
            nonlocal flush_call_count
            flush_call_count += 1
            if flush_call_count == 2:  # Fail on second flush
                raise Exception("Flush failed")

        mock_session.flush.side_effect = mock_flush

        # Act & Assert
        with pytest.raises(Exception, match="Flush failed"):
            await import_radarr_movies(mock_session)

        # Assert
        assert flush_call_count == 2, f"Expected 2 flush calls, got {flush_call_count}"
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_import_radarr_movies_handles_commit_failure(mock_session):
    """Test service handles commit failure."""
    # Arrange
    from tests.factories import RadarrMovieDictFactory

    with (
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
        patch(
            "app.services.radarr_service.find_movie_by_radarr_id", new_callable=AsyncMock
        ) as mock_find_radarr,
        patch(
            "app.services.radarr_service.find_movie_by_external_ids", new_callable=AsyncMock
        ) as mock_find_external,
    ):
        mock_fetch.return_value = [RadarrMovieDictFactory.build(id=1, title="Movie 1", tmdbId=1001)]

        mock_find_radarr.return_value = None
        mock_find_external.return_value = None

        # Simulate commit failure
        mock_session.commit.side_effect = Exception("Commit failed")

        # Act & Assert
        with pytest.raises(Exception, match="Commit failed"):
            await import_radarr_movies(mock_session)

        mock_session.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_import_radarr_movies_skips_movies_without_id(
    mock_session,
    radarr_movies_without_radarr_id,
):
    """Test service skips movies without Radarr ID or with invalid data."""
    # Arrange
    with (
        patch(
            "app.services.radarr_service.fetch_radarr_movies", new_callable=AsyncMock
        ) as mock_fetch,
        patch(
            "app.services.radarr_service.find_movie_by_radarr_id", new_callable=AsyncMock
        ) as mock_find_radarr,
        patch(
            "app.services.radarr_service.find_movie_by_external_ids", new_callable=AsyncMock
        ) as mock_find_external,
    ):
        mock_fetch.return_value = radarr_movies_without_radarr_id

        mock_find_radarr.return_value = None
        mock_find_external.return_value = None

        # Act
        result = await import_radarr_movies(mock_session)

        # Assert
        assert result.imported_count == 1, (
            f"Expected 1 imported movie, got {result.imported_count}. "
            f"Movies data: {radarr_movies_without_radarr_id}"
        )
        assert result.updated_count == 0

        # Verify add was called for the valid movie
        assert mock_session.add.call_count == 2  # Media + Movie for one film
